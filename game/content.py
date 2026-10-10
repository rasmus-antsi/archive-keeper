"""Everything the writer and artists edit lives in data/ and is loaded here.

data/game.json          interface text, the robot's lines, the shelves, credits
data/documents/*.json   one file per memory (a record you can step into)
data/archive.json       the real heritage records that fill the shelves
"""
import json
import os


def _load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


class Content:
    def __init__(self):
        self.game = _load("data/game.json")
        self.archive = _load("data/archive.json")
        self.documents = [_load(f"data/documents/{name}")
                          for name in sorted(os.listdir("data/documents")) if name.endswith(".json")]
        self.by_id = {d["id"]: d for d in self.documents}
        self.shelves = self.game["shelves"]
        for doc in self.documents:
            _check(doc, {s["id"] for s in self.shelves})

    def shelf_entries(self, shelf):
        """What a shelf holds: its memories first, then the plain archive records.

        Each entry is {"title", "sub", "record", "doc"}; doc is None for plain records.
        """
        entries = [{"title": d["title"], "sub": d.get("place", ""), "record": d.get("record", {}), "doc": d}
                   for d in self.documents if d["shelf"] == shelf["id"]]
        for rec in self.archive:
            if any(rec["folder"].startswith(prefix) for prefix in shelf.get("folders", [])):
                entries.append({"title": rec["name"], "sub": rec["folder"].split("/")[-1], "record": rec, "doc": None})
        return entries

    def shelf_documents(self, shelf):
        return [d for d in self.documents if d["shelf"] == shelf["id"]]


def _check(doc, shelf_ids):
    """Fail early, with the file's id in the message, when a document is put together wrong."""
    where = f"data/documents: '{doc.get('id', '?')}'"
    for key in ("id", "shelf", "title", "objects", "requests"):
        if key not in doc:
            raise ValueError(f"{where} is missing \"{key}\"")
    if doc["shelf"] not in shelf_ids:
        raise ValueError(f"{where} names shelf '{doc['shelf']}', which is not in data/game.json")
    objects = {o["id"] for o in doc["objects"]}
    npcs = {n["id"] for n in doc.get("npcs", [])}
    for req in doc["requests"]:
        if req["target"] not in objects:
            raise ValueError(f"{where} asks for '{req['target']}', which is not one of its objects")
        if "speaker" in req and req["speaker"] not in npcs:
            raise ValueError(f"{where} has a request spoken by unknown npc '{req['speaker']}'")
