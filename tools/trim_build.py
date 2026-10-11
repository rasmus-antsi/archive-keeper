"""Removes from a COPY of the game what no shelf shows, so the browser has less to
download: the archive records that stand on no shelf, and their photographs.

    python tools/trim_build.py <folder holding the copy's game/, data/ and assets/>

The Dockerfile runs it on the copy it builds from. Which records stand on a shelf
is asked of the game itself (game/content.py), so the two cannot disagree.
"""
import json
import os
import sys

root = os.path.abspath(sys.argv[1])
if os.path.isdir(os.path.join(root, ".git")):
    sys.exit("this is the repository itself; give it a copy")
os.chdir(root)
sys.path.insert(0, root)
sys.dont_write_bytecode = True          # no __pycache__ left behind in the copy
from game.content import Content

content = Content()
kept = {entry["record"]["id"]: entry["record"]
        for shelf in content.shelves for entry in content.shelf_entries(shelf) if entry["doc"] is None}
used = {record.get(key) for record in kept.values() for key in ("image", "thumb")}

removed = 0
for folder, _, names in os.walk("assets/img/arc"):
    for name in names:
        path = os.path.join(folder, name)
        if os.path.relpath(path, "assets/img").replace(os.sep, "/") not in used:
            os.remove(path)
            removed += 1
with open("data/archive.json", "w", encoding="utf-8") as f:
    json.dump([record for record in content.archive if record["id"] in kept], f, ensure_ascii=False)
print(f"kept {len(kept)} of {len(content.archive)} records, removed {removed} files")
