#!/usr/bin/env python3
import json
import os
import re


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


def normalize(text):
    return re.sub(r"\s+", " ", text or "").strip().lower()


def build_relation_id(from_id, rel_type, to_id):
    safe_type = rel_type.lower()
    return f"rel.{from_id}.{safe_type}.{to_id}"


def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    facts_path = os.path.join(base_dir, "data", "processed", "pest_relation_table.jsonl")
    rel_path = os.path.join(base_dir, "data", "processed", "relations.jsonl")
    seed_rel_path = os.path.join(base_dir, "data", "seed", "seed_relations.jsonl")

    facts = read_jsonl(facts_path)
    relations = read_jsonl(rel_path)
    if not relations:
        relations = read_jsonl(seed_rel_path)

    existing_keys = {(r.get("type"), r.get("from"), r.get("to")) for r in relations}
    rel_index = {(r.get("type"), r.get("from"), r.get("to")): r for r in relations}

    crop_rules = {
        "crop.rice": ["rice", "paddy", "oryza"],
        "crop.maize": ["maize", "corn", "zea mays"],
    }
    symptom_rules = {
        "symptom.hopperburn": ["hopperburn"],
        "symptom.wilting": ["wilt", "wilting"],
        "symptom.yellowing": ["yellow", "yellowing", "chlorosis"],
        "symptom.deadheart": ["deadheart"],
        "symptom.whitehead": ["whitehead"],
        "symptom.leaf_holes": ["leaf hole", "leaf holes", "chewing", "holes on leaves"],
    }
    stage_rules = {
        "stage.seedling": ["seedling"],
        "stage.tillering": ["tillering"],
        "stage.flowering": ["flowering", "anthesis"],
        "stage.milk": ["milk stage", "milk"],
        "stage.dough": ["dough stage", "dough"],
    }
    pesticide_rules = {
        "pesticide.insecticide_generic": ["insecticide", "insecticides", "pesticide", "pesticides"],
    }

    added = 0
    for row in facts:
        pest_id = row.get("pest_id")
        if not pest_id:
            continue
        hosts_text = normalize(row.get("hosts"))
        symptoms_text = normalize(row.get("symptoms_lifecycle"))
        management_text = normalize(row.get("management"))
        rel_notes = "auto: PPP fact sheet extraction"
        source_id = row.get("source_id")
        source_refs = [source_id] if source_id else []

        def add_relation(rel_type, to_id):
            nonlocal added
            key = (rel_type, pest_id, to_id)
            if key in existing_keys:
                rel = rel_index.get(key)
                if rel is not None and source_id:
                    refs = rel.get("source_refs", [])
                    if not isinstance(refs, list):
                        refs = [refs]
                    if source_id not in refs:
                        refs.append(source_id)
                        rel["source_refs"] = refs
                return
            relations.append({
                "id": build_relation_id(pest_id, rel_type, to_id),
                "type": rel_type,
                "from": pest_id,
                "to": to_id,
                "notes": rel_notes,
                "source_refs": source_refs,
            })
            existing_keys.add(key)
            rel_index[key] = relations[-1]
            added += 1

        for crop_id, kws in crop_rules.items():
            if any(kw in hosts_text for kw in kws):
                add_relation("AFFECTS", crop_id)

        for symptom_id, kws in symptom_rules.items():
            if any(kw in symptoms_text for kw in kws):
                add_relation("CAUSES", symptom_id)

        for stage_id, kws in stage_rules.items():
            if any(kw in symptoms_text for kw in kws):
                add_relation("OCCURS_IN_STAGE", stage_id)

        for pesticide_id, kws in pesticide_rules.items():
            if any(kw in management_text for kw in kws):
                add_relation("CONTROLLED_BY", pesticide_id)

    write_jsonl(rel_path, relations)
    print("Merged PPP relations. Added:", added, "Total:", len(relations))


if __name__ == "__main__":
    main()
