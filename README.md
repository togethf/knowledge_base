# Knowledge Base (Pest-Centric)

This folder is a clean, extensible knowledge base (KB) scaffold for a future pest-diagnosis system.
It is designed to support:
- Pest / disease control as the core scope.
- Auxiliary facts (crop, growth stage, pesticide, weather) for monitoring and early warning.
- A future knowledge graph (KG) backend.

## Quick start
1) Add or edit seed items in `data/seed/`.
2) Validate: `python tools/validate_kb.py`
3) Export for KG ingestion: `python tools/build_kg_csv.py`
4) Crawl Wikipedia summaries: `python tools/crawl_wikipedia.py`
5) Build processed entities from Wikipedia: `python tools/process_wikipedia.py`
6) Build initial relations from text: `python tools/build_relations_from_text.py`
7) Extract pest fact tables from PDFs: `python tools/extract_pest_facts.py`
8) Download full Wikipedia pages: `python tools/download_wikipedia_pages.py`
9) Extract relations from Wikipedia pages: `python tools/extract_relations_from_wikipedia_pages.py`
10) Merge PPP fact sheet relations: `python tools/merge_ppp_relations.py`
11) Extract pesticide dosage recommendations: `python tools/extract_pesticide_recommendations.py`
12) Merge pesticide recommendations: `python tools/merge_pesticide_recommendations.py`

## Folder layout
- `schema/`: Entity and relation type definitions.
- `data/seed/`: Small, hand-authored examples.
- `data/raw/`: Raw records from future crawlers or manual sources.
- `data/processed/`: Cleaned, normalized records.
- `data/sources/`: Source metadata (URL, license, source name).
- `tools/`: Validation and export utilities.
- `configs/`: Paths and global settings.

## Minimal data rules
- Every entity and relation must have a stable `id`.
- Keep `name` human-readable; use `aliases` for synonyms.
- Relations should be directional and typed.
- Keep data ASCII unless you intentionally add multilingual content.

## Future extensions
- Add a crawler that writes into `data/raw/`.
- Add a normalizer that moves records into `data/processed/`.
- Add a vector index build step for RAG if desired later.
