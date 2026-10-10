# Builds the browser version with pygbag and serves it as static files.
FROM python:3.12-slim AS build
RUN pip install --no-cache-dir pygbag==0.9.3
WORKDIR /src
COPY main.py archive-keeper/
COPY game archive-keeper/game
COPY data archive-keeper/data
COPY assets archive-keeper/assets
COPY web/pygbag.tmpl pygbag.tmpl
RUN python -m pygbag --build --title "Archive Keeper" --template /src/pygbag.tmpl archive-keeper

FROM caddy:2-alpine
COPY Caddyfile /etc/caddy/Caddyfile
COPY --from=build /src/archive-keeper/build/web /srv
