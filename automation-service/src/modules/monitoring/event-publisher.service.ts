import { Injectable, Logger, OnModuleDestroy, OnModuleInit } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import Redis from 'ioredis';
import { ExecutionEvent, ExecutionEventType } from '../../contracts/events.contract';

@Injectable()
export class EventPublisherService implements OnModuleInit, OnModuleDestroy {
  private readonly logger = new Logger(EventPublisherService.name);
  private redisClient: Redis;
  private readonly sequences = new Map<string, number>();

  constructor(private readonly configService: ConfigService) {}

  onModuleInit() {
    const redisConfig = this.configService.get('app.redis');
    this.redisClient = new Redis({
      host: redisConfig.host,
      port: redisConfig.port,
      password: redisConfig.password,
      db: redisConfig.db,
      lazyConnect: true,
      maxRetriesPerRequest: 1,
    });

    this.redisClient.connect().catch((err) => {
      this.logger.warn(`Redis connection failed in EventPublisherService: ${err.message}. Operating in offline log fallback.`);
    });
  }

  async publish<T = any>(executionId: string, type: ExecutionEventType, payload: T): Promise<void> {
    const currentSeq = (this.sequences.get(executionId) || 0) + 1;
    this.sequences.set(executionId, currentSeq);

    const event: ExecutionEvent<T> = {
      event_id: `evt-${Date.now()}-${currentSeq}`,
      execution_id: executionId,
      seq: currentSeq,
      timestamp: new Date().toISOString(),
      type,
      payload,
    };

    const channel = `execution:events:${executionId}`;
    try {
      if (this.redisClient && this.redisClient.status === 'ready') {
        await this.redisClient.publish(channel, JSON.stringify(event));
      }
    } catch (err: any) {
      this.logger.debug(`Failed to publish event to Redis: ${err.message}`);
    }
  }

  async onModuleDestroy() {
    if (this.redisClient) {
      await this.redisClient.quit().catch(() => {});
    }
  }
}

