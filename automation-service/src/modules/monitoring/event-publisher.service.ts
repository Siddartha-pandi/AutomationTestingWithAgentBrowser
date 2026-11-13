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

    const eventId = `evt-${Date.now()}-${currentSeq}`;
    const timestamp = new Date().toISOString();

    // Standardized dual-compatible event envelope (supports both contract and legacy event_bus schema)
    const event = {
      event_id: eventId,
      id: eventId,
      execution_id: executionId,
      seq: currentSeq,
      timestamp,
      type,
      payload,
      data: payload,
    };

    const payloadJson = JSON.stringify(event);
    const channel1 = `execution:events:${executionId}`;
    const channel2 = `execution:channel:${executionId}`;

    try {
      if (this.redisClient && this.redisClient.status === 'ready') {
        await Promise.all([
          this.redisClient.publish(channel1, payloadJson),
          this.redisClient.publish(channel2, payloadJson),
        ]);
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

