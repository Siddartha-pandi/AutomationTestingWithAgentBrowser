import { Module } from '@nestjs/common';
import { ActionExecutorService } from './action-executor.service';
import { SelectorsModule } from '../selectors/selectors.module';

@Module({
  imports: [SelectorsModule],
  providers: [ActionExecutorService],
  exports: [ActionExecutorService],
})
export class ActionsModule {}

