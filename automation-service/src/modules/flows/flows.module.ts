import { Module } from '@nestjs/common';
import { FlowExecutorService } from './flow-executor.service';
import { ActionsModule } from '../actions/actions.module';
import { AssertionsModule } from '../assertions/assertions.module';
import { ScreenshotsModule } from '../screenshots/screenshots.module';
import { MonitoringModule } from '../monitoring/monitoring.module';
import { BrowserModule } from '../browser/browser.module';

@Module({
  imports: [ActionsModule, AssertionsModule, ScreenshotsModule, MonitoringModule, BrowserModule],
  providers: [FlowExecutorService],
  exports: [FlowExecutorService],
})
export class FlowsModule {}

