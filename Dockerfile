FROM python:3.10-slim

# Install system dependencies including GDAL
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    gdal-bin \
    libgdal-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Set GDAL environment variables
ENV GDAL_CONFIG=/usr/bin/gdal-config
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Collect static files with a dummy database URL (database not needed for static files)
ENV WILDEBACKYARD_API_DATABASE_URL="postgres://dummy:dummy@localhost/dummy"
RUN python manage.py collectstatic --noinput --settings=config.settings.wildebackyard_api || true

# Remove the dummy database URL so runtime uses the real one from app.yaml
ENV WILDEBACKYARD_API_DATABASE_URL=""

# Run gunicorn
CMD exec gunicorn -t 2400 -b :$PORT config.wsgi.wildebackyard_api:application
