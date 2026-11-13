import { Module } from '@nestjs/common';
import { ChangeDetectorService } from './change-detector.service';

@Module({
  providers: [ChangeDetectorService],
  exports: [ChangeDetectorService],
})
export class ChangeDetectionModule {}

