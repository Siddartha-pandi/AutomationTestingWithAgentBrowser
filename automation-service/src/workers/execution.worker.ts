import { Injectable, Logger, OnModuleDestroy, OnModuleInit } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { Worker, Job } from 'bullmq';
import { ExecuteJobDto, ExecutionJobResult } from '../contracts/execution.contract';
import { ExecutionEventType } from '../contracts/events.contract';
import { BrowserManagerService } from '../modules/browser/browser-manager.service';
import { ContextManagerService } from '../modules/browser/context-manager.service';
import { PageManagerService } from '../modules/browser/page-manager.service';
import { FlowExecutorService, FlowExecutionState } from '../modules/flows/flow-executor.service';
import { EventPublisherService } from '../modules/monitoring/event-publisher.service';

@Injectable()
export class ExecutionWorker implements OnModuleInit, OnModuleDestroy {
  private readonly logger = new Logger(ExecutionWorker.name);
  private worker: Worker;

  constructor(
    private readonly configService: ConfigService,
    private readonly browserManager: BrowserManagerService,
    private readonly contextManager: ContextManagerService,
    private readonly pageManager: PageManagerService,
    private readonly flowExecutor: FlowExecutorService,
    private readonly eventPublisher: EventPublisherService,
  ) {}

  onModuleInit() {
    const redis = this.configService.get('app.redis');
    const concurrency = this.configService.get<number>('app.worker.concurrency') || 2;

    this.worker = new Worker(
      'browser-execution',
      async (job: Job<ExecuteJobDto>) => {
        return this.processJob(job);
      },
      {
        connection: {
          host: redis.host,
          port: redis.port,
          password: redis.password,
          db: redis.db,
          maxRetriesPerRequest: null,
        },
        concurrency,
      },
    );

    this.worker.on('completed', (job) => {
      this.logger.log(`Job ${job.id} (execution: ${job.data.execution_id}) completed successfully.`);
    });

    this.worker.on('failed', (job, err) => {
      this.logger.error(`Job ${job?.id} failed: ${err.message}`);
    });

    this.logger.log(`ExecutionWorker started listening on 'browser-execution' with concurrency: ${concurrency}`);
  }

  async processJob(job: Job<ExecuteJobDto>): Promise<ExecutionJobResult> {
    const payload = job.data;
    const start = Date.now();
    const executionId = payload.execution_id;
    const storageDir = this.configService.get<string>('app.storageDir')!;

    this.logger.log(`Starting execution run ${executionId} (browser: ${payload.browser_config.browser_type})...`);

    // 1. Publish Status Change -> 'running'
    await this.eventPublisher.publish(executionId, ExecutionEventType.STATUS_CHANGE, {
      status: 'running',
      message: 'Worker picked up job. Initializing isolated Playwright browser context...',
    });

    const browser = await this.browserManager.getBrowser(
      payload.browser_config.browser_type,
      payload.browser_config.headless,
    );

    const isolatedSession = await this.contextManager.createIsolatedContext(
      browser,
      executionId,
      payload.browser_config,
      storageDir,
    );

    const state: FlowExecutionState = {
      executionId,
      storageDir,
      variables: { ...payload.variables },
      cancelled: false,
      stepResults: [],
    };

    let resultStatus: 'passed' | 'failed' | 'cancelled' = 'passed';
    let errorMessage: string | undefined;

    try {
      const page = await this.pageManager.createPageWithPolicies(
        isolatedSession.context,
        payload.allowed_domains,
        (level, msg) => {
          this.eventPublisher.publish(executionId, ExecutionEventType.CONSOLE_LOG, { level, message: msg });
        },
      );

      // Execute Flow Graph
      const execOutcome = await this.flowExecutor.executeFlow(page, payload.graph_definition, state);
      resultStatus = execOutcome.status;
      errorMessage = execOutcome.errorMessage;
    } catch (err: any) {
      resultStatus = 'failed';
      errorMessage = err.message || String(err);
      this.logger.error(`Execution ${executionId} error: ${errorMessage}`);
    } finally {
      await isolatedSession.close();
    }

    const duration_ms = Date.now() - start;

    // 2. Publish Final Status Change
    await this.eventPublisher.publish(executionId, ExecutionEventType.STATUS_CHANGE, {
      status: resultStatus,
      duration_ms,
      message: errorMessage || `Execution completed with status '${resultStatus}'.`,
    });

    return {
      execution_id: executionId,
      status: resultStatus,
      duration_ms,
      steps_total: state.stepResults.length,
      steps_passed: state.stepResults.filter((s) => s.status === 'passed').length,
      steps_failed: state.stepResults.filter((s) => s.status === 'failed').length,
      error_message: errorMessage,
      artifacts: {
        screenshots: [],
        trace_path: isolatedSession.tracePath,
      },
    };
  }

  async onModuleDestroy() {
    if (this.worker) {
      this.logger.log('Gracefully closing BullMQ ExecutionWorker...');
      await this.worker.close();
    }
  }
}

