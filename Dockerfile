FROM python:3.11.14-slim-bookworm AS build
WORKDIR /build
COPY requirements.txt requirements-build.txt ./
RUN python -m pip install --no-cache-dir -r requirements-build.txt \
    && python -m pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt
COPY openapi/ ./openapi/
COPY scripts/generate_schemas.sh ./scripts/generate_schemas.sh
RUN sh scripts/generate_schemas.sh

FROM python:3.11.14-slim-bookworm AS runtime
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
COPY --from=build /wheels /wheels
COPY requirements.txt ./
RUN python -m pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt \
    && rm -rf /wheels \
    && groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --no-create-home app
COPY --from=build /build/generated/ ./generated/
COPY app/ ./app/
COPY db/ ./db/
COPY tests/ ./tests/
COPY gunicorn.conf.py ./
ARG SOURCE_REVISION=unknown
LABEL org.opencontainers.image.revision=$SOURCE_REVISION
USER app
EXPOSE 8000
STOPSIGNAL SIGTERM
CMD ["gunicorn", "--config", "gunicorn.conf.py", "app.main:app"]
