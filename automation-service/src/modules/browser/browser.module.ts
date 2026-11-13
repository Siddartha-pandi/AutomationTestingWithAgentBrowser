import { Module } from '@nestjs/common';
import { BrowserManagerService } from './browser-manager.service';
import { ContextManagerService } from './context-manager.service';
import { PageManagerService } from './page-manager.service';

@Module({
  providers: [BrowserManagerService, ContextManagerService, PageManagerService],
  exports: [BrowserManagerService, ContextManagerService, PageManagerService],
})
export class BrowserModule {}

