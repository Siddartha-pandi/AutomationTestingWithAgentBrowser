import { Module } from '@nestjs/common';
import { ArtifactManagerService } from './artifact-manager.service';

@Module({
  providers: [ArtifactManagerService],
  exports: [ArtifactManagerService],
})
export class ScreenshotsModule {}

