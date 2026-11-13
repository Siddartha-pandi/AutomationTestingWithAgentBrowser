import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';
import { appConfig } from './config/configuration';
import { BrowserModule } from './modules/browser/browser.module';
import { SelectorsModule } from './modules/selectors/selectors.module';
import { ActionsModule } from './modules/actions/actions.module';
import { AssertionsModule } from './modules/assertions/assertions.module';
import { ScreenshotsModule } from './modules/screenshots/screenshots.module';
import { MonitoringModule } from './modules/monitoring/monitoring.module';
import { ChangeDetectionModule } from './modules/change-detection/change-detection.module';
import { FlowsModule } from './modules/flows/flows.module';
import { QueueModule } from './modules/queue/queue.module';
import { ExecutionModule } from './modules/execution/execution.module';
import { ExecutionWorker } from './workers/execution.worker';

@Module({
  imports: [
    ConfigModule.forRoot({
      isGlobal: true,
      load: [appConfig],
    }),
    BrowserModule,
    SelectorsModule,
    ActionsModule,
    AssertionsModule,
    ScreenshotsModule,
    MonitoringModule,
    ChangeDetectionModule,
    FlowsModule,
    QueueModule,
    ExecutionModule,
  ],
  providers: [ExecutionWorker],
})
export class AppModule {}

