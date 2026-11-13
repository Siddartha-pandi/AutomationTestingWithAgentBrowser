import { Injectable, Logger, OnApplicationShutdown } from '@nestjs/common';
import { Browser, BrowserType, chromium, firefox, webkit } from 'playwright';
import { BrowserConfig } from '../../contracts/execution.contract';

@Injectable()
export class BrowserManagerService implements OnApplicationShutdown {
  private readonly logger = new Logger(BrowserManagerService.name);
  private readonly browserInstances = new Map<string, Browser>();

  async getBrowser(browserType: 'chromium' | 'firefox' | 'webkit' = 'chromium', headless = true): Promise<Browser> {
    const key = `${browserType}-${headless}`;
    const existing = this.browserInstances.get(key);

    if (existing && existing.isConnected()) {
      return existing;
    }

    this.logger.log(`Launching ${browserType} instance (headless: ${headless})...`);
    let launcher: BrowserType;
    switch (browserType) {
      case 'firefox':
        launcher = firefox;
        break;
      case 'webkit':
        launcher = webkit;
        break;
      case 'chromium':
      default:
        launcher = chromium;
        break;
    }

    const browser = await launcher.launch({
      headless,
      args: browserType === 'chromium' ? ['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu'] : [],
    });

    browser.on('disconnected', () => {
      this.logger.warn(`${browserType} instance disconnected or crashed.`);
      this.browserInstances.delete(key);
    });

    this.browserInstances.set(key, browser);
    return browser;
  }

  async checkBrowsersHealth(): Promise<Record<string, boolean>> {
    const results: Record<string, boolean> = {
      chromium: false,
      firefox: false,
      webkit: false,
    };

    try {
      const b = await chromium.launch({ headless: true });
      results.chromium = b.isConnected();
      await b.close();
    } catch (e) {
      this.logger.warn(`Chromium health probe failed: ${e}`);
    }

    try {
      const b = await firefox.launch({ headless: true });
      results.firefox = b.isConnected();
      await b.close();
    } catch (e) {
      this.logger.warn(`Firefox health probe failed: ${e}`);
    }

    try {
      const b = await webkit.launch({ headless: true });
      results.webkit = b.isConnected();
      await b.close();
    } catch (e) {
      this.logger.warn(`WebKit health probe failed: ${e}`);
    }

    return results;
  }

  async onApplicationShutdown() {
    this.logger.log('Closing all active browser instances...');
    for (const [key, browser] of this.browserInstances.entries()) {
      try {
        if (browser.isConnected()) {
          await browser.close();
        }
      } catch (err) {
        this.logger.error(`Error closing browser ${key}: ${err}`);
      }
    }
    this.browserInstances.clear();
  }
}

