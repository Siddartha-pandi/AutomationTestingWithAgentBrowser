import { registerAs } from '@nestjs/config';

export const appConfig = registerAs('app', () => ({
  port: parseInt(process.env.AUTOMATION_SERVICE_PORT || '3001', 10),
  internalServiceKey: process.env.INTERNAL_SERVICE_KEY || 'enterprise-internal-secret-service-key-32chars',
  storageDir: process.env.STORAGE_DIR || (process.platform === 'win32' ? 'C:\\Prama\\AutomationTestingWithAgentBrowser\\reports' : '/app/reports'),
  defaultTimeoutMs: parseInt(process.env.BROWSER_TIMEOUT_MS || '30000', 10),
  databaseUrl: process.env.DATABASE_URL || 'postgresql://postgres:postgres@localhost:5432/automation_platform_db',
  redis: {
    host: process.env.REDIS_HOST || '127.0.0.1',
    port: parseInt(process.env.REDIS_PORT || '6379', 10),
    password: process.env.REDIS_PASSWORD || undefined,
    db: parseInt(process.env.REDIS_DB || '0', 10),
  },
  worker: {
    concurrency: parseInt(process.env.WORKER_CONCURRENCY || '2', 10),
  },
}));

