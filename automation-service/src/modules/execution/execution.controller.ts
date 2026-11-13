import { Body, Controller, Get, HttpCode, HttpStatus, Param, Post, UseGuards } from '@nestjs/common';
import { ExecutionService } from './execution.service';
import { InternalAuthGuard } from '../../common/guards/internal-auth.guard';

@Controller()
export class ExecutionController {
  constructor(private readonly executionService: ExecutionService) {}

  @Get('health')
  @HttpCode(HttpStatus.OK)
  async rootHealth() {
    return this.executionService.getHealthStatus();
  }

  @Get('internal/v1/health')
  @HttpCode(HttpStatus.OK)
  async internalHealth() {
    return this.executionService.getHealthStatus();
  }

  @Post('internal/v1/jobs/execute')
  @UseGuards(InternalAuthGuard)
  @HttpCode(HttpStatus.ACCEPTED)
  async submitExecutionJob(@Body() payload: unknown) {
    return this.executionService.submitExecution(payload);
  }

  @Post('internal/v1/jobs/:execution_id/cancel')
  @UseGuards(InternalAuthGuard)
  @HttpCode(HttpStatus.OK)
  async cancelExecutionJob(@Param('execution_id') executionId: string) {
    return this.executionService.cancelExecution(executionId);
  }
}

