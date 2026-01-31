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
        return "\n".join(self._chunks)


def html_to_text(html):
    parser = TextExtractor()
    parser.feed(html)
    return parser.text()


def read_file(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def write_jsonl(path, items):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=True) + "\n")


def extract_dosage_lines(text):
    # Normalize spacing and split into sentence-like chunks
    text = text.replace("\r", "\n").replace("\x0c", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    chunks = re.split(r"[。；;!！？\n]|(?<!\d)\.(?!\d)", text)
    dosage_lines = []
    for chunk in chunks:
        line = chunk.strip()
        if not line:
            continue
        if "亩" in line and ("克" in line or "毫升" in line or "毫克" in line or "公斤" in line or "千克" in line or "ml" in line or "ML" in line):
            dosage_lines.append(line)
            continue
        if "倍液" in line:
            dosage_lines.append(line)
            continue
        if "ha" in line or "ha-1" in line or "ha-1" in line:
            if any(u in line for u in ["kg", "Kg", "g", "ml", "ML", "L", "l", "a.i."]):
                dosage_lines.append(line)
    return dosage_lines


def parse_pesticide_items(line):
    items = []
    enable_pct = True
    dose_pattern = r"\d+(?:\.\d+)?"
    dose_range_pattern = r"\d+(?:\.\d+)?(?:[-～—~]\d+(?:\.\d+)?)?"
    unit_pattern = r"(克|毫升|毫克|公斤|千克|ml|ML|L|l)"
    bad_ai_terms = [
        "干细土", "中耕", "撒施", "混匀", "灌根", "喷雾", "每株", "倍液", "土中", "幼虫", "成虫",
        "虫害较轻", "地块", "温水溶解成", "药液", "腐熟有机肥", "三料磷肥", "硫酸钾复合肥", "二铵", "肥料",
        "混细沙", "细沙", "撒施", "锄入"
    ]

    def clean_ai(ai):
        ai = ai.replace("有效成份", "")
        ai = ai.replace("效成份", "")
        ai = ai.replace("防治", "")
        ai = ai.replace("时亩用", "")
        ai = ai.replace("亩用", "")
        ai = ai.replace("每亩", "")
        ai = ai.replace("或于", "")
        ai = ai.replace("或", "")
        ai = ai.replace("于", "")
        ai = ai.replace("+", "").replace("＋", "")
        ai = re.sub(r"\b(foliar application of|application of|broadcasting of)\b", "", ai, flags=re.IGNORECASE)
        ai = re.sub(r"\b(and|the|of)\b", "", ai, flags=re.IGNORECASE)
        if "（" in ai or "(" in ai:
            left = ai
            for mark in ["（", "("]:
                if mark in ai:
                    left = ai.split(mark, 1)[-1]
                    right_mark = "）" if mark == "（" else ")"
                    if right_mark in left:
                        left = left.split(right_mark, 1)[0]
                    break
            if left and len(left) >= 2:
                ai = left
        ai = re.sub(r"\b[a-zA-Z]\b", "", ai)
        ai = re.sub(r"\s+[a-zA-Z]\s+", " ", ai)
        if "释放" in ai:
            ai = ai.split("释放")[-1]
        if "：" in ai:
            ai = ai.split("：")[-1]
        if ":" in ai:
            ai = ai.split(":")[-1]
        if ai.startswith("%"):
            ai = ai.lstrip("%")
        if ai.startswith("克/升"):
            ai = ai.replace("克/升", "", 1)
        for suffix in ["可湿性粉剂", "粉剂", "悬浮剂", "乳油", "乳剂", "水分散粒剂", "颗粒剂", "可溶液剂", "水剂", "晶体"]:
            ai = ai.replace(suffix, "")
        ai = re.sub(r"\s+", " ", ai)
        ai = ai.lstrip("的")
        ai = ai.strip("、，,;； .（）()")
        return ai
    if enable_pct:
        pattern_pct = re.compile(
            rf"(?P<formulation>\d+(?:\.\d+)?%)\s*(?P<ai>[^\d]{{2,20}}?)(?P<dose>{dose_range_pattern})(?P<unit>{unit_pattern})(?:\s*/?亩)?"
        )
        for m in pattern_pct.finditer(line):
            ai = clean_ai(m.group("ai"))
            if any(bad in ai for bad in bad_ai_terms):
                continue
            if "千克" in ai or "公斤" in ai or ai.endswith("-"):
                continue
            if any(bad in line for bad in ["对干细土", "细土", "中耕", "锄入"]):
                continue
            if "株率" in line:
                left = line.split(m.group("formulation"), 1)[0]
                if "株率" in left:
                    continue
            if any(bad in ai for bad in ["株率", "枯鞘", "时亩用", "亩用"]):
                continue
            items.append({
                "active_ingredient": ai,
                "formulation": m.group("formulation"),
                "dosage": f"{m.group('dose')}{m.group('unit')}/亩",
            })

    # Pattern without percent, e.g. "有效成份氯虫苯甲酰胺2克/亩"
    existing_ai = {item["active_ingredient"] for item in items}
    pattern_plain = re.compile(
        rf"(?:有效成份)?(?P<ai>[^\d]{{2,30}}?)(?P<dose>{dose_range_pattern})(?P<unit>{unit_pattern})(?:\s*/?亩)?"
    )
    for m in pattern_plain.finditer(line):
        ai = clean_ai(m.group("ai"))
        if any(bad in ai for bad in bad_ai_terms):
            continue
        if "千克" in ai or "公斤" in ai or ai.endswith("-"):
            continue
        if "IU/微升" in ai or "IU/毫克" in ai:
            continue
        if "%" in ai or "克/升" in ai:
            continue
        if "Bt可湿性粉剂" in ai or "毫克Bt" in ai:
            ai = "Bt"
        if not ai:
            continue
        if ai in existing_ai:
            continue
        items.append({
            "active_ingredient": ai,
            "formulation": "",
            "dosage": f"{m.group('dose')}{m.group('unit')}/亩",
        })

    # BT formulation pattern, e.g. "16000IU/毫克Bt可湿性粉剂100克/亩"
    pattern_bt = re.compile(r"(?P<formulation>\d+IU/毫克)\s*(?P<ai>Bt)可湿性粉剂\s*(?P<dose>\d+)(?P<unit>克|公斤|千克)(?:\s*/?亩)?")
    for m in pattern_bt.finditer(line):
        items.append({
            "active_ingredient": m.group("ai"),
            "formulation": f"{m.group('formulation')}可湿性粉剂",
            "dosage": f"{m.group('dose')}{m.group('unit')}/亩",
        })

    # Concentration like "150克/升茚虫威15毫升/亩"
    pattern_gpl = re.compile(
        rf"(?P<formulation>\d+\s*克/升)\s*(?P<ai>[^\d]{{2,20}}?)(?P<dose>{dose_range_pattern})(?P<unit>毫升|克|ml|ML)(?:\s*/?亩)?"
    )
    for m in pattern_gpl.finditer(line):
        formulation = m.group("formulation").replace(" ", "")
        ai = clean_ai(m.group("ai"))
        if any(bad in ai for bad in bad_ai_terms):
            continue
        if "千克" in ai or "公斤" in ai or ai.endswith("-"):
            continue
        items.append({
            "active_ingredient": ai,
            "formulation": formulation,
            "dosage": f"{m.group('dose')}{m.group('unit')}/亩",
        })

    # IU per microliter formulation, e.g. "8000IU/微升苏云金杆菌悬浮剂150-200毫升/亩"
    pattern_iu = re.compile(
        rf"(?P<formulation>\d+IU/微升)\s*(?P<ai>[^\d]{{2,20}}?)(?P<dose>{dose_range_pattern})(?P<unit>毫升|克|ml|ML)(?:\s*/?亩)?"
    )
    for m in pattern_iu.finditer(line):
        ai = clean_ai(m.group("ai"))
        if any(bad in ai for bad in bad_ai_terms):
            continue
        items.append({
            "active_ingredient": ai,
            "formulation": m.group("formulation"),
            "dosage": f"{m.group('dose')}{m.group('unit')}/亩",
        })

    # Dilution pattern, e.g. "25%灭幼脲Ⅲ悬浮剂1000～1500倍液"
    pattern_dilution = re.compile(
        rf"(?P<formulation>\d+(?:\.\d+)?%)?\s*(?P<ai>[^\d]{{2,30}}?)(?P<dose>{dose_range_pattern})\s*倍液"
    )
    for m in pattern_dilution.finditer(line):
        ai = clean_ai(m.group("ai"))
        if any(bad in ai for bad in bad_ai_terms):
            continue
        formulation = (m.group("formulation") or "").strip()
        if not ai:
            continue
        items.append({
            "active_ingredient": ai,
            "formulation": formulation,
            "dosage": f"{m.group('dose')}倍液",
        })

    # English dosage pattern, e.g. "carbofuran 3G @ 1.0 Kg a.i. ha-1"
    pattern_ai_ha = re.compile(
        rf"(?P<ai>[A-Za-z][A-Za-z\-]+)(?:\s+(?:spray|granules|granular))?\s*(?P<formulation>\d+G|\d+\s*G|\d+\s*SC|\d+\s*EC|\d+\s*SL)?\s*@\s*(?P<dose>{dose_range_pattern})\s*(?P<unit>Kg|kg|g|ml|ML|L|l)\s*a\.i\.\s*ha-1",
        re.IGNORECASE,
    )
    for m in pattern_ai_ha.finditer(line):
        ai = clean_ai(m.group("ai"))
        formulation = (m.group("formulation") or "").replace(" ", "")
        if not ai:
            continue
        if re.fullmatch(r"[A-Za-z\\-]+", ai):
            ai = ai.lower()
        unit = m.group("unit")
        start = max(0, m.start() - 80)
        end = min(len(line), m.end() + 80)
        items.append({
            "active_ingredient": ai,
            "formulation": formulation,
            "dosage": f"{m.group('dose')}{unit} a.i./ha",
            "evidence": line[start:end],
        })

    # De-duplicate
    deduped = {}
    for item in items:
        key = (item["active_ingredient"], item["formulation"], item["dosage"])
        deduped[key] = item
    return list(deduped.values())


def extract_timing(text):
    # Extract timing windows like "5月23-25日"
    m = re.search(r"(\d{1,2}月\d{1,2})(?:-|—|~)(\d{1,2})日", text)
    if m:
        return f"{m.group(1)}-{m.group(2)}日"
    return ""


def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    raw_dir = os.path.join(base_dir, "data", "raw", "sources", "zh_gov")
    out_path = os.path.join(base_dir, "data", "processed", "pesticide_recommendations.jsonl")

    sources = [
        {
            "file": "luan_stem_borer_2021.html",
            "source_id": "source.luan_chilo_suppressalis_2021",
            "region": "安徽省六安市",
            "pest_map": {
                "二化螟": "pest.chilo_suppressalis",
            },
        },
        {
            "file": "huzhou_pest_bulletin_2024_08.html",
            "source_id": "source.huzhou_pest_bulletin_2024_08",
            "region": "浙江省湖州市",
            "pest_map": {
                "稻纵卷叶螟": "pest.cnaphalocrocis_medinalis",
                "二化螟": "pest.chilo_suppressalis",
                "褐飞虱": "pest.nilaparvata_lugens",
            },
        },
        {
            "file": "dachuan_planthopper_2023.html",
            "source_id": "source.dachuan_whitebacked_planthopper_2023",
            "region": "四川省达州市达川区",
            "pest_map": {
                "白背飞虱": "pest.sogatella_furcifera",
                "稻飞虱": "pest.planthopper",
            },
        },
        {
            "file": "shaanxi_wubu_soil_pests_2025.html",
            "source_id": "source.shaanxi_wubu_soil_pests_2025",
            "region": "陕西省榆林市吴堡县",
            "pest_map": {
                "蝼蛄": "pest.gryllotalpa_spp",
                "金龟子": "pest.anomala_corpulenta",
            },
        },
        {
            "file": "shaanxi_zhidan_soil_pests_2025.html",
            "source_id": "source.shaanxi_zhidan_soil_pests_2025",
            "region": "陕西省延安市志丹县",
            "pest_map": {
                "蝼蛄": "pest.gryllotalpa_spp",
                "金龟子": "pest.anomala_corpulenta",
            },
        },
        {
            "file": "hongsibu_grub_beetle_2024.html",
            "source_id": "source.hongsibu_grub_beetle_2024",
            "region": "宁夏回族自治区吴忠市红寺堡区",
            "pest_map": {
                "金龟子": "pest.anomala_corpulenta",
            },
        },
        {
            "file": "mianxian_corn_borer_2025.html",
            "source_id": "source.mianxian_corn_borer_2025",
            "region": "陕西省汉中市勉县",
            "pest_map": {
                "玉米螟": "pest.ostrinia_nubilalis",
            },
        },
        {
            "file": "cnhnb_sweet_corn_borer_2021.html",
            "source_id": "source.cnhnb_sweet_corn_borer_2021",
            "region": "全国（甜玉米）",
            "pest_map": {
                "大螟": "pest.sesamia_inferens",
            },
            "pest_keywords": {
                "大螟": ["大螟", "台湾螟", "米乐尔", "巴丹"],
            },
        },
        {
            "file": "sina_poplar_defoliators_2005.html",
            "source_id": "source.sina_poplar_defoliators_2005",
            "region": "中国（杨树食叶害虫）",
            "pest_map": {
                "杨雪毒蛾": "pest.stilpnotia_salicis",
            },
        },
        {
            "file": "csrl_rice_gall_midge_2018.txt",
            "source_id": "source.csrl_rice_gall_midge_2018",
            "region": "印度（田间试验）",
            "pest_map": {
                "gall midge": "pest.dao_ming_ling",
            },
            "folder": "papers",
            "use_full_text": True,
        },
    ]

    rows = []
    for src in sources:
        folder = src.get("folder", "zh_gov")
        path = os.path.join(base_dir, "data", "raw", "sources", folder, src["file"])
        if not os.path.exists(path):
            continue
        html = read_file(path)
        if path.endswith(".txt"):
            text = html
        else:
            text = html_to_text(html)
        timing = extract_timing(text)
        if src.get("use_full_text"):
            dosage_lines = [text]
        else:
            dosage_lines = extract_dosage_lines(text)

        for pest_name, pest_id in src["pest_map"].items():
            keywords = src.get("pest_keywords", {}).get(pest_name)
            if keywords:
                pest_lines = [l for l in dosage_lines if any(kw in l for kw in keywords)]
                if not pest_lines:
                    continue
            else:
                pest_lines = [l for l in dosage_lines if pest_name in l] or dosage_lines
            for line in pest_lines:
                items = parse_pesticide_items(line)
                for item in items:
                    method = "spray"
                    if any(k in line for k in ["拌种", "seed", "seed dressing"]):
                        method = "seed_treatment"
                    elif "G" in item.get("formulation", "") or "颗粒" in line or "granule" in line or "granular" in line:
                        method = "granular"
                    evidence = item.get("evidence", line)
                    rows.append({
                        "pest_id": pest_id,
                        "pest_name": pest_name,
                        "active_ingredient": item["active_ingredient"],
                        "formulation": item["formulation"],
                        "dosage": item["dosage"],
                        "method": method,
                        "timing": timing or evidence,
                        "region": src["region"],
                        "source_id": src["source_id"],
                        "evidence": evidence,
                    })

    write_jsonl(out_path, rows)
    print("Wrote:", out_path, "records:", len(rows))


if __name__ == "__main__":
    main()
