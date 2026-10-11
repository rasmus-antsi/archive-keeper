# Allikad ja õigused

Iga pärandmaterjali kohta üks rida: mis, kust, mis tingimustel. Lisa siia kohe, kui midagi uut võtad.
Kirjete tekstid ja viited on failis `data/records.json`.

| Fail | Mis | Allikas | Õigused |
|---|---|---|---|
| assets/img/rec/kolk.jpg | Kolk, öövalvuri, ERM B 171:85 | http://opendata.muis.ee/object/620951 · pilt http://opendata.muis.ee/dhmedia/106d61c1-5ece-47be-a61c-f6a79ebe2a10 | MuIS: „Teosele ei rakendu teadaolevalt autoriõigustega seotud piirangud.“ |
| assets/img/rec/ankur.jpg | Võrgu otsimise ankur, ERM B 68:73 | http://opendata.muis.ee/object/620482 · pilt http://opendata.muis.ee/dhmedia/8c9017cb-c485-4c53-a95b-718cf0ae67f2 | sama |
| assets/img/rec/roos.jpg | „Rasvakaku roos“, ERM B 18:30 | http://opendata.muis.ee/object/636429 · pilt http://opendata.muis.ee/dhmedia/d2c15d1c-451f-4a1b-91b8-19817e35b8e7 | sama |
| assets/img/rec/peakorv.jpg | Peakorv, mesiniku, ERM B 18:32 | http://opendata.muis.ee/object/636431 · pilt http://opendata.muis.ee/dhmedia/bc89faa0-cba4-4498-8aef-7b037aff0d4d | sama |
| data/records.json (hõimusaal) | Museaalide kirjeldused (nimetus, materjal, koht, koguja, legend) | HUM-häkatoni näidisandmestik „Objects of Finno-Ugric Peoples“ / MuIS | Metaandmed CC0 |
| data/records.json (vallasaal), assets/img/rec/{koiola,sauga,keila,padi}.png | Vallakohtu protokollid, kirjed 119032, 91286, 113993, 97222 (tekst) | https://www.ra.ee/vallakohtud/ · HUM-häkatoni näidisandmestik „Parish Court Records“ | KONTROLLIDA – litsentsi lehel ei leidnud |
| data/records.json (linnasaal) | Ehitusprojektid EAA.2623.1.125, lehed 90, 91, 92, 94 (andmed) | https://www.ra.ee/apps/hooned/ · HUM-häkatoni näidisandmestik „Building Designs in Tartu“ | KONTROLLIDA – litsentsi lehel ei leidnud |
| assets/fonts/CrimsonText-*.ttf | Kirjatüüp Crimson Text | https://github.com/google/fonts/tree/main/ofl/crimsontext | SIL OFL 1.1 |
| assets/fonts/Jersey10-Regular.ttf | Kirjatüüp Jersey 10 (pikslikiri: menüüd, vihjed, kõnekastid) | https://github.com/google/fonts/tree/main/ofl/jersey10 | SIL OFL 1.1 |
| assets/fonts/UnifrakturMaguntia-Book.ttf | Kirjatüüp UnifrakturMaguntia | https://github.com/google/fonts/tree/main/ofl/unifrakturmaguntia | SIL OFL 1.1 |
| assets/snd/tick.ogg | Menüü klõps | koodiga genereeritud: `tools/make_tick.py` | tiimi enda tehtud |
| favicon.png | Brauseri vahekaardi ja akna ikoon | tehtud tiimi kummituse pildist: `tools/make_icon.py` | tiimi enda tehtud |

## Kogu arhiiv mängus

`data/archive.json` sisaldab kõiki kolme näidisandmestiku kirjeid: 171 museaali (MuIS), 6 vallakohtu protokolli ja 6 Tartu ehitusprojekti. Iga kirje juures on allikaviide. 151 museaalil on pilt kaustas `assets/img/arc/`; iga pildi kõrval on samanimeline `.txt` fail MuISi õiguste märkuse ja pildi aadressiga (kõigil 151-l: „Teosele ei rakendu teadaolevalt autoriõigustega seotud piirangud.“). Uuesti tõmbamiseks: `tools/fetch_archive.py`.

Mäng tühjendab osa välju ise (`data/cases.json`); päris andmeid ei ole muudetud.

Riiulitel on mängus 24 kirjet: Tartu ehitusprojektid (6), vallakohtud (6) ja kummaltki hõimurahvaste riiulilt 6 välja valitud museaali (`data/game.json`, "shelves" → "records"). Ülejäänud kirjed on failis alles, aga brauseriversioonist jätab `tools/trim_build.py` need ja nende pildid välja.

## Tiimi joonistatud pildid

Originaalid on kaustas `art-src/` (Drive'i kaustad Objektid ja Raamatukogu); mängu failid teeb neist `tools/import_art.py`: esemete suured pildid (`assets/img/objektid`), Raekoja platsi talvine vaade ja arhiivi mööbel (`assets/img/props`).

## Veel tegemata

- **Päikesekell-kompassi museaali link ja õiguste rida puudub** (`data/documents/meremehe-poeg.json`, "record" → "source"). Seni mäng allikarida ei näita.
- Trükimasinal ja kirjapakil ei ole joonistatud pilti; mängus on koodis joonistatud ikoon.

- Linnasaal: päris plaanide skaneeringud puuduvad (praegu joonistatud asenduspildid).
- Vallasaal: protokollilehtede skaneeringud puuduvad (praegu ärakiri tekstist).
- Sauga protokolli (1865) tänapäevane ümberjutustus vajab ajaloolase või keeleinimese pilku.

## Tehisaru kasutus

Kood ja koodis joonistatud asenduspildid (sh trükimasina ja kirjapaki ikoon) on tehtud Claude Code'i abil. Sissejuhatuse, roboti, lõpuekraani ja mälestuste tekstid, muusika, heliefektid ja pildid (assets/music, assets/snd/{wrong,restore,page*}.ogg, assets/img/tegelased, assets/img/objektid) on tiimi enda tehtud; ülejäänud helid kaustas assets/snd on koodiga genereeritud. Tekstid vajavad inimese ülelugemist.
