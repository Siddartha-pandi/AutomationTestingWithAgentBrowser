import { chromium, Browser, BrowserContext, Page } from 'playwright';
import * as fs from 'fs';
import * as path from 'path';
import { LocatorResolverService } from '../selectors/locator-resolver.service';
import { ActionExecutorService } from './action-executor.service';
import { AssertionExecutorService } from '../assertions/assertion-executor.service';
import { ContextManagerService } from '../browser/context-manager.service';
import { ArtifactManagerService } from '../screenshots/artifact-manager.service';

describe('Comprehensive Browser Test Scenarios (Playwright Native)', () => {
  let browser: Browser;
  let contextManager: ContextManagerService;
  let artifactManager: ArtifactManagerService;
  let resolver: LocatorResolverService;
  let actionExecutor: ActionExecutorService;
  let assertionExecutor: AssertionExecutorService;
  const tempDir = path.join(process.cwd(), 'temp_test_reports');

  beforeAll(async () => {
    browser = await chromium.launch({ headless: true });
    contextManager = new ContextManagerService();
    artifactManager = new ArtifactManagerService();
    resolver = new LocatorResolverService();
    actionExecutor = new ActionExecutorService(resolver);
    assertionExecutor = new AssertionExecutorService(resolver);
    fs.mkdirSync(tempDir, { recursive: true });
  });

  afterAll(async () => {
    if (browser) await browser.close();
    try {
      fs.rmSync(tempDir, { recursive: true, force: true });
    } catch {}
  });

  it('verifies Chromium launch, isolated context creation, and tracing', async () => {
    expect(browser.isConnected()).toBe(true);

    const session = await contextManager.createIsolatedContext(
      browser,
      'test-session-1',
      {
        browser_type: 'chromium',
        headless: true,
        viewport: { width: 1280, height: 800 },
        record_video: false,
        record_trace: true,
        timeout_ms: 10000,
      },
      tempDir,
    );

    expect(session.context).toBeDefined();
    const page = await session.context.newPage();
    await page.setContent('<h1>Tracing Verification</h1>');
    await session.close();

    if (session.tracePath) {
      expect(fs.existsSync(session.tracePath)).toBe(true);
    }
  });

  it('executes role, label, and test_id locators with actions and assertions', async () => {
    const page = await browser.newPage();
    const html = `
      <!DOCTYPE html>
      <html>
        <head><title>Scenario Testing Portal</title></head>
        <body>
          <h2 data-testid="portal-header">Enterprise Test Suite</h2>
          <label for="country">Select Country</label>
          <select id="country" name="country">
            <option value="us">United States</option>
            <option value="in">India</option>
            <option value="de">Germany</option>
          </select>
          <label for="comments">Comments</label>
          <textarea id="comments" placeholder="Add remarks"></textarea>
          <input type="file" id="uploader" data-testid="file-upload" />
          <button role="button">Submit Feedback</button>
        </body>
      </html>
    `;
    await page.setContent(html);

    // Locate by test ID
    const headerAssert = await assertionExecutor.execute(page, {
      assertion: 'element_visible',
      config: { strategy: 'test_id', test_id: 'portal-header' },
    });
    expect(headerAssert.success).toBe(true);

    // Select dropdown option
    const selectRes = await actionExecutor.execute(page, {
      action: 'select',
      config: { strategy: 'label', label: 'Select Country', value: 'in' },
    });
    expect(selectRes.success).toBe(true);

    // Fill placeholder
    const fillRes = await actionExecutor.execute(page, {
      action: 'fill',
      config: { strategy: 'placeholder', placeholder: 'Add remarks', value: 'Automated test feedback' },
    });
    expect(fillRes.success).toBe(true);

    // Click by role
    const clickRes = await actionExecutor.execute(page, {
      action: 'click',
      config: { strategy: 'role', role: 'button', name: 'Submit Feedback' },
    });
    expect(clickRes.success).toBe(true);

    // Screenshot capture
    const screenshot = await artifactManager.captureScreenshot(page, 'test-exec-2', 'step-1', tempDir);
    expect(screenshot).not.toBeNull();
    expect(screenshot?.sha256_hash).toBeDefined();

    await page.close();
  });

  it('strictly rejects ambiguous selectors matching multiple elements', async () => {
    const page = await browser.newPage();
    const html = `
      <div>
        <button class="action-btn">Duplicate Button</button>
        <button class="action-btn">Duplicate Button</button>
      </div>
    `;
    await page.setContent(html);

    await expect(
      resolver.resolve(page, { selector: '.action-btn', strict: true }),
    ).rejects.toThrow(/Ambiguity error|Ambiguous element/);

    await page.close();
  });

  it('handles missing selectors deterministically with detailed error message', async () => {
    const page = await browser.newPage();
    await page.setContent('<div>No buttons here</div>');

    await expect(
      resolver.resolve(page, { strategy: 'role', role: 'button', name: 'Non Existent' }),
    ).rejects.toThrow(/Element not found/);

    await page.close();
  });

  it('handles navigation timeouts gracefully', async () => {
    const page = await browser.newPage();

    // Navigate with a tiny timeout to an unroutable port
    const res = await actionExecutor.execute(page, {
      action: 'navigate',
      config: { url: 'http://127.0.0.1:59999/unreachable', timeout_ms: 100 },
    });

    expect(res.success).toBe(false);
    expect(res.error).toBeDefined();
    await page.close();
  });
});

