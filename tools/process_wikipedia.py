#!/usr/bin/env python3
import json
import os
from collections import defaultdict


def read_jsonl(path):
    items = []
    if not os.path.exists(path):
        return items
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            items.append(json.loads(line))
    return items


def write_jsonl(path, items):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=True) + "\n")


def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    seed_path = os.path.join(base_dir, "data", "seed", "seed_entities.jsonl")
    raw_path = os.path.join(base_dir, "data", "raw", "wikipedia_raw.jsonl")
    out_path = os.path.join(base_dir, "data", "processed", "entities.jsonl")

    seed_entities = read_jsonl(seed_path)
    raw_records = read_jsonl(raw_path)

    by_id = defaultdict(list)
    for rec in raw_records:
        ent_id = rec.get("id")
        if not ent_id:
            continue
        by_id[ent_id].append(rec)

    processed = []
    for ent in seed_entities:
        ent_id = ent.get("id")
        if not ent_id:
            continue
        merged = dict(ent)
        candidates = by_id.get(ent_id, [])
        if candidates:
            # Prefer zh extract, then en extract
            zh = next((c for c in candidates if c.get("lang") == "zh" and c.get("extract")), None)
            en = next((c for c in candidates if c.get("lang") == "en" and c.get("extract")), None)
            chosen = zh or en
            if chosen and not merged.get("description"):
                merged["description"] = chosen.get("extract")
            source_refs = merged.get("source_refs", [])
            if not isinstance(source_refs, list):
                source_refs = [source_refs]
            if chosen:
                if chosen.get("lang") == "zh":
                    source_refs.append("source.wikipedia_zh")
                elif chosen.get("lang") == "en":
                    source_refs.append("source.wikipedia_en")
            merged["source_refs"] = sorted(set(source_refs))
        processed.append(merged)

    write_jsonl(out_path, processed)
    print("Wrote:", out_path, "records:", len(processed))


if __name__ == "__main__":
    main()
