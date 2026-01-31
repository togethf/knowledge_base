#!/usr/bin/env python3
import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KB_DIR = os.path.join(BASE_DIR, "knowledge_base", "data", "processed")
RELATIONS_PATH = os.path.join(KB_DIR, "relations.jsonl")
ENTITIES_PATH = os.path.join(KB_DIR, "entities.jsonl")

# YOLO label -> pest_id mapping
YOLO_PEST_MAP = {
    "DaoZhong": "pest.cnaphalocrocis_medinalis",
    "ErHua": "pest.chilo_suppressalis",
    "DaMingShen": "pest.sesamia_inferens",
    "HeiBai": "pest.sogatella_furcifera",
    "DaoMingLing": "pest.dao_ming_ling",
    "YuMiMing": "pest.ostrinia_nubilalis",
    "YangXue": "pest.stilpnotia_salicis",
    "LouGu": "pest.gryllotalpa_spp",
    "JinGui": "pest.anomala_corpulenta",
    "brown planthopper": "pest.nilaparvata_lugens",
}

PROMPT_TEMPLATE = """你是农业病虫害诊断助手。请基于用户的害虫识别结果与检索到的知识库证据，给出可执行的防治建议。
要求：
1) 仅使用检索到的知识库证据，不要编造。
2) 输出结构化内容，包含：害虫名称、受害作物、主要症状、发生期/条件、防治方案。
3) 防治方案必须包含：有效成分、剂量、方法、适用时期、来源地区与来源ID。
4) 若剂量单位不一致（如“倍液”“a.i./ha”“/亩”），必须保留原单位并提示“单位差异需当地规范校正”。
5) 若证据地区与用户地区不一致，必须提示“区域差异请以当地农技/标签为准”。
6) 若证据不足，必须明确说明“证据不足，不给出具体用药剂量”，仅给出原则性建议。
7) 加入安全提示：遵循当地登记标签与安全间隔期，避免超量与混配风险。

输入：
- 用户害虫识别结果：{pests}
- 证据关系：\n{evidence}

输出格式：
- 害虫诊断：…
- 证据摘要（列出关键证据点 + source_id）
- 防治方案（表格形式）
- 注意事项（单位差异/区域差异/安全提示）
"""


def load_jsonl(path):
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def build_entity_map(entities):
    return {e.get("id"): e.get("name", e.get("id")) for e in entities}


def load_relations():
    return load_jsonl(RELATIONS_PATH)


def load_entities():
    return load_jsonl(ENTITIES_PATH)


def parse_yolo_input(raw):
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if isinstance(data, list):
        return data
    return []


def map_pests(yolo_results):
    mapped = []
    for item in yolo_results:
        label = item.get("label")
        if not label:
            continue
        pest_id = YOLO_PEST_MAP.get(label)
        if pest_id:
            mapped.append({"label": label, "pest_id": pest_id, "score": item.get("score")})
    return mapped


def collect_evidence(relations, pest_ids, entity_map):
    keep_types = {
        "AFFECTS",
        "CAUSES",
        "OCCURS_IN_STAGE",
        "CONTROLLED_BY",
        "FAVORED_BY_WEATHER",
    }
    selected = [r for r in relations if r.get("from") in pest_ids and r.get("type") in keep_types]
    lines = []
    for r in selected:
        rel_type = r.get("type")
        src = ",".join(r.get("source_refs", []))
        if rel_type == "CONTROLLED_BY":
            lines.append(
                f"{r.get('from')} -> {entity_map.get(r.get('to'), r.get('to'))} | dosage={r.get('dosage')} | method={r.get('method')} | timing={r.get('timing')} | region={r.get('region')} | sources={src}"
            )
        else:
            lines.append(
                f"{r.get('from')} --{rel_type}--> {entity_map.get(r.get('to'), r.get('to'))} | sources={src}"
            )
    return lines


def build_prompt(pest_list, evidence_lines):
    pests_text = ", ".join([f"{p['label']}({p['pest_id']})" for p in pest_list])
    evidence = "\n".join(evidence_lines) if evidence_lines else "(暂无证据)"
    return PROMPT_TEMPLATE.format(pests=pests_text, evidence=evidence)


def main():
    # If input JSON provided via file or stdin, use it; otherwise use a demo sample.
    raw = ""
    if len(sys.argv) > 1:
        with open(sys.argv[1], "r", encoding="utf-8") as f:
            raw = f.read()
    elif not sys.stdin.isatty():
        raw = sys.stdin.read()

    if not raw.strip():
        raw = json.dumps([
            {"label": "DaoZhong", "score": 0.93},
            {"label": "ErHua", "score": 0.88},
        ], ensure_ascii=True)

    yolo_results = parse_yolo_input(raw)
    pest_list = map_pests(yolo_results)
    if not pest_list:
        print("No mapped pests from YOLO input.")
        return

    entities = load_entities()
    relations = load_relations()
    entity_map = build_entity_map(entities)
    pest_ids = [p["pest_id"] for p in pest_list]
    evidence_lines = collect_evidence(relations, pest_ids, entity_map)
    prompt = build_prompt(pest_list, evidence_lines)

    print(prompt)


if __name__ == "__main__":
    main()
