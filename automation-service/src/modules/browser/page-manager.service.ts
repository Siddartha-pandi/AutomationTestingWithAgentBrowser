import { Injectable, Logger } from '@nestjs/common';
import { BrowserContext, Page, Request, Route } from 'playwright';

@Injectable()
export class PageManagerService {
  private readonly logger = new Logger(PageManagerService.name);

  async createPageWithPolicies(
    context: BrowserContext,
    allowedDomains: string[] = [],
    onConsole?: (level: 'info' | 'warn' | 'error' | 'debug', msg: string) => void,
  ): Promise<Page> {
    const page = await context.newPage();

    if (onConsole) {
      page.on('console', (msg) => {
        const type = msg.type();
        const level = type === 'error' ? 'error' : type === 'warning' ? 'warn' : 'info';
        onConsole(level, msg.text());
      });

      page.on('pageerror', (err) => {
        onConsole('error', `Page Exception: ${err.message}`);
      });
    }

    // SSRF Interceptor: Block cloud metadata and restricted networks
    await page.route('**/*', (route: Route, request: Request) => {
      const urlStr = request.url();
      try {
        const parsed = new URL(urlStr);
        const host = parsed.hostname.toLowerCase();

        // 1. Strictly block cloud metadata
        if (
          host === '169.254.169.254' ||
          host === 'metadata.google.internal' ||
          host === 'metadata.goog' ||
          host.startsWith('169.254.')
        ) {
          this.logger.warn(`SSRF Block: Route abort for cloud metadata attempt: ${urlStr}`);
          return route.abort('accessdenied');
        }

        // 2. Allowed domain policy check if allowlist configured
        if (allowedDomains.length > 0 && !allowedDomains.includes('*')) {
          const match = allowedDomains.some((pattern) => {
            if (pattern.startsWith('*.')) {
              const suffix = pattern.substring(2).toLowerCase();
              return host === suffix || host.endsWith(`.${suffix}`);
            }
            return host === pattern.toLowerCase();
          });

          if (!match && !['data:', 'blob:', 'about:blank'].includes(urlStr)) {
            this.logger.warn(`SSRF Block: Route abort for unapproved domain: ${host}`);
            return route.abort('accessdenied');
          }
        }

        return route.continue();
      } catch (e) {
        return route.continue();
      }
    });

    return page;
  }

  async captureViewportFrame(page: Page): Promise<string | null> {
    try {
      if (page.isClosed()) return null;
      const buffer = await page.screenshot({ type: 'jpeg', quality: 60 });
      return buffer.toString('base64');
    } catch {
      return null;
    }
  }
}

