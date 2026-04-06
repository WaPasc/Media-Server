# STAGE 1: Builder
FROM python:3.12-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create a Python virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory for the build
WORKDIR /build

# COPY dependency files AND the src directory so pip can package it
COPY pyproject.toml ./
COPY src/ ./src/

# INSTALL the dependencies into the virtual environment
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir . 


# STAGE 2: Runner (Production Image)
FROM python:3.12-slim 

# Install runtime dependencies (PostgreSQL libs AND ffmpeg for media parsing)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy the populated virtual environment from the builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create a non-root user and group for security
RUN groupadd -g 1000 appgroup && \
    useradd -u 1000 -g appgroup -s /bin/bash -m appuser

# Set the working directory
WORKDIR /app

# Create directories for the app, database (if SQLite), and media
RUN mkdir -p /app/data /media && \
    chown -R appuser:appgroup /app /media

# Copy the rest of the application code
COPY --chown=appuser:appgroup . .

# Tell Python exactly where the source code is
ENV PYTHONPATH="/app/src"

# Switch to the non-root user
USER appuser

# Expose the port FastAPI runs on
EXPOSE 8000

# Make the entrypoint script executable
RUN chmod +x entrypoint.sh

# Start the application via the entrypoint script
CMD ["./entrypoint.sh"]