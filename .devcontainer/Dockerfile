# Official Microsoft Python 3.11 Dev Container Base Image (Debian Bookworm)
FROM mcr.microsoft.com/devcontainers/python:1-3.11-bookworm

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# 1. Install Linux system libraries, build tools, postgresql-client, and browser dependencies for agent-browser (Chromium)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gnupg \
    ca-certificates \
    postgresql-client \
    git \
    procps \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    fonts-liberation \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# 2. Install Node.js 20 LTS & agent-browser CLI globally
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install -g agent-browser@0.41.2 \
    && rm -rf /var/lib/apt/lists/*

# 3. Verify toolchain installations
RUN node --version \
    && npm --version \
    && python --version \
    && agent-browser --version

