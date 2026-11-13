import { Injectable, Logger } from '@nestjs/common';
import { Browser, BrowserContext } from 'playwright';
import { BrowserConfig } from '../../contracts/execution.contract';
import * as path from 'path';

export interface IsolatedSessionContext {
  context: BrowserContext;
  tracePath?: string;
  videoDir?: string;
  close: () => Promise<void>;
}

@Injectable()
export class ContextManagerService {
  private readonly logger = new Logger(ContextManagerService.name);

  async createIsolatedContext(
    browser: Browser,
    executionId: string,
    config: BrowserConfig,
    storageDir: string,
  ): Promise<IsolatedSessionContext> {
    const tracePath = config.record_trace
      ? path.join(storageDir, 'traces', `${executionId}.zip`)
      : undefined;

    const videoDir = config.record_video
      ? path.join(storageDir, 'videos', executionId)
      : undefined;

    this.logger.debug(`Creating isolated browser context for execution: ${executionId}`);

    const context = await browser.newContext({
      viewport: {
        width: config.viewport.width || 1280,
        height: config.viewport.height || 800,
      },
      ignoreHTTPSErrors: false,
      recordVideo: videoDir
        ? {
            dir: videoDir,
            size: {
              width: config.viewport.width || 1280,
              height: config.viewport.height || 800,
            },
          }
        : undefined,
    });

    if (config.record_trace) {
      await context.tracing.start({
        screenshots: true,
        snapshots: true,
        sources: true,
      });
    }

    const close = async () => {
      try {
        if (config.record_trace && tracePath) {
          this.logger.debug(`Exporting trace to: ${tracePath}`);
          await context.tracing.stop({ path: tracePath });
        }
      } catch (err) {
        this.logger.warn(`Failed to export Playwright trace for ${executionId}: ${err}`);
      } finally {
        await context.close();
      }
    };

    return {
      context,
      tracePath,
      videoDir,
      close,
    };
  }
}
