import { chromium, Browser, Page } from 'playwright';
import { LocatorResolverService } from '../selectors/locator-resolver.service';
import { ActionExecutorService } from './action-executor.service';
import { AssertionExecutorService } from '../assertions/assertion-executor.service';

describe('Playwright Real Browser Automation Integration Test', () => {
  let browser: Browser;
  let page: Page;
  let resolver: LocatorResolverService;
  let actionExecutor: ActionExecutorService;
  let assertionExecutor: AssertionExecutorService;

  beforeAll(async () => {
    browser = await chromium.launch({ headless: true });
    resolver = new LocatorResolverService();
    actionExecutor = new ActionExecutorService(resolver);
    assertionExecutor = new AssertionExecutorService(resolver);
  });

  afterAll(async () => {
    if (browser) await browser.close();
  });

  beforeEach(async () => {
    page = await browser.newPage();
  });

  afterEach(async () => {
    if (page) await page.close();
  });

  it('navigates to data HTML, fills inputs, clicks buttons, and verifies assertions', async () => {
    const html = `
      <!DOCTYPE html>
      <html>
        <head><title>Test Automation Portal</title></head>
        <body>
          <h1 data-testid="heading">Welcome to Automation Testing</h1>
          <form id="login-form">
            <label for="username">Username</label>
            <input id="username" name="user" placeholder="Enter username" />

            <label for="newsletter">Subscribe</label>
            <input type="checkbox" id="newsletter" name="subscribe" />

            <button type="button" data-testid="submit-btn" role="button">Submit Form</button>
          </form>
          <div id="output" style="display:none;">Form Processed</div>
          <script>
            document.querySelector('[data-testid="submit-btn"]').addEventListener('click', () => {
              document.getElementById('output').style.display = 'block';
            });
          </script>
        </body>
      </html>
    `;

    await page.setContent(html);

    // 1. Assert Heading is Visible via test_id
    const headingAssert = await assertionExecutor.execute(page, {
      assertion: 'element_visible',
      config: { strategy: 'test_id', test_id: 'heading' },
    });
    expect(headingAssert.success).toBe(true);

    // 2. Fill Input using label locator
    const fillResult = await actionExecutor.execute(page, {
      action: 'fill',
      config: { strategy: 'label', label: 'Username', value: 'playwright_user' },
    });
    expect(fillResult.success).toBe(true);

    // 3. Verify input value equals
    const valAssert = await assertionExecutor.execute(page, {
      assertion: 'input_value_equals',
      config: { strategy: 'label', label: 'Username', expected_value: 'playwright_user' },
    });
    expect(valAssert.success).toBe(true);

    // 4. Check checkbox using label
    const checkResult = await actionExecutor.execute(page, {
      action: 'check',
      config: { strategy: 'label', label: 'Subscribe' },
    });
    expect(checkResult.success).toBe(true);

    // 5. Click Submit button using role + name
    const clickResult = await actionExecutor.execute(page, {
      action: 'click',
      config: { strategy: 'role', role: 'button', name: 'Submit Form' },
    });
    expect(clickResult.success).toBe(true);

    // 6. Assert text equals
    const textAssert = await assertionExecutor.execute(page, {
      assertion: 'text_equals',
      config: { selector: '#output', expected_text: 'Form Processed' },
    });
    expect(textAssert.success).toBe(true);
  });
});
