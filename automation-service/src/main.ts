import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';
import { Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';

async function bootstrap() {
  const logger = new Logger('AutomationServiceBootstrap');
  const app = await NestFactory.create(AppModule);

  app.enableCors({
    origin: '*',
    methods: 'GET,HEAD,PUT,PATCH,POST,DELETE',
  });

  app.enableShutdownHooks();

  const configService = app.get(ConfigService);
  const port = configService.get<number>('app.port') || 3001;

  await app.listen(port);
  logger.log(`================================================================`);
  logger.log(`🚀 NestJS Playwright Automation Service running on port ${port}`);
  logger.log(`   Healthcheck: http://localhost:${port}/health`);
  logger.log(`   Internal API: http://localhost:${port}/internal/v1/*`);
  logger.log(`================================================================`);
}

bootstrap();

