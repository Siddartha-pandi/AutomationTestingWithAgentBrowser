import { Injectable, Logger } from '@nestjs/common';
import { Page } from 'playwright';
import { FlowGraph, FlowNode } from '../../contracts/execution.contract';
import { ExecutionEventType } from '../../contracts/events.contract';
import { ActionExecutorService } from '../actions/action-executor.service';
import { AssertionExecutorService } from '../assertions/assertion-executor.service';
import { ArtifactManagerService } from '../screenshots/artifact-manager.service';
import { EventPublisherService } from '../monitoring/event-publisher.service';
import { PageManagerService } from '../browser/page-manager.service';

export interface FlowExecutionState {
  executionId: string;
  storageDir: string;
  variables: Record<string, any>;
  cancelled: boolean;
  stepResults: Array<{
    nodeId: string;
    action: string;
    status: 'passed' | 'failed' | 'skipped';
    duration_ms: number;
    error?: string;
  }>;
}

export interface ValidationReport {
  valid: boolean;
  errors: string[];
}

@Injectable()
export class FlowExecutorService {
  private readonly logger = new Logger(FlowExecutorService.name);

  constructor(
    private readonly actionExecutor: ActionExecutorService,
    private readonly assertionExecutor: AssertionExecutorService,
    private readonly artifactManager: ArtifactManagerService,
    private readonly eventPublisher: EventPublisherService,
    private readonly pageManager: PageManagerService,
  ) {}

  interpolateVariables(str: string, variables: Record<string, any>): string {
    if (!str || typeof str !== 'string') return str;
    return str.replace(/\{\{\s*([a-zA-Z0-9_.-]+)\s*\}\}/g, (_, key) => {
      const val = variables[key];
      return val !== undefined ? String(val) : `{{${key}}}`;
    });
  }

  interpolateConfig(config: Record<string, any>, variables: Record<string, any>): Record<string, any> {
    const interpolated: Record<string, any> = {};
    for (const [key, value] of Object.entries(config || {})) {
      if (typeof value === 'string') {
        interpolated[key] = this.interpolateVariables(value, variables);
      } else if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
        interpolated[key] = this.interpolateConfig(value, variables);
      } else {
        interpolated[key] = value;
      }
    }
    return interpolated;
  }

  evaluateCondition(config: Record<string, any>, variables: Record<string, any>): boolean {
    const left = config.left_operand ?? config.variable ?? '';
    const operator = (config.operator || '==').trim();
    const right = config.right_operand ?? config.value ?? '';

    const leftVal = typeof left === 'string' ? this.interpolateVariables(left, variables) : left;
    const rightVal = typeof right === 'string' ? this.interpolateVariables(right, variables) : right;

    switch (operator) {
      case '==':
      case '===':
      case 'equals':
        return String(leftVal).trim() === String(rightVal).trim();
      case '!=':
      case '!==':
      case 'not_equals':
        return String(leftVal).trim() !== String(rightVal).trim();
      case '>':
        return Number(leftVal) > Number(rightVal);
      case '>=':
        return Number(leftVal) >= Number(rightVal);
      case '<':
        return Number(leftVal) < Number(rightVal);
      case '<=':
        return Number(leftVal) <= Number(rightVal);
      case 'contains':
        return String(leftVal).includes(String(rightVal));
      case 'not_contains':
        return !String(leftVal).includes(String(rightVal));
      case 'truthy':
      case 'is_empty':
        return !leftVal || leftVal === '0' || leftVal === 'false';
      default:
        return Boolean(leftVal);
    }
  }

  validateGraph(graph: FlowGraph): ValidationReport {
    const errors: string[] = [];
    if (!graph.nodes || graph.nodes.length === 0) {
      errors.push('Flow graph contains no nodes.');
      return { valid: false, errors };
    }

    const nodeIds = new Set<string>();
    for (const node of graph.nodes) {
      if (!node.id) {
        errors.push('Found node with missing or empty ID.');
      } else if (nodeIds.has(node.id)) {
        errors.push(`Duplicate node ID detected: '${node.id}'`);
      } else {
        nodeIds.add(node.id);
      }

      const action = (node.action || node.type || '').toLowerCase();
      if (action === 'navigate' && !node.config?.url && !node.config?.target_url) {
        errors.push(`Node '${node.id}' (navigate) requires a 'url' configuration.`);
      }
    }

    for (const edge of graph.edges || []) {
      if (!nodeIds.has(edge.source)) {
        errors.push(`Edge references non-existent source node '${edge.source}'`);
      }
      if (!nodeIds.has(edge.target)) {
        errors.push(`Edge references non-existent target node '${edge.target}'`);
      }
    }

    return {
      valid: errors.length === 0,
      errors,
    };
  }

  topologicalSort(graph: FlowGraph): FlowNode[] {
    const nodesMap = new Map<string, FlowNode>();
    const inDegree = new Map<string, number>();
    const adj = new Map<string, string[]>();

    for (const node of graph.nodes) {
      nodesMap.set(node.id, node);
      inDegree.set(node.id, 0);
      adj.set(node.id, []);
    }

    for (const edge of graph.edges) {
      if (nodesMap.has(edge.source) && nodesMap.has(edge.target)) {
        adj.get(edge.source)!.push(edge.target);
        inDegree.set(edge.target, (inDegree.get(edge.target) || 0) + 1);
      }
    }

    const queue: string[] = [];
    for (const [nodeId, deg] of inDegree.entries()) {
      if (deg === 0) queue.push(nodeId);
    }

    const sorted: FlowNode[] = [];
    while (queue.length > 0) {
      const curr = queue.shift()!;
      sorted.push(nodesMap.get(curr)!);

      for (const neighbor of adj.get(curr) || []) {
        inDegree.set(neighbor, inDegree.get(neighbor)! - 1);
        if (inDegree.get(neighbor) === 0) {
          queue.push(neighbor);
        }
      }
    }

    if (sorted.length !== graph.nodes.length) {
      this.logger.warn('Cycle or disconnected components detected in flow graph. Falling back to declared node order.');
      return graph.nodes;
    }

    return sorted;
  }

  async executeFlow(
    page: Page,
    graph: FlowGraph,
    state: FlowExecutionState,
  ): Promise<{
    status: 'passed' | 'failed' | 'cancelled';
    stepsTotal: number;
    stepsPassed: number;
    stepsFailed: number;
    errorMessage?: string;
  }> {
    // 1. Graph validation
    const validation = this.validateGraph(graph);
    if (!validation.valid) {
      const err = `Graph validation failed: ${validation.errors.join('; ')}`;
      this.logger.error(err);
      return {
        status: 'failed',
        stepsTotal: graph.nodes.length,
        stepsPassed: 0,
        stepsFailed: 1,
        errorMessage: err,
      };
    }

    const sortedNodes = this.topologicalSort(graph);
    let stepsPassed = 0;
    let stepsFailed = 0;

    for (const node of sortedNodes) {
      if (state.cancelled) {
        this.logger.warn(`Execution ${state.executionId} cancelled before node ${node.id}`);
        return {
          status: 'cancelled',
          stepsTotal: sortedNodes.length,
          stepsPassed,
          stepsFailed,
          errorMessage: 'Execution cancelled by user.',
        };
      }

      const actionType = (node.action || node.type || '').toLowerCase();
      const stepStart = Date.now();

      // Emit Step Start
      await this.eventPublisher.publish(state.executionId, ExecutionEventType.STEP_START, {
        node_id: node.id,
        action: actionType,
        status: 'running',
      });

      const config = this.interpolateConfig(node.config, state.variables);
      const maxRetries = Math.min(Math.max(Number(config.max_retries || config.retry_count || 0), 0), 3);
      const continueOnFailure = Boolean(config.continue_on_failure);

      let stepSuccess = false;
      let stepError: string | undefined;

      // Handle Condition / Branching Node
      if (actionType === 'condition' || actionType === 'if_else') {
        const conditionResult = this.evaluateCondition(config, state.variables);
        state.variables[`${node.id}_result`] = conditionResult;
        stepSuccess = true;
      } else {
        // Execute Action / Assertion with optional retry policy
        for (let attempt = 0; attempt <= maxRetries; attempt++) {
          try {
            if (this.isAssertion(actionType)) {
              const res = await this.assertionExecutor.execute(page, {
                assertion: actionType,
                config,
                variables: state.variables,
              });
              stepSuccess = res.success;
              stepError = res.error;
            } else {
              const res = await this.actionExecutor.execute(page, {
                action: actionType,
                config,
                variables: state.variables,
              });
              stepSuccess = res.success;
              stepError = res.error;

              if (res.extracted_data) {
                Object.assign(state.variables, res.extracted_data);
              }
            }

            if (stepSuccess) break;

            if (attempt < maxRetries) {
              this.logger.warn(`Step '${actionType}' (${node.id}) failed (attempt ${attempt + 1}). Retrying in 500ms...`);
              await page.waitForTimeout(500);
            }
          } catch (err: any) {
            stepSuccess = false;
            stepError = err.message || String(err);
            if (attempt >= maxRetries) break;
            await page.waitForTimeout(500);
          }
        }

        // Stream live viewport frame after action
        try {
          const frameBase64 = await this.pageManager.captureViewportFrame(page);
          if (frameBase64) {
            await this.eventPublisher.publish(state.executionId, ExecutionEventType.VIEWPORT_FRAME, {
              frame_base64: frameBase64,
              timestamp: Date.now(),
              url: page.url(),
            });
          }
        } catch {
          // Non-fatal viewport capture error
        }
      }

      const stepDuration = Date.now() - stepStart;

      if (stepSuccess || continueOnFailure) {
        stepsPassed++;
        state.stepResults.push({
          nodeId: node.id,
          action: actionType,
          status: stepSuccess ? 'passed' : 'failed',
          duration_ms: stepDuration,
          error: stepSuccess ? undefined : stepError,
        });

        await this.eventPublisher.publish(state.executionId, ExecutionEventType.STEP_COMPLETE, {
          node_id: node.id,
          action: actionType,
          status: stepSuccess ? 'passed' : 'failed',
          duration_ms: stepDuration,
          url: page.url(),
          page_title: await page.title().catch(() => ''),
        });
      } else {
        stepsFailed++;
        state.stepResults.push({
          nodeId: node.id,
          action: actionType,
          status: 'failed',
          duration_ms: stepDuration,
          error: stepError,
        });

        // Capture failure screenshot artifact
        await this.artifactManager.captureScreenshot(page, state.executionId, node.id, state.storageDir, true);

        await this.eventPublisher.publish(state.executionId, ExecutionEventType.STEP_FAILED, {
          node_id: node.id,
          action: actionType,
          status: 'failed',
          duration_ms: stepDuration,
          error: stepError,
          url: page.url(),
        });

        return {
          status: 'failed',
          stepsTotal: sortedNodes.length,
          stepsPassed,
          stepsFailed,
          errorMessage: `Step '${actionType}' (${node.id}) failed: ${stepError}`,
        };
      }
    }

    return {
      status: 'passed',
      stepsTotal: sortedNodes.length,
      stepsPassed,
      stepsFailed,
    };
  }

  private isAssertion(action: string): boolean {
    const assertions = [
      'element_visible',
      'element_hidden',
      'element_enabled',
      'element_disabled',
      'text_equals',
      'text_contains',
      'url_equals',
      'url_contains',
      'title_equals',
      'element_count',
      'attribute_equals',
      'input_value_equals',
    ];
    return assertions.includes(action.toLowerCase());
  }
}
