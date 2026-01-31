#!/usr/bin/env python3
import json
import os
import re
from html.parser import HTMLParser


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self._chunks = []

    def handle_data(self, data):
        if data:
            self._chunks.append(data)

    def text(self):
        return " ".join(self._chunks)


def html_to_text(html):
    parser = TextExtractor()
    parser.feed(html)
    text = parser.text()
    text = re.sub(r"\s+", " ", text).strip()
    return text


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


def build_relation_id(from_id, rel_type, to_id):
    safe_type = rel_type.lower()
    return f"rel.{from_id}.{safe_type}.{to_id}"


def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    manifest_path = os.path.join(base_dir, "data", "raw", "sources", "wikipedia_manifest.jsonl")
    processed_rel_path = os.path.join(base_dir, "data", "processed", "relations.jsonl")
    seed_rel_path = os.path.join(base_dir, "data", "seed", "seed_relations.jsonl")

    manifest = read_jsonl(manifest_path)
    existing = read_jsonl(processed_rel_path)
    if not existing:
        existing = read_jsonl(seed_rel_path)

    existing_keys = {(r.get("type"), r.get("from"), r.get("to")) for r in existing}
    relations = list(existing)

    crop_rules = {
        "crop.rice": [" rice ", " paddy ", " oryza "],
        "crop.maize": [" maize ", " corn ", " zea mays "],
    }
    symptom_rules = {
        "symptom.hopperburn": [" hopperburn "],
        "symptom.wilting": [" wilt ", " wilting "],
        "symptom.yellowing": [" yellow ", " yellowing ", " chlorosis "],
        "symptom.deadheart": [" deadheart "],
        "symptom.whitehead": [" whitehead "],
        "symptom.leaf_holes": [" leaf hole ", " leaf holes ", " chewing ", " holes on leaves "],
    }
    stage_rules = {
        "stage.seedling": [" seedling "],
        "stage.tillering": [" tillering "],
        "stage.flowering": [" flowering ", " anthesis "],
        "stage.milk": [" milk stage ", " milk "],
        "stage.dough": [" dough stage ", " dough "],
    }
    pesticide_rules = {
        "pesticide.insecticide_generic": [" insecticide ", " insecticides ", " pesticide ", " pesticides "],
    }
    weather_rules = {
        "weather.high_humidity": [" high humidity ", " humid "],
    }

    for item in manifest:
        ent_id = item.get("id")
        lang = item.get("lang")
        rel_source = "source.wikipedia_en" if lang == "en" else "source.wikipedia_zh"
        rel_notes = f"auto: keyword match from wikipedia:{lang}"
        file_rel = item.get("file")
        if not ent_id or not file_rel:
            continue
        file_path = os.path.join(base_dir, file_rel)
        if not os.path.exists(file_path):
            continue

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            html = f.read()
        text = " " + html_to_text(html).lower() + " "

        for crop_id, kws in crop_rules.items():
            if any(kw in text for kw in kws):
                key = ("AFFECTS", ent_id, crop_id)
                if key in existing_keys:
                    continue
                relations.append({
                    "id": build_relation_id(ent_id, "AFFECTS", crop_id),
                    "type": "AFFECTS",
                    "from": ent_id,
                    "to": crop_id,
                    "notes": rel_notes,
                    "source_refs": [rel_source],
                })
                existing_keys.add(key)

        for symptom_id, kws in symptom_rules.items():
            if any(kw in text for kw in kws):
                key = ("CAUSES", ent_id, symptom_id)
                if key in existing_keys:
                    continue
                relations.append({
                    "id": build_relation_id(ent_id, "CAUSES", symptom_id),
                    "type": "CAUSES",
                    "from": ent_id,
                    "to": symptom_id,
                    "notes": rel_notes,
                    "source_refs": [rel_source],
                })
                existing_keys.add(key)

        for stage_id, kws in stage_rules.items():
            if any(kw in text for kw in kws):
                key = ("OCCURS_IN_STAGE", ent_id, stage_id)
                if key in existing_keys:
                    continue
                relations.append({
                    "id": build_relation_id(ent_id, "OCCURS_IN_STAGE", stage_id),
                    "type": "OCCURS_IN_STAGE",
                    "from": ent_id,
                    "to": stage_id,
                    "notes": rel_notes,
                    "source_refs": [rel_source],
                })
                existing_keys.add(key)

        for pest_id, kws in pesticide_rules.items():
            if any(kw in text for kw in kws):
                key = ("CONTROLLED_BY", ent_id, pest_id)
                if key in existing_keys:
                    continue
                relations.append({
                    "id": build_relation_id(ent_id, "CONTROLLED_BY", pest_id),
                    "type": "CONTROLLED_BY",
                    "from": ent_id,
                    "to": pest_id,
                    "notes": rel_notes,
                    "source_refs": [rel_source],
                })
                existing_keys.add(key)

        for weather_id, kws in weather_rules.items():
            if any(kw in text for kw in kws):
                key = ("FAVORED_BY_WEATHER", ent_id, weather_id)
                if key in existing_keys:
                    continue
                relations.append({
                    "id": build_relation_id(ent_id, "FAVORED_BY_WEATHER", weather_id),
                    "type": "FAVORED_BY_WEATHER",
                    "from": ent_id,
                    "to": weather_id,
                    "notes": rel_notes,
                    "source_refs": [rel_source],
                })
                existing_keys.add(key)

    write_jsonl(processed_rel_path, relations)
    print("Wrote:", processed_rel_path, "records:", len(relations))


if __name__ == "__main__":
    main()
