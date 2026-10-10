"""Builds the in-game archive from the HUM hackathon sample datasets.

venv/bin/python tools/fetch_archive.py <folder with fu.csv, courts.csv, buildings.csv>

Writes data/archive.json (one entry per real record) and, for museum objects,
downloads the first public image from MuIS into assets/img/arc/ (640 px) and
assets/img/arc/t/ (thumbnail). Each entry keeps its source link and the
rights statement MuIS gives for that image.
"""
import csv
import io
import json
import os
import re
import sys
import time
import urllib.request

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame

pygame.init()
pygame.display.set_mode((1, 1))
csv.field_size_limit(10 ** 9)
SRC = sys.argv[1]
OUT_IMG = "assets/img/arc"
os.makedirs(f"{OUT_IMG}/t", exist_ok=True)

PEOPLE = {
    "mari": "Marid", "udmurdi": "Udmurdid", "udmurdid": "Udmurdid", "mordva": "Mordvalased",
    "ersa-mordva": "Mordvalased", "mokša-mordva": "Mordvalased", "vepsa": "Vepslased", "liivi": "Liivlased",
    "isuri": "Isurid", "komi": "Komid", "saami": "Saamid", "handi": "Handid", "karjala": "Karjalased",
    "vadja": "Vadjalased", "mansi": "Mansid", "ungari": "Ungarlased", "soome": "Soomlased", "neenetsi": "Neenetsid",
}


def clean(s):
    return re.sub(r"\s+", " ", (s or "").replace("\xa0", " ")).strip().strip(";").strip()


def get(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "arhiivihoidja-gamejam/0.1"})
            return urllib.request.urlopen(req, timeout=30).read()
        except Exception as e:
            if i == tries - 1:
                print("  failed", url, type(e).__name__)
                return None
            time.sleep(1.5)


def fit(surf, w, h):
    k = min(w / surf.get_width(), h / surf.get_height(), 1.0)
    return pygame.transform.smoothscale(surf, (max(1, round(surf.get_width() * k)), max(1, round(surf.get_height() * k))))


def museum_objects():
    objs = {}
    for r in csv.DictReader(open(f"{SRC}/fu.csv", encoding="utf-8")):
        o = objs.setdefault(r["object_id"], dict(r, texts=[]))
        text = clean(r["description_text"]).strip('"')
        if text and (r["description_type_label"], text) not in o["texts"]:
            o["texts"].append((r["description_type_label"] or "märkus", text))
    out = []
    for n, o in enumerate(objs.values()):
        oid = o["object_id"]
        people = clean(o["people_names"])
        if "," in people:
            folder = "Mitu rahvast"
        elif people.lower() in ("", "hõimurahvad"):
            folder = "Määramata"
        else:
            folder = PEOPLE.get(people.lower(), people.capitalize())
        number = clean(o["museaali_number"])
        m = re.match(r"(ERM [A-Z]+ \d+)", number)
        entry = {
            "id": f"muis-{oid}", "kind": "museaal", "folder": f"Hõimurahvad/{folder}",
            "name": f"{number} {clean(o['title_clean'])}", "title": clean(o["title_clean"]),
            "group": m.group(1) if m else number,
            "fields": [["Number", number], ["Nimetus", clean(o["title_clean"])], ["Rahvas", people],
                       ["Materjal", clean(o["material"])], ["Koht", clean(o["places"])],
                       ["Kogutud", clean(o["collection_date_raw"])], ["Koguja", clean(o["collectors"])]],
            "texts": [[t, x] for t, x in o["texts"]],
            "source": f"http://opendata.muis.ee/object/{oid}", "image": None, "rights": "",
        }
        path = f"{OUT_IMG}/{oid}.jpg"
        if not os.path.exists(path):
            listing = (get(f"http://opendata.muis.ee/media-list/{oid}") or b"").decode("utf-8", "ignore")
            items = re.findall(r'rdf:about="(http://opendata\.muis\.ee/dhmedia/[^"]+)">\s*<dcterms:rights>(.*?)</dcterms:rights>\s*'
                               r"<dcterms:format>(.*?)</dcterms:format>", listing, flags=re.S)
            jpgs = [(u, clean(r)) for u, r, f in items if "jp" in f]
            if jpgs:
                raw = get(jpgs[0][0])
                try:
                    img = pygame.image.load(io.BytesIO(raw), "x.jpg").convert()
                    pygame.image.save(fit(img, 640, 640), path)
                    pygame.image.save(fit(img, 132, 96), f"{OUT_IMG}/t/{oid}.jpg")
                    with open(f"{OUT_IMG}/{oid}.txt", "w", encoding="utf-8") as f:
                        f.write(jpgs[0][1] + "\n" + jpgs[0][0] + "\n")
                except Exception as e:
                    print("  bad image", oid, type(e).__name__)
            time.sleep(0.15)
        if os.path.exists(path):
            entry["image"] = f"arc/{oid}.jpg"
            entry["thumb"] = f"arc/t/{oid}.jpg"
            if os.path.exists(f"{OUT_IMG}/{oid}.txt"):
                lines = open(f"{OUT_IMG}/{oid}.txt", encoding="utf-8").read().split("\n")
                entry["rights"], entry["image_source"] = lines[0], lines[1]
        out.append(entry)
        if n % 20 == 0:
            print(f"  objects {n}/{len(objs)}", flush=True)
    return out


def courts():
    out = []
    for r in csv.DictReader(open(f"{SRC}/courts.csv", encoding="utf-8"), delimiter="\t"):
        text = re.sub(r"<[^>]+>", "", r["text"]).replace("&lt;", "<").replace("&gt;", ">")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n\s*\n+", "\n", text).strip()
        date = f"{int(r['day']):02d}.{int(r['month']):02d}.{r['year']}"
        kind = clean(re.sub(r"\d+\.\s*", "", r["_record_type"]))
        out.append({
            "id": f"vk-{r['id']}", "kind": "protokoll", "folder": f"Vallakohtud/{r['maakond']}maa",
            "name": f"{r['vald']} {r['year']} · kirje {r['id']}", "title": f"{r['vald']} vallakohus, {date}",
            "group": f"{r['vald']} vallakohus",
            "fields": [["Kirje", r["id"]], ["Kohus", f"{r['vald']} vallakohus"], ["Kuupäev", date], ["Liik", kind],
                       ["Maakond", r["maakond"]], ["Kihelkond", r["kihelkond"]],
                       ["Kohtumehed", clean(r["jury"]).replace("-", " – ")]],
            "texts": [["protokoll", text]],
            "source": f"https://www.ra.ee/vallakohtud/index.php/record/view?id={r['id']}", "image": None,
            "rights": "Rahvusarhiiv, vallakohtute protokollide ühisloome",
        })
    return out


def buildings():
    out = []
    for r in csv.DictReader(open(f"{SRC}/buildings.csv", encoding="utf-8"), delimiter="|"):
        owners = []
        try:
            for o in json.loads(r["Projekti tellija \\ Omanikud"]):
                name = " ".join(x for x in (o.get("Eesnimi"), (o.get("Perenimi") or "").title()) if x) or o.get("Asutus") or ""
                if o.get("Amet"):
                    name += f" ({o['Amet']})"
                owners.append((name, o.get("Omanik 1940") == "Jah"))
        except (ValueError, TypeError):
            pass
        flats = [f"{v} × {k.split('-')[0]}-toaline" for k, v in r.items() if "toalisi" in k and "uues" in k and v]
        street = clean(f"{r['Tänav (uus)']} {r['Maja nr. (uus)']}")
        d = r["Projekti kinnitamise kuupäev"]
        date = f"{d[8:10]}.{d[5:7]}.{d[:4]}" if d else ""
        what = r["Otstarve"]
        out.append({
            "id": f"eaa-{r['id']}", "kind": "ehitusprojekt", "folder": "Tartu ehitusprojektid/1887",
            "name": f"projekt {r['Projekti nr.']} · {what}" + (f", {street}" if street else ""),
            "title": f"{what.capitalize()}" + (f", {street}" if street else ""), "group": r["refcode"],
            "fields": [["Viide", f"{r['refcode']}, l {r['Lehekülg']}"], ["Projekti nr", r["Projekti nr."]],
                       ["Aadress", street], ["Otstarve", what], ["Ehituse tüüp", r["Ehituse tüüp"]],
                       ["Välisseinad", r["Välisseina materjal"]], ["Vaheseinad", r["Vaheseina materjal"]],
                       ["Küte", r["Küte"]], ["Kuivkäimla", r["Kuivkäimla"]], ["Korruseid", r["Korruseid uues"]],
                       ["Korterid", ", ".join(flats)], ["Tellija", ", ".join(n for n, later in owners if not later)],
                       ["Omanik 1940", ", ".join(n for n, later in owners if later)], ["Kinnitatud", date]],
            "texts": [],
            "source": "https://www.ra.ee/apps/hooned/", "image": None,
            "rights": "Rahvusarhiiv, Tartu ehitusprojektide andmebaas",
        })
    return out


if __name__ == "__main__":
    files = museum_objects() + courts() + buildings()
    for f in files:
        f["fields"] = [[k, v] for k, v in f["fields"]]
    with open("data/archive.json", "w", encoding="utf-8") as f:
        json.dump(files, f, ensure_ascii=False, indent=1)
    with_img = sum(1 for x in files if x["image"])
    print(f"wrote data/archive.json: {len(files)} files, {with_img} with images")
