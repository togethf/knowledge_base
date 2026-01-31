#!/usr/bin/env python3
import csv
import json
import os
import re
from pdfminer.high_level import extract_text


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


def normalize_text(text):
    return re.sub(r"\s+", " ", text).strip()


def extract_section(text, heading, next_headings):
    # Match heading on its own line (PPP PDFs use heading as a line)
    pattern = re.compile(rf"^\s*{re.escape(heading)}\s*$", re.MULTILINE | re.IGNORECASE)
    match = pattern.search(text)
    if not match:
        return ""
    start = match.end()
    end = len(text)
    for nh in next_headings:
        nh_pattern = re.compile(rf"^\s*{re.escape(nh)}\s*$", re.MULTILINE | re.IGNORECASE)
        nh_match = nh_pattern.search(text, start)
        if nh_match and nh_match.start() < end:
            end = nh_match.start()
    return normalize_text(text[start:end])


def extract_value(text, heading):
    # Gets the line(s) right after a heading until next blank line
    pattern = re.compile(rf"^\s*{re.escape(heading)}\s*$", re.MULTILINE | re.IGNORECASE)
    match = pattern.search(text)
    if not match:
        return ""
    start = match.end()
    tail = text[start:]
    lines = [line.strip() for line in tail.splitlines() if line.strip()]
    return lines[0] if lines else ""


def build_alias_index(seed_entities):
    index = {}
    for ent in seed_entities:
        aliases = ent.get("aliases", []) or []
        names = [ent.get("name", "")] + aliases
        for name in names:
            if not name:
                continue
            index[name.strip().lower()] = ent
    return index


def source_id_from_filename(filename):
    mapping = {
        "ppp_rice_brown_planthopper_064.pdf": "source.ppp_rice_brown_planthopper_064",
        "ppp_rice_whitebacked_planthopper_423.pdf": "source.ppp_rice_whitebacked_planthopper_423",
        "ppp_rice_leaf_folder_414.pdf": "source.ppp_rice_leaf_folder_414",
        "ppp_rice_leaf_roller_415.pdf": "source.ppp_rice_leaf_roller_415",
        "ppp_rice_striped_stem_borer_412.pdf": "source.ppp_rice_striped_stem_borer_412",
    }
    return mapping.get(filename, "")


def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    seed_path = os.path.join(base_dir, "data", "seed", "seed_entities.jsonl")
    raw_dir = os.path.join(base_dir, "data", "raw", "sources")
    out_csv = os.path.join(base_dir, "data", "processed", "pest_relation_table.csv")
    out_jsonl = os.path.join(base_dir, "data", "processed", "pest_relation_table.jsonl")

    seed_entities = read_jsonl(seed_path)
    alias_index = build_alias_index(seed_entities)

    rows = []
    for filename in sorted(os.listdir(raw_dir)):
        if not filename.endswith(".pdf") or not filename.startswith("ppp_"):
            continue
        file_path = os.path.join(raw_dir, filename)
        text = extract_text(file_path)
        common_name = extract_value(text, "Common Name")
        scientific_name = extract_value(text, "Scientific Name")
        common_name_clean = common_name.split(";")[0].strip()
        scientific_name_clean = scientific_name.split(".")[0].strip()
        hosts = extract_section(text, "Hosts", ["Symptoms & Life Cycle", "Management", "Distribution", "Common Name", "Scientific Name"])
        symptoms = extract_section(text, "Symptoms & Life Cycle", ["Management", "Hosts", "Distribution", "Common Name", "Scientific Name"])
        management = extract_section(text, "Management", ["Hosts", "Symptoms & Life Cycle", "Distribution", "Common Name", "Scientific Name"])

        ent = None
        for key in [scientific_name_clean, common_name_clean, scientific_name, common_name]:
            if key and key.lower() in alias_index:
                ent = alias_index[key.lower()]
                break

        rows.append({
            "pest_id": ent.get("id") if ent else "",
            "pest_name": ent.get("name") if ent else common_name_clean or scientific_name_clean or common_name or scientific_name,
            "scientific_name": scientific_name_clean or scientific_name,
            "common_name": common_name_clean or common_name,
            "hosts": hosts,
            "symptoms_lifecycle": symptoms,
            "management": management,
            "source_id": source_id_from_filename(filename),
            "source_file": filename,
            "notes": "auto: extracted from PPP fact sheet"
        })

    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    with open(out_csv, "w", encoding="utf-8", newline="") as f:
        fieldnames = [
            "pest_id",
            "pest_name",
            "scientific_name",
            "common_name",
            "hosts",
            "symptoms_lifecycle",
            "management",
            "source_id",
            "source_file",
            "notes",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    write_jsonl(out_jsonl, rows)
    print("Wrote:", out_csv, "rows:", len(rows))
    print("Wrote:", out_jsonl, "rows:", len(rows))


if __name__ == "__main__":
    main()
