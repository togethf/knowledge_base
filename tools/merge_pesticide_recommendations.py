#!/usr/bin/env python3
import hashlib
import json
import os


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


def slug_id(name):
    h = hashlib.md5(name.encode("utf-8")).hexdigest()[:8]
    return f"pesticide.ai_{h}"


def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    rec_path = os.path.join(base_dir, "data", "processed", "pesticide_recommendations.jsonl")
    rel_path = os.path.join(base_dir, "data", "processed", "relations.jsonl")
    seed_rel_path = os.path.join(base_dir, "data", "seed", "seed_relations.jsonl")
    proc_ent_path = os.path.join(base_dir, "data", "processed", "entities.jsonl")
    seed_ent_path = os.path.join(base_dir, "data", "seed", "seed_entities.jsonl")

    recs = read_jsonl(rec_path)
    relations = read_jsonl(rel_path) or read_jsonl(seed_rel_path)
    entities = read_jsonl(proc_ent_path) or read_jsonl(seed_ent_path)

    ent_index = {e.get("id"): e for e in entities}
    rel_keys = {(r.get("type"), r.get("from"), r.get("to"), r.get("dosage")) for r in relations}

    added_rel = 0
    for rec in recs:
        pest_id = rec.get("pest_id")
        ai = rec.get("active_ingredient")
        if not pest_id or not ai:
            continue
        pest_id = pest_id.strip()
        ai = ai.strip()
        pesticide_id = slug_id(ai)

        if pesticide_id not in ent_index:
            ent = {
                "id": pesticide_id,
                "type": "Pesticide",
                "name": ai,
                "active_ingredient": ai,
                "description": "Auto-extracted pesticide recommendation.",
                "source_refs": [rec.get("source_id")] if rec.get("source_id") else [],
            }
            entities.append(ent)
            ent_index[pesticide_id] = ent

        key = ("CONTROLLED_BY", pest_id, pesticide_id, rec.get("dosage"))
        if key in rel_keys:
            continue

        relations.append({
            "id": f"rel.{pest_id}.controlled_by.{pesticide_id}",
            "type": "CONTROLLED_BY",
            "from": pest_id,
            "to": pesticide_id,
            "dosage": rec.get("dosage"),
            "method": rec.get("method"),
            "timing": rec.get("timing"),
            "formulation": rec.get("formulation"),
            "region": rec.get("region"),
            "notes": "auto: pesticide recommendation extraction",
            "source_refs": [rec.get("source_id")] if rec.get("source_id") else [],
        })
        rel_keys.add(key)
        added_rel += 1

    write_jsonl(proc_ent_path, entities)
    write_jsonl(rel_path, relations)
    print("Merged pesticide recommendations. Added relations:", added_rel)


if __name__ == "__main__":
    main()
