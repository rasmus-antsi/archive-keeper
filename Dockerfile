# Builds the browser version with pygbag and serves it as static files.
FROM python:3.12-slim AS build
RUN pip install --no-cache-dir pygbag==0.9.3
WORKDIR /src
COPY main.py archive-keeper/
COPY game archive-keeper/game
COPY data archive-keeper/data
COPY assets archive-keeper/assets
COPY web/pygbag.tmpl favicon.png ./
# Left over from earlier versions of the game and no longer opened by it: without them
# the page has 3 MB less to download. Named one by one so that new art is never caught.
RUN cd archive-keeper && rm -rf data/levels data/records.json data/cases.json \
    assets/img/rec assets/img/maps assets/img/npc assets/img/obj assets/img/arc/*.txt \
    assets/img/card.png assets/img/ghost.png assets/img/map.png \
    assets/img/static_0.png assets/img/static_1.png assets/img/static_2.png assets/img/static_3.png \
    assets/img/visitor_0.png assets/img/visitor_1.png assets/img/visitor_2.png assets/img/visitor_3.png \
    assets/img/visitor_4.png
RUN python -m pygbag --build --title "Archive Keeper" --icon /src/favicon.png --template /src/pygbag.tmpl archive-keeper

FROM caddy:2-alpine
COPY Caddyfile /etc/caddy/Caddyfile
COPY --from=build /src/archive-keeper/build/web /srv
# the loading page is written in the game's two typefaces before the game itself has arrived
COPY assets/fonts/UnifrakturMaguntia-Book.ttf assets/fonts/Jersey10-Regular.ttf /srv/fonts/
