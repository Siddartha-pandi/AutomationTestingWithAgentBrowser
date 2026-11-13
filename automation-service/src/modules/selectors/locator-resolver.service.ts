import { Injectable, Logger } from '@nestjs/common';
import { Locator, Page } from 'playwright';

export interface SelectorConfig {
  strategy?: 'test_id' | 'role' | 'label' | 'placeholder' | 'text' | 'css' | 'xpath' | 'auto';
  test_id?: string;
  role?: string;
  name?: string;
  label?: string;
  placeholder?: string;
  text?: string;
  selector?: string; // CSS or XPath fallback
  xpath?: string;
  exact?: boolean;
  strict?: boolean;
}

export interface ResolutionResult {
  locator: Locator;
  resolvedStrategy: string;
  resolvedPattern: string;
  matchCount: number;
}

@Injectable()
export class LocatorResolverService {
  private readonly logger = new Logger(LocatorResolverService.name);

  async resolve(page: Page, config: SelectorConfig): Promise<ResolutionResult> {
    const isStrict = config.strict !== false; // Default to strict ambiguity protection

    // 1. Explicit Strategy Routing if configured
    if (config.strategy && config.strategy !== 'auto') {
      const loc = this.resolveExplicitStrategy(page, config);
      const count = await loc.count();
      if (count === 0) {
        throw new Error(`Element not found using strategy '${config.strategy}' with target: ${JSON.stringify(config)}`);
      }
      if (isStrict && count > 1) {
        throw new Error(`Ambiguous element: matched ${count} elements using strategy '${config.strategy}'. Strict policy requires a single match.`);
      }
      return {
        locator: loc,
        resolvedStrategy: config.strategy,
        resolvedPattern: this.getPatternDescription(config),
        matchCount: count,
      };
    }

    // 2. Deterministic Priority Resolution Hierarchy (Auto-Strategy)
    // Priority 1: Explicit Test ID (data-testid, data-test, data-qa)
    if (config.test_id) {
      const loc = page.getByTestId(config.test_id);
      const count = await loc.count();
      if (count === 1) {
        return { locator: loc, resolvedStrategy: 'test_id', resolvedPattern: config.test_id, matchCount: 1 };
      }
      if (count > 1 && isStrict) {
        throw new Error(`Ambiguity error: Test ID '${config.test_id}' matched ${count} elements.`);
      }
    }

    // Priority 2: Accessible Role + Name
    if (config.role) {
      const roleName = config.role as any;
      const options = config.name ? { name: config.name, exact: config.exact ?? true } : undefined;
      const loc = page.getByRole(roleName, options);
      const count = await loc.count();
      if (count === 1) {
        return { locator: loc, resolvedStrategy: 'role', resolvedPattern: `role=${config.role}, name=${config.name}`, matchCount: 1 };
      }
      if (count > 1 && isStrict) {
        throw new Error(`Ambiguity error: Role '${config.role}' (name='${config.name}') matched ${count} elements.`);
      }
    }

    // Priority 3: Accessible Label
    if (config.label) {
      const loc = page.getByLabel(config.label, { exact: config.exact ?? true });
      const count = await loc.count();
      if (count === 1) {
        return { locator: loc, resolvedStrategy: 'label', resolvedPattern: config.label, matchCount: 1 };
      }
      if (count > 1 && isStrict) {
        throw new Error(`Ambiguity error: Label '${config.label}' matched ${count} elements.`);
      }
    }

    // Priority 4: Placeholder Text
    if (config.placeholder) {
      const loc = page.getByPlaceholder(config.placeholder, { exact: config.exact ?? true });
      const count = await loc.count();
      if (count === 1) {
        return { locator: loc, resolvedStrategy: 'placeholder', resolvedPattern: config.placeholder, matchCount: 1 };
      }
      if (count > 1 && isStrict) {
        throw new Error(`Ambiguity error: Placeholder '${config.placeholder}' matched ${count} elements.`);
      }
    }

    // Priority 5: Exact Visible Text
    if (config.text) {
      const loc = page.getByText(config.text, { exact: config.exact ?? true });
      const count = await loc.count();
      if (count === 1) {
        return { locator: loc, resolvedStrategy: 'text', resolvedPattern: config.text, matchCount: 1 };
      }
      if (count > 1 && isStrict) {
        throw new Error(`Ambiguity error: Text '${config.text}' matched ${count} elements.`);
      }
    }

    // Priority 6: Explicit CSS or XPath Selector string
    const selectorStr = config.selector || config.xpath;
    if (selectorStr) {
      const isXPath = selectorStr.startsWith('/') || selectorStr.startsWith('xpath=') || selectorStr.startsWith('(');
      const loc = page.locator(selectorStr);
      const count = await loc.count();
      if (count === 1) {
        return {
          locator: loc,
          resolvedStrategy: isXPath ? 'xpath' : 'css',
          resolvedPattern: selectorStr,
          matchCount: 1,
        };
      }
      if (count > 1 && isStrict) {
        throw new Error(`Ambiguity error: ${isXPath ? 'XPath' : 'CSS'} '${selectorStr}' matched ${count} elements.`);
      }
      if (count > 0 && !isStrict) {
        return { locator: loc.first(), resolvedStrategy: isXPath ? 'xpath' : 'css', resolvedPattern: selectorStr, matchCount: count };
      }
    }

    throw new Error(`Element could not be resolved with any deterministic selector strategy: ${JSON.stringify(config)}`);
  }

  private resolveExplicitStrategy(page: Page, config: SelectorConfig): Locator {
    switch (config.strategy) {
      case 'test_id':
        return page.getByTestId(config.test_id || config.selector || '');
      case 'role':
        return page.getByRole(config.role as any, config.name ? { name: config.name, exact: config.exact } : undefined);
      case 'label':
        return page.getByLabel(config.label || config.selector || '', { exact: config.exact });
      case 'placeholder':
        return page.getByPlaceholder(config.placeholder || config.selector || '', { exact: config.exact });
      case 'text':
        return page.getByText(config.text || config.selector || '', { exact: config.exact });
      case 'xpath':
        return page.locator(config.xpath || config.selector || '');
      case 'css':
      default:
        return page.locator(config.selector || '');
    }
  }

  private getPatternDescription(config: SelectorConfig): string {
    return config.selector || config.test_id || config.name || config.label || config.text || '';
  }
}

