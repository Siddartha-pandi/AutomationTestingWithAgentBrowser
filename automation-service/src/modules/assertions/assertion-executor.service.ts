import { Injectable, Logger } from '@nestjs/common';
import { Page } from 'playwright';
import { LocatorResolverService, SelectorConfig } from '../selectors/locator-resolver.service';

export interface AssertionPayload {
  assertion: string;
  config: Record<string, any>;
  variables?: Record<string, any>;
}

export interface AssertionResult {
  success: boolean;
  assertion: string;
  duration_ms: number;
  actual?: any;
  expected?: any;
  error?: string;
}

@Injectable()
export class AssertionExecutorService {
  private readonly logger = new Logger(AssertionExecutorService.name);

  constructor(private readonly locatorResolver: LocatorResolverService) {}

  async execute(page: Page, payload: AssertionPayload): Promise<AssertionResult> {
    const start = Date.now();
    const assertion = payload.assertion.toLowerCase();
    const cfg = payload.config || {};
    const timeout = cfg.timeout_ms || 10000;

    try {
      let actual: any;
      let expected: any;

      switch (assertion) {
        case 'element_visible': {
          const { locator } = await this.locatorResolver.resolve(page, cfg as SelectorConfig);
          await locator.waitFor({ state: 'visible', timeout });
          actual = true;
          expected = true;
          break;
        }

        case 'element_hidden': {
          const { locator } = await this.locatorResolver.resolve(page, cfg as SelectorConfig);
          await locator.waitFor({ state: 'hidden', timeout });
          actual = false;
          expected = false;
          break;
        }

        case 'element_enabled': {
          const { locator } = await this.locatorResolver.resolve(page, cfg as SelectorConfig);
          const isEnabled = await locator.isEnabled({ timeout });
          if (!isEnabled) throw new Error('Expected element to be enabled, but it was disabled.');
          actual = isEnabled;
          expected = true;
          break;
        }

        case 'element_disabled': {
          const { locator } = await this.locatorResolver.resolve(page, cfg as SelectorConfig);
          const isDisabled = await locator.isDisabled({ timeout });
          if (!isDisabled) throw new Error('Expected element to be disabled, but it was enabled.');
          actual = isDisabled;
          expected = true;
          break;
        }

        case 'text_equals': {
          const { locator } = await this.locatorResolver.resolve(page, cfg as SelectorConfig);
          expected = String(cfg.expected_text ?? cfg.value ?? '');
          const text = (await locator.innerText({ timeout })).trim();
          actual = text;
          if (text !== expected.trim()) {
            throw new Error(`Text equals mismatch: expected '${expected}', got '${text}'`);
          }
          break;
        }

        case 'text_contains': {
          const { locator } = await this.locatorResolver.resolve(page, cfg as SelectorConfig);
          expected = String(cfg.expected_text ?? cfg.value ?? '');
          const text = (await locator.innerText({ timeout })).trim();
          actual = text;
          if (!text.includes(expected.trim())) {
            throw new Error(`Text contains mismatch: expected '${expected}' to be inside '${text}'`);
          }
          break;
        }

        case 'url_equals': {
          expected = String(cfg.expected_url ?? cfg.value ?? '');
          actual = page.url();
          if (actual !== expected) {
            throw new Error(`URL equals mismatch: expected '${expected}', got '${actual}'`);
          }
          break;
        }

        case 'url_contains': {
          expected = String(cfg.expected_url ?? cfg.value ?? '');
          actual = page.url();
          if (!actual.includes(expected)) {
            throw new Error(`URL contains mismatch: expected '${expected}' to be in '${actual}'`);
          }
          break;
        }

        case 'title_equals': {
          expected = String(cfg.expected_title ?? cfg.value ?? '');
          actual = await page.title();
          if (actual !== expected) {
            throw new Error(`Title equals mismatch: expected '${expected}', got '${actual}'`);
          }
          break;
        }

        case 'element_count': {
          const loc = page.locator(cfg.selector || '');
          expected = Number(cfg.expected_count ?? 1);
          actual = await loc.count();
          if (actual !== expected) {
            throw new Error(`Element count mismatch: expected ${expected}, got ${actual}`);
          }
          break;
        }

        case 'attribute_equals': {
          const { locator } = await this.locatorResolver.resolve(page, cfg as SelectorConfig);
          const attr = cfg.attribute_name || 'value';
          expected = String(cfg.expected_value ?? '');
          actual = await locator.getAttribute(attr, { timeout });
          if (actual !== expected) {
            throw new Error(`Attribute '${attr}' mismatch: expected '${expected}', got '${actual}'`);
          }
          break;
        }

        case 'input_value_equals': {
          const { locator } = await this.locatorResolver.resolve(page, cfg as SelectorConfig);
          expected = String(cfg.expected_value ?? '');
          actual = await locator.inputValue({ timeout });
          if (actual !== expected) {
            throw new Error(`Input value mismatch: expected '${expected}', got '${actual}'`);
          }
          break;
        }

        default:
          throw new Error(`Unsupported assertion type: '${assertion}'`);
      }

      return {
        success: true,
        assertion,
        duration_ms: Date.now() - start,
        actual,
        expected,
      };
    } catch (err: any) {
      return {
        success: false,
        assertion,
        duration_ms: Date.now() - start,
        error: err.message || String(err),
      };
    }
  }
}

