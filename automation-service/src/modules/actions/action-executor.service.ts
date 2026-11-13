import { Injectable, Logger } from '@nestjs/common';
import { Page } from 'playwright';
import { LocatorResolverService, SelectorConfig } from '../selectors/locator-resolver.service';

export interface ActionPayload {
  action: string;
  config: Record<string, any>;
  variables?: Record<string, any>;
}

export interface ActionResult {
  success: boolean;
  action: string;
  duration_ms: number;
  output?: any;
  error?: string;
  extracted_data?: Record<string, any>;
}

@Injectable()
export class ActionExecutorService {
  private readonly logger = new Logger(ActionExecutorService.name);

  constructor(private readonly locatorResolver: LocatorResolverService) {}

  async execute(page: Page, payload: ActionPayload): Promise<ActionResult> {
    const start = Date.now();
    const action = payload.action.toLowerCase();
    const cfg = payload.config || {};

    try {
      let output: any = null;
      let extracted_data: Record<string, any> | undefined;

      switch (action) {
        case 'navigate': {
          const url = cfg.url || cfg.target_url;
          if (!url) throw new Error("Action 'navigate' requires a 'url' config.");
          const waitUntil = cfg.wait_until || 'domcontentloaded';
          const timeout = cfg.timeout_ms || 30000;
          const resp = await page.goto(url, { waitUntil, timeout });
          output = { url: page.url(), status: resp?.status() };
          break;
        }

        case 'click': {
          const { locator } = await this.locatorResolver.resolve(page, cfg as SelectorConfig);
          await locator.click({
            button: (cfg.button as any) || 'left',
            clickCount: cfg.click_count || 1,
            timeout: cfg.timeout_ms || 10000,
            force: cfg.force ?? false,
          });
          break;
        }

        case 'double_click': {
          const { locator } = await this.locatorResolver.resolve(page, cfg as SelectorConfig);
          await locator.dblclick({ timeout: cfg.timeout_ms || 10000 });
          break;
        }

        case 'right_click': {
          const { locator } = await this.locatorResolver.resolve(page, cfg as SelectorConfig);
          await locator.click({ button: 'right', timeout: cfg.timeout_ms || 10000 });
          break;
        }

        case 'hover': {
          const { locator } = await this.locatorResolver.resolve(page, cfg as SelectorConfig);
          await locator.hover({ timeout: cfg.timeout_ms || 10000 });
          break;
        }

        case 'fill': {
          const { locator } = await this.locatorResolver.resolve(page, cfg as SelectorConfig);
          const value = cfg.value ?? cfg.text ?? '';
          await locator.fill(String(value), { timeout: cfg.timeout_ms || 10000 });
          break;
        }

        case 'type':
        case 'keyboard_type': {
          const text = cfg.text ?? cfg.value ?? '';
          if (cfg.selector || cfg.role || cfg.label || cfg.test_id) {
            const { locator } = await this.locatorResolver.resolve(page, cfg as SelectorConfig);
            await locator.pressSequentially(String(text), { delay: cfg.delay_ms || 50 });
          } else {
            await page.keyboard.type(String(text), { delay: cfg.delay_ms || 50 });
          }
          break;
        }

        case 'clear': {
          const { locator } = await this.locatorResolver.resolve(page, cfg as SelectorConfig);
          await locator.clear({ timeout: cfg.timeout_ms || 10000 });
          break;
        }

        case 'press_key': {
          const key = cfg.key || 'Enter';
          if (cfg.selector || cfg.role || cfg.label || cfg.test_id) {
            const { locator } = await this.locatorResolver.resolve(page, cfg as SelectorConfig);
            await locator.press(key, { timeout: cfg.timeout_ms || 10000 });
          } else {
            await page.keyboard.press(key);
          }
          break;
        }

        case 'select':
        case 'select_option': {
          const { locator } = await this.locatorResolver.resolve(page, cfg as SelectorConfig);
          const value = cfg.value || cfg.option || cfg.label;
          await locator.selectOption(value, { timeout: cfg.timeout_ms || 10000 });
          break;
        }

        case 'check': {
          const { locator } = await this.locatorResolver.resolve(page, cfg as SelectorConfig);
          await locator.check({ timeout: cfg.timeout_ms || 10000 });
          break;
        }

        case 'uncheck': {
          const { locator } = await this.locatorResolver.resolve(page, cfg as SelectorConfig);
          await locator.uncheck({ timeout: cfg.timeout_ms || 10000 });
          break;
        }

        case 'scroll': {
          const x = cfg.x || 0;
          const y = cfg.y || 500;
          await page.evaluate(({ dx, dy }) => window.scrollBy(dx, dy), { dx: x, dy: y });
          break;
        }

        case 'scroll_into_view': {
          const { locator } = await this.locatorResolver.resolve(page, cfg as SelectorConfig);
          await locator.scrollIntoViewIfNeeded({ timeout: cfg.timeout_ms || 10000 });
          break;
        }

        case 'drag_and_drop': {
          const source = await this.locatorResolver.resolve(page, cfg as SelectorConfig);
          const target = await this.locatorResolver.resolve(page, {
            selector: cfg.target_selector,
            strategy: cfg.target_strategy,
          });
          await source.locator.dragTo(target.locator, { timeout: cfg.timeout_ms || 15000 });
          break;
        }

        case 'upload_file': {
          const { locator } = await this.locatorResolver.resolve(page, cfg as SelectorConfig);
          const filePath = cfg.file_path || cfg.files;
          if (!filePath) throw new Error("Action 'upload_file' requires 'file_path'");
          await locator.setInputFiles(filePath, { timeout: cfg.timeout_ms || 10000 });
          break;
        }

        case 'reload':
        case 'refresh': {
          await page.reload({ waitUntil: cfg.wait_until || 'domcontentloaded' });
          break;
        }

        case 'go_back':
        case 'browser_back': {
          await page.goBack({ waitUntil: cfg.wait_until || 'domcontentloaded' });
          break;
        }

        case 'go_forward':
        case 'browser_forward': {
          await page.goForward({ waitUntil: cfg.wait_until || 'domcontentloaded' });
          break;
        }

        case 'wait':
        case 'wait_for_timeout': {
          const ms = Math.min(cfg.duration_ms || cfg.timeout || 1000, 30000);
          await page.waitForTimeout(ms);
          break;
        }

        case 'wait_for_network_idle': {
          const timeout = cfg.timeout_ms || 10000;
          try {
            await page.waitForLoadState('networkidle', { timeout });
          } catch (e) {
            this.logger.warn(`Network idle timed out after ${timeout}ms, continuing.`);
          }
          break;
        }

        case 'extract_text': {
          const { locator } = await this.locatorResolver.resolve(page, cfg as SelectorConfig);
          const text = await locator.innerText({ timeout: cfg.timeout_ms || 10000 });
          const varName = cfg.variable_name || cfg.assign_to || 'extracted_text';
          extracted_data = { [varName]: text };
          output = text;
          break;
        }

        case 'extract_attribute': {
          const { locator } = await this.locatorResolver.resolve(page, cfg as SelectorConfig);
          const attr = cfg.attribute_name || 'value';
          const val = await locator.getAttribute(attr, { timeout: cfg.timeout_ms || 10000 });
          const varName = cfg.variable_name || cfg.assign_to || `extracted_${attr}`;
          extracted_data = { [varName]: val };
          output = val;
          break;
        }

        case 'evaluate_js': {
          const script = cfg.script || cfg.code;
          if (!script) throw new Error("Action 'evaluate_js' requires 'script'");
          output = await page.evaluate(script);
          if (cfg.assign_to) {
            extracted_data = { [cfg.assign_to]: output };
          }
          break;
        }

        case 'set_variable': {
          const varName = cfg.name || cfg.variable_name;
          const varValue = cfg.value;
          if (!varName) throw new Error("Action 'set_variable' requires 'name'");
          extracted_data = { [varName]: varValue };
          output = { [varName]: varValue };
          break;
        }

        case 'api_request':
        case 'http_request': {
          const method = (cfg.method || 'GET').toUpperCase();
          const urlStr = cfg.url || cfg.endpoint;
          if (!urlStr) throw new Error("Action 'api_request' requires 'url'");

          // SSRF validation
          const parsed = new URL(urlStr);
          const host = parsed.hostname.toLowerCase();
          if (
            host === '169.254.169.254' ||
            host === 'metadata.google.internal' ||
            host === 'metadata.goog' ||
            host.startsWith('169.254.')
          ) {
            throw new Error(`SSRF Block: API Request to cloud metadata '${host}' is strictly prohibited.`);
          }

          const headers = cfg.headers || {};
          const body = cfg.body ? (typeof cfg.body === 'string' ? cfg.body : JSON.stringify(cfg.body)) : undefined;

          const response = await page.request.fetch(urlStr, {
            method,
            headers,
            data: body,
            timeout: cfg.timeout_ms || 30000,
          });

          const status = response.status();
          let jsonBody: any = null;
          let textBody = '';
          try {
            jsonBody = await response.json();
          } catch {
            textBody = await response.text();
          }

          output = {
            status,
            ok: response.ok(),
            headers: response.headers(),
            body: jsonBody || textBody,
          };

          if (cfg.expected_status && status !== Number(cfg.expected_status)) {
            throw new Error(`API Status Assertion failed: expected ${cfg.expected_status}, received ${status}`);
          }

          if (cfg.assign_to) {
            extracted_data = { [cfg.assign_to]: jsonBody || textBody };
          }
          if (cfg.extract_field && jsonBody && typeof jsonBody === 'object') {
            const varName = cfg.assign_field_to || cfg.extract_field;
            extracted_data = {
              ...(extracted_data || {}),
              [varName]: jsonBody[cfg.extract_field],
            };
          }
          break;
        }

        default:
          throw new Error(`Unsupported browser action: '${action}'`);
      }

      return {
        success: true,
        action,
        duration_ms: Date.now() - start,
        output,
        extracted_data,
      };
    } catch (err: any) {
      return {
        success: false,
        action,
        duration_ms: Date.now() - start,
        error: err.message || String(err),
      };
    }
  }
}

