import { Module } from '@nestjs/common';
import { ExecutionController } from './execution.controller';
import { ExecutionService } from './execution.service';
import { QueueModule } from '../queue/queue.module';
import { BrowserModule } from '../browser/browser.module';

@Module({
  imports: [QueueModule, BrowserModule],
  controllers: [ExecutionController],
  providers: [ExecutionService],
  exports: [ExecutionService],
})
export class ExecutionModule {}

