import { Module } from '@nestjs/common';
import { LocatorResolverService } from './locator-resolver.service';

@Module({
  providers: [LocatorResolverService],
  exports: [LocatorResolverService],
})
export class SelectorsModule {}

