export enum ExecutionEventType {
  STATUS_CHANGE = 'execution:status_change',
  STEP_START = 'step:start',
  STEP_COMPLETE = 'step:complete',
  STEP_FAILED = 'step:failed',
  SCREENSHOT_CAPTURED = 'screenshot:captured',
  CONSOLE_LOG = 'console:log',
  VIEWPORT_FRAME = 'viewport:frame',
}

export interface ExecutionEvent<T = any> {
  event_id: string;
  execution_id: string;
  seq: number;
  timestamp: string;
  type: ExecutionEventType;
  payload: T;
}

export interface StatusChangePayload {
  status: 'queued' | 'running' | 'passed' | 'failed' | 'cancelled';
  message?: string;
  duration_ms?: number;
}

export interface StepEventPayload {
  node_id: string;
  action: string;
  status: 'running' | 'passed' | 'failed' | 'skipped';
  duration_ms?: number;
  url?: string;
  page_title?: string;
  error?: string;
  state_after?: Record<string, any>;
}

export interface ViewportFramePayload {
  frame_base64: string; // JPEG data
  timestamp: number;
  url: string;
}

export interface ConsoleLogPayload {
  level: 'info' | 'warn' | 'error' | 'debug';
  message: string;
  source?: string;
}

