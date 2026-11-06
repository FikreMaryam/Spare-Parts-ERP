FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    fonts-sil-abyssinica \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-prod.txt .
RUN pip install --no-cache-dir -r requirements-prod.txt

COPY . .

ENV DEBUG=False
ENV USE_SQLITE=False

RUN SECRET_KEY=collectstatic-build-only-placeholder USE_SQLITE=True python manage.py collectstatic --noinput

EXPOSE 8000

CMD python manage.py migrate_schemas --noinput && gunicorn core.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 1 --timeout 120
