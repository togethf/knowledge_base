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


def fetch_page(title, lang, timeout_sec):
    encoded = urllib.parse.quote(title)
    url = f"https://{lang}.wikipedia.org/wiki/{encoded}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "AgriSystemKB/0.1 (educational; contact=local)",
            "Accept": "text/html",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            return url, resp.read().decode("utf-8", errors="ignore")
    except Exception:
        return url, ""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="Max number of entities to fetch (0 means all).")
    parser.add_argument("--offset", type=int, default=0, help="Start offset in entity list.")
    parser.add_argument("--timeout", type=int, default=10, help="HTTP timeout seconds per request.")
    parser.add_argument("--sleep", type=float, default=0.2, help="Sleep seconds between requests.")
    args = parser.parse_args()

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    seed_path = os.path.join(base_dir, "data", "seed", "seed_entities.jsonl")
    out_dir = os.path.join(base_dir, "data", "raw", "sources", "wikipedia")
    manifest_path = os.path.join(base_dir, "data", "raw", "sources", "wikipedia_manifest.jsonl")

    entities = read_jsonl(seed_path)
    targets = [e for e in entities if e.get("type") in {"Pest", "Disease"}]
    if args.offset and args.offset > 0:
        targets = targets[args.offset :]
    if args.limit and args.limit > 0:
        targets = targets[: args.limit]

    os.makedirs(out_dir, exist_ok=True)
    manifest = []
    if os.path.exists(manifest_path):
        manifest = read_jsonl(manifest_path)
    manifest_index = {(m.get("id"), m.get("lang"), m.get("query")) for m in manifest}
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
            is_cjk = any("\u4e00" <= ch <= "\u9fff" for ch in query)
            langs = ["zh", "en"] if is_cjk else ["en", "zh"]
            for lang in langs:
                slug = urllib.parse.quote(query)
                filename = f"wikipedia_{lang}_{slug}.html"
                out_path = os.path.join(out_dir, filename)
                if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
                    entry = {
                        "id": ent.get("id"),
                        "name": ent.get("name"),
                        "query": query,
                        "lang": lang,
                        "url": f"https://{lang}.wikipedia.org/wiki/{slug}",
                        "file": os.path.relpath(out_path, base_dir),
                        "source": f"wikipedia:{lang}",
                        "fetched_at": fetched_at,
                    }
                    key = (entry.get("id"), entry.get("lang"), entry.get("query"))
                    if key not in manifest_index:
                        manifest.append(entry)
                        manifest_index.add(key)
                    break
                url, html = fetch_page(query, lang, timeout_sec=args.timeout)
                if not html:
                    continue
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(html)
                entry = {
                    "id": ent.get("id"),
                    "name": ent.get("name"),
                    "query": query,
                    "lang": lang,
                    "url": url,
                    "file": os.path.relpath(out_path, base_dir),
                    "source": f"wikipedia:{lang}",
                    "fetched_at": fetched_at,
                }
                key = (entry.get("id"), entry.get("lang"), entry.get("query"))
                if key not in manifest_index:
                    manifest.append(entry)
                    manifest_index.add(key)
                break
            time.sleep(args.sleep)

    write_jsonl(manifest_path, manifest)
    print("Wrote:", manifest_path, "records:", len(manifest))


if __name__ == "__main__":
    main()
