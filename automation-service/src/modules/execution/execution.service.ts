import { BadRequestException, Injectable, Logger } from '@nestjs/common';
import { QueueService } from '../queue/queue.service';
import { BrowserManagerService } from '../browser/browser-manager.service';
import { ExecuteJobDto, ExecuteJobDtoSchema } from '../../contracts/execution.contract';

@Injectable()
export class ExecutionService {
  private readonly logger = new Logger(ExecutionService.name);

  constructor(
    private readonly queueService: QueueService,
    private readonly browserManager: BrowserManagerService,
  ) {}

  async submitExecution(payload: unknown) {
    const parseResult = ExecuteJobDtoSchema.safeParse(payload);
    if (!parseResult.success) {
      throw new BadRequestException({
        message: 'Invalid execution job payload schema',
        errors: parseResult.error.errors,
      });
    }

    const validPayload: ExecuteJobDto = parseResult.data;
    const job = await this.queueService.addExecutionJob(validPayload);

    return {
      status: 'queued',
      job_id: job.id,
      execution_id: validPayload.execution_id,
      correlation_id: validPayload.correlation_id || null,
      queued_at: new Date().toISOString(),
    };
  }

  async cancelExecution(executionId: string) {
    const cancelled = await this.queueService.cancelJob(executionId);
    return {
      execution_id: executionId,
      cancelled,
      message: cancelled ? 'Execution cancellation signal accepted.' : 'Job not found in active or waiting queue.',
    };
  }

  async getHealthStatus() {
    const browsersReady = await this.browserManager.checkBrowsersHealth();
    const queueMetrics = await this.queueService.getQueueMetrics();

    return {
      status: 'healthy',
      service: 'automation-service',
      version: '1.0.0',
      timestamp: new Date().toISOString(),
      browsers: browsersReady,
      queue: queueMetrics,
    };
  }
}

