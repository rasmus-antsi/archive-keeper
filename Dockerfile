# Builds the browser version with pygbag and serves it as static files.
FROM python:3.12-slim AS build
RUN pip install --no-cache-dir pygbag==0.9.3
WORKDIR /src
COPY main.py archive-keeper/
COPY game archive-keeper/game
COPY data archive-keeper/data
COPY assets archive-keeper/assets
RUN python -m pygbag --build --title "Archive Keeper" archive-keeper \
    && rm -f archive-keeper/build/web/*.tar.gz

FROM caddy:2-alpine
COPY Caddyfile /etc/caddy/Caddyfile
COPY --from=build /src/archive-keeper/build/web /srv
