#!/usr/bin/env python3
import csv
import json
import os


def load_config(path):
    try:
        import yaml  # type: ignore
    except Exception:
        yaml = None

    if yaml:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    config = {"paths": {}}
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
        for line in f:
            line = line.strip()
            if not line:
                continue
            items.append(json.loads(line))
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
    seed_entities_path = os.path.join(base_dir, paths.get("seed_entities", "data/seed/seed_entities.jsonl"))
    seed_relations_path = os.path.join(base_dir, paths.get("seed_relations", "data/seed/seed_relations.jsonl"))
    processed_entities_path = os.path.join(base_dir, paths.get("processed_entities", "data/processed/entities.jsonl"))
    processed_relations_path = os.path.join(base_dir, paths.get("processed_relations", "data/processed/relations.jsonl"))
    export_nodes_path = os.path.join(base_dir, paths.get("export_nodes", "data/processed/kg_nodes.csv"))
    export_edges_path = os.path.join(base_dir, paths.get("export_edges", "data/processed/kg_edges.csv"))

    entities = pick_dataset(seed_entities_path, processed_entities_path)
    relations = pick_dataset(seed_relations_path, processed_relations_path)

    os.makedirs(os.path.dirname(export_nodes_path), exist_ok=True)

    with open(export_nodes_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "label", "name", "description", "props"])
        writer.writeheader()
        for ent in entities:
            props = {k: v for k, v in ent.items() if k not in {"id", "type", "name", "description"}}
            writer.writerow({
                "id": ent.get("id", ""),
                "label": ent.get("type", ""),
                "name": ent.get("name", ""),
                "description": ent.get("description", ""),
                "props": json.dumps(props, ensure_ascii=True)
            })

    with open(export_edges_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "source", "target", "type", "props"])
        writer.writeheader()
        for rel in relations:
            props = {k: v for k, v in rel.items() if k not in {"id", "from", "to", "type"}}
            writer.writerow({
                "id": rel.get("id", ""),
                "source": rel.get("from", ""),
                "target": rel.get("to", ""),
                "type": rel.get("type", ""),
                "props": json.dumps(props, ensure_ascii=True)
            })

    print("Wrote:", export_nodes_path)
    print("Wrote:", export_edges_path)


if __name__ == "__main__":
    main()
