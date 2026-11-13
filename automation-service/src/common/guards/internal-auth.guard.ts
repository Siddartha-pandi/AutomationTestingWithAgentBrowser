import { CanActivate, ExecutionContext, Injectable, UnauthorizedException } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';

@Injectable()
export class InternalAuthGuard implements CanActivate {
  constructor(private readonly configService: ConfigService) {}

  canActivate(context: ExecutionContext): boolean {
    const request = context.switchToHttp().getRequest();
    const providedKey = request.headers['x-internal-service-key'];
    const expectedKey = this.configService.get<string>('app.internalServiceKey');

    if (!providedKey || providedKey !== expectedKey) {
      throw new UnauthorizedException('Invalid or missing internal service authorization key.');
    }

    return true;
  }
}

