import { Injectable, Logger, OnModuleDestroy, OnModuleInit } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { Queue, Job } from 'bullmq';
import { ExecuteJobDto } from '../../contracts/execution.contract';

@Injectable()
export class QueueService implements OnModuleInit, OnModuleDestroy {
  private readonly logger = new Logger(QueueService.name);
  private executionQueue: Queue;

  constructor(private readonly configService: ConfigService) {}

  onModuleInit() {
    const redis = this.configService.get('app.redis');
    this.executionQueue = new Queue('browser-execution', {
      connection: {
        host: redis.host,
        port: redis.port,
        password: redis.password,
        db: redis.db,
        maxRetriesPerRequest: null,
      },
      defaultJobOptions: {
        attempts: 1, // Non-idempotent browser actions should not retry blindly
        removeOnComplete: 100,
        removeOnFail: 200,
      },
    });
    this.logger.log('BullMQ browser-execution queue initialized.');
  }

  async addExecutionJob(payload: ExecuteJobDto): Promise<Job> {
    const jobId = `exec-${payload.execution_id}`;
    this.logger.log(`Queueing execution job ${jobId} (correlation: ${payload.correlation_id || 'none'})...`);

    return this.executionQueue.add('execute-flow', payload, {
      jobId, // Idempotency: prevents duplicate queueing of the same execution
      priority: 1,
    });
  }

  async cancelJob(executionId: string): Promise<boolean> {
    const jobId = `exec-${executionId}`;
    const job = await this.executionQueue.getJob(jobId);
    if (job) {
      const state = await job.getState();
      if (state === 'waiting' || state === 'delayed') {
        await job.remove();
        return true;
      }
      // If already active, the worker listens to cancellation signal
      await job.updateProgress({ cancelled: true });
      return true;
    }
    return false;
  }

  async getQueueMetrics(): Promise<{ waiting: number; active: number; failed: number; completed: number }> {
    const counts = await this.executionQueue.getJobCounts('waiting', 'active', 'failed', 'completed');
    return {
      waiting: counts.waiting || 0,
      active: counts.active || 0,
      failed: counts.failed || 0,
      completed: counts.completed || 0,
    };
  }

  async onModuleDestroy() {
    if (this.executionQueue) {
      await this.executionQueue.close();
    }
  }
}

