import { Module } from '@nestjs/common';
import { AssertionExecutorService } from './assertion-executor.service';
import { SelectorsModule } from '../selectors/selectors.module';

@Module({
  imports: [SelectorsModule],
  providers: [AssertionExecutorService],
  exports: [AssertionExecutorService],
})
export class AssertionsModule {}

