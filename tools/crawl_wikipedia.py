#!/usr/bin/env python3
import argparse
import json
import os
import time
import urllib.parse
import urllib.request


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


def fetch_summary(title, lang, timeout_sec):
    encoded = urllib.parse.quote(title)
    url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{encoded}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "AgriSystemKB/0.1 (educational; contact=local)",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None
    if data.get("type") == "https://mediawiki.org/wiki/HyperSwitch/errors/not_found":
        return None
    return {
        "title": data.get("title"),
        "extract": data.get("extract"),
        "url": data.get("content_urls", {}).get("desktop", {}).get("page"),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="Max number of entities to fetch (0 means all).")
    parser.add_argument("--timeout", type=int, default=8, help="HTTP timeout seconds per request.")
    parser.add_argument("--sleep", type=float, default=0.2, help="Sleep seconds between requests.")
    args = parser.parse_args()

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    seed_path = os.path.join(base_dir, "data", "seed", "seed_entities.jsonl")
    out_path = os.path.join(base_dir, "data", "raw", "wikipedia_raw.jsonl")

    entities = read_jsonl(seed_path)
    targets = [e for e in entities if e.get("type") in {"Pest", "Disease"}]
    if args.limit and args.limit > 0:
        targets = targets[: args.limit]

    results = []
    fetched_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    for ent in targets:
        name = ent.get("name", "")
        aliases = ent.get("aliases", []) or []
        queries = [name] + aliases
        used = set()
        for query in queries:
            if not query or query in used:
                continue
            used.add(query)
            # Try Chinese first if the name contains CJK characters
            is_cjk = any("\u4e00" <= ch <= "\u9fff" for ch in query)
            langs = ["zh", "en"] if is_cjk else ["en", "zh"]
            for lang in langs:
                summary = fetch_summary(query, lang, args.timeout)
                if not summary:
                    continue
                results.append({
                    "id": ent.get("id"),
                    "name": ent.get("name"),
                    "query": query,
                    "lang": lang,
                    "title": summary.get("title"),
                    "extract": summary.get("extract"),
                    "url": summary.get("url"),
                    "source": f"wikipedia:{lang}",
                    "fetched_at": fetched_at,
                })
                break
            time.sleep(args.sleep)

    write_jsonl(out_path, results)
    print("Wrote:", out_path, "records:", len(results))


if __name__ == "__main__":
    main()
