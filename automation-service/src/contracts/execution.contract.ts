import { z } from 'zod';

export const BrowserConfigSchema = z.object({
  browser_type: z.enum(['chromium', 'firefox', 'webkit']).default('chromium'),
  headless: z.boolean().default(true),
  viewport: z.object({
    width: z.number().default(1280),
    height: z.number().default(800),
  }).default({ width: 1280, height: 800 }),
  record_video: z.boolean().default(false),
  record_trace: z.boolean().default(true),
  timeout_ms: z.number().default(30000),
});

export type BrowserConfig = z.infer<typeof BrowserConfigSchema>;

export const FlowNodeSchema = z.object({
  id: z.string(),
  type: z.string(),
  action: z.string().optional(),
  config: z.record(z.any()).default({}),
  position: z.object({ x: z.number(), y: z.number() }).optional(),
});

export type FlowNode = z.infer<typeof FlowNodeSchema>;

export const FlowEdgeSchema = z.object({
  id: z.string().optional(),
  source: z.string(),
  target: z.string(),
  sourceHandle: z.string().nullable().optional(),
  targetHandle: z.string().nullable().optional(),
});

export type FlowEdge = z.infer<typeof FlowEdgeSchema>;

export const FlowGraphSchema = z.object({
  nodes: z.array(FlowNodeSchema),
  edges: z.array(FlowEdgeSchema),
  variables: z.record(z.any()).optional().default({}),
});

export type FlowGraph = z.infer<typeof FlowGraphSchema>;

export const ExecuteJobDtoSchema = z.object({
  execution_id: z.string().uuid(),
  project_id: z.string().uuid(),
  environment_id: z.string().uuid().nullable().optional(),
  user_id: z.string().uuid(),
  flow_id: z.string().uuid().optional(),
  test_case_id: z.string().uuid().optional(),
  browser_config: BrowserConfigSchema.default({}),
  allowed_domains: z.array(z.string()).default([]),
  variables: z.record(z.any()).default({}),
  graph_definition: FlowGraphSchema,
  correlation_id: z.string().optional(),
});

export type ExecuteJobDto = z.infer<typeof ExecuteJobDtoSchema>;

export interface ExecutionJobResult {
  execution_id: string;
  status: 'passed' | 'failed' | 'cancelled';
  duration_ms: number;
  steps_total: number;
  steps_passed: number;
  steps_failed: number;
  error_message?: string;
  artifacts: {
    screenshots: string[];
    trace_path?: string;
    video_path?: string;
    dom_snapshot_path?: string;
  };
}

