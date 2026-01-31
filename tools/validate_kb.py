#!/usr/bin/env python3
import json
import os
import sys


def load_config(path):
    try:
        import yaml  # type: ignore
    except Exception:
        yaml = None

    if yaml:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    # Minimal fallback parser for this repo's simple YAML
    config = {"paths": {}, "validation": {}}
    current = None
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.endswith(":") and not line.startswith("-"):
                current = line[:-1]
                if current not in config:
                    config[current] = {}
                continue
            if ":" in line and current:
                key, value = [part.strip() for part in line.split(":", 1)]
                value = value.strip("\"'")
                config[current][key] = value
    return config


def read_jsonl(path):
    items = []
    if not os.path.exists(path):
        return items
    with open(path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError:
                raise ValueError(f"Invalid JSON on line {idx} of {path}")
    return items


def pick_dataset(seed_path, processed_path):
    if os.path.exists(processed_path) and os.path.getsize(processed_path) > 0:
        return read_jsonl(processed_path)
    return read_jsonl(seed_path)


def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, "configs", "kb_config.yaml")
    config = load_config(config_path)

    paths = config.get("paths", {})
    schema_entities_path = os.path.join(base_dir, paths.get("schema_entities", "schema/entities.json"))
    schema_relations_path = os.path.join(base_dir, paths.get("schema_relations", "schema/relations.json"))
    seed_entities_path = os.path.join(base_dir, paths.get("seed_entities", "data/seed/seed_entities.jsonl"))
    seed_relations_path = os.path.join(base_dir, paths.get("seed_relations", "data/seed/seed_relations.jsonl"))
    processed_entities_path = os.path.join(base_dir, paths.get("processed_entities", "data/processed/entities.jsonl"))
    processed_relations_path = os.path.join(base_dir, paths.get("processed_relations", "data/processed/relations.jsonl"))

    with open(schema_entities_path, "r", encoding="utf-8") as f:
        entity_schema = json.load(f)
    with open(schema_relations_path, "r", encoding="utf-8") as f:
        relation_schema = json.load(f)

    entity_types = {e["type"]: e for e in entity_schema.get("entity_types", [])}
    relation_types = {r["type"]: r for r in relation_schema.get("relation_types", [])}

    entities = pick_dataset(seed_entities_path, processed_entities_path)
    relations = pick_dataset(seed_relations_path, processed_relations_path)

    errors = []
    entity_ids = set()

    for i, ent in enumerate(entities):
        ent_id = ent.get("id")
        ent_type = ent.get("type")
        ent_name = ent.get("name")
        if not ent_id or not ent_name:
            errors.append(f"Entity missing id or name at index {i}")
        if ent_type not in entity_types:
            errors.append(f"Unknown entity type '{ent_type}' for id '{ent_id}'")
        else:
            required = set(entity_types[ent_type].get("required_fields", []))
            missing = [field for field in required if field not in ent]
            if missing:
                errors.append(f"Entity '{ent_id}' missing required fields: {', '.join(missing)}")
        if ent_id:
            if ent_id in entity_ids:
                errors.append(f"Duplicate entity id '{ent_id}'")
            entity_ids.add(ent_id)

    for i, rel in enumerate(relations):
        rel_id = rel.get("id")
        rel_type = rel.get("type")
        rel_from = rel.get("from")
        rel_to = rel.get("to")
        if not rel_id or not rel_type or not rel_from or not rel_to:
            errors.append(f"Relation missing id/type/from/to at index {i}")
            continue
        if rel_type not in relation_types:
            errors.append(f"Unknown relation type '{rel_type}' for id '{rel_id}'")
        if rel_from not in entity_ids:
            errors.append(f"Relation '{rel_id}' references unknown from id '{rel_from}'")
        if rel_to not in entity_ids:
            errors.append(f"Relation '{rel_id}' references unknown to id '{rel_to}'")

    if errors:
        print("KB validation failed:")
        for err in errors:
            print("-", err)
        sys.exit(1)

    print("KB validation passed. Entities:", len(entities), "Relations:", len(relations))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
