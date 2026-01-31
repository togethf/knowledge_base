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


def text_has_any(text, keywords):
    if not text:
        return False
    for kw in keywords:
        if kw in text:
            return True
    return False


def build_relations(entities):
    # Very light-weight bootstrapping from descriptions.
    # Extend the keyword map as you add more crops/symptoms/weather/stages.
    crop_rules = [
        ("crop.maize", ["maize", "corn", "玉米"]),
        ("crop.rice", ["rice", "水稻", "稻"]),
    ]
    symptom_rules = [
        ("symptom.leaf_holes", ["leaf hole", "leaf holes", "chewing", "虫孔", "孔洞", "咬食"]),
    ]
    weather_rules = [
        ("weather.high_humidity", ["high humidity", "humid", "高湿", "潮湿"]),
    ]
    stage_rules = [
        ("stage.seedling", ["seedling", "幼苗"]),
    ]

    relations = []
    seen = set()

    for ent in entities:
        if ent.get("type") not in {"Pest", "Disease"}:
            continue
        ent_id = ent.get("id")
        text = (ent.get("description") or "").lower()

        def add_relation(rel_type, target_id):
            rel_id = f"rel.{ent_id}.{rel_type.lower()}.{target_id}"
            key = (rel_type, ent_id, target_id)
            if key in seen:
                return
            seen.add(key)
            relations.append({
                "id": rel_id,
                "type": rel_type,
                "from": ent_id,
                "to": target_id,
                "notes": "auto: keyword match from description"
            })

        for crop_id, kws in crop_rules:
            kws_lc = [k.lower() for k in kws]
            if text_has_any(text, kws_lc):
                add_relation("AFFECTS", crop_id)

        for symptom_id, kws in symptom_rules:
            kws_lc = [k.lower() for k in kws]
            if text_has_any(text, kws_lc):
                add_relation("CAUSES", symptom_id)

        for weather_id, kws in weather_rules:
            kws_lc = [k.lower() for k in kws]
            if text_has_any(text, kws_lc):
                add_relation("FAVORED_BY_WEATHER", weather_id)

        for stage_id, kws in stage_rules:
            kws_lc = [k.lower() for k in kws]
            if text_has_any(text, kws_lc):
                add_relation("OCCURS_IN_STAGE", stage_id)

    return relations


def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    processed_entities_path = os.path.join(base_dir, "data", "processed", "entities.jsonl")
    seed_entities_path = os.path.join(base_dir, "data", "seed", "seed_entities.jsonl")
    out_path = os.path.join(base_dir, "data", "processed", "relations.jsonl")

    entities = read_jsonl(processed_entities_path)
    if not entities:
        entities = read_jsonl(seed_entities_path)

    relations = build_relations(entities)
    write_jsonl(out_path, relations)
    print("Wrote:", out_path, "records:", len(relations))


if __name__ == "__main__":
    main()
