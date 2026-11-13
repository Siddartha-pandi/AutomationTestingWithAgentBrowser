import { Injectable, Logger } from '@nestjs/common';
import { Page } from 'playwright';
import * as fs from 'fs';
import * as path from 'path';
import * as crypto from 'crypto';

export interface ArtifactRecord {
  id: string;
  type: 'screenshot' | 'trace' | 'video' | 'dom_snapshot';
  file_path: string;
  file_size_bytes: number;
  sha256_hash: string;
  created_at: string;
}

@Injectable()
export class ArtifactManagerService {
  private readonly logger = new Logger(ArtifactManagerService.name);

  async captureScreenshot(
    page: Page,
    executionId: string,
    stepId: string,
    storageDir: string,
    fullPage = false,
  ): Promise<ArtifactRecord | null> {
    try {
      if (page.isClosed()) return null;

      const targetDir = path.join(storageDir, 'screenshots', executionId);
      fs.mkdirSync(targetDir, { recursive: true });

      const fileName = `${stepId}_${Date.now()}.png`;
      const filePath = path.join(targetDir, fileName);

      await page.screenshot({ path: filePath, fullPage });

      const fileBuffer = fs.readFileSync(filePath);
      const sha256 = crypto.createHash('sha256').update(fileBuffer).digest('hex');

      return {
        id: crypto.randomUUID(),
        type: 'screenshot',
        file_path: filePath,
        file_size_bytes: fileBuffer.length,
        sha256_hash: sha256,
        created_at: new Date().toISOString(),
      };
    } catch (err: any) {
      this.logger.warn(`Failed to capture screenshot: ${err.message}`);
      return null;
    }
  }

  async saveDOMSnapshot(
    page: Page,
    executionId: string,
    stepId: string,
    storageDir: string,
  ): Promise<ArtifactRecord | null> {
    try {
      if (page.isClosed()) return null;

      const targetDir = path.join(storageDir, 'dom', executionId);
      fs.mkdirSync(targetDir, { recursive: true });

      const html = await page.content();
      const fileName = `${stepId}_${Date.now()}.html`;
      const filePath = path.join(targetDir, fileName);

      fs.writeFileSync(filePath, html, 'utf-8');
      const sha256 = crypto.createHash('sha256').update(html, 'utf-8').digest('hex');

      return {
        id: crypto.randomUUID(),
        type: 'dom_snapshot',
        file_path: filePath,
        file_size_bytes: Buffer.byteLength(html, 'utf-8'),
        sha256_hash: sha256,
        created_at: new Date().toISOString(),
      };
    } catch (err: any) {
      this.logger.warn(`Failed to save DOM snapshot: ${err.message}`);
      return null;
    }
  }
}

