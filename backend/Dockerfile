FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt requirements-prod.txt ./
RUN pip install --no-cache-dir -r requirements-prod.txt

COPY . .

# Run as an unprivileged user. Secrets (HEALTHSITES_API_KEY, DJANGO_SECRET_KEY, ...)
# are never baked into the image: pass them at runtime (env vars or --env-file).
RUN useradd --create-home --uid 10001 app && chown -R app /app
USER app

EXPOSE 8000

CMD ["gunicorn", "-c", "gunicorn.conf.py", "backend.wsgi:application"]
