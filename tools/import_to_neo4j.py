#!/usr/bin/env python3
"""
Import knowledge base entities and relations into Neo4j.

Usage:
    python import_to_neo4j.py [--uri URI] [--user USER] [--password PASSWORD] [--clear]

Environment variables (alternative to CLI args):
    NEO4J_URI      - Neo4j connection URI (default: bolt://localhost:7687)
    NEO4J_USER     - Neo4j username (default: neo4j)
    NEO4J_PASSWORD - Neo4j password (required)

Examples:
    # Using environment variables
    export NEO4J_PASSWORD=your_password
    python import_to_neo4j.py

    # Using CLI arguments
    python import_to_neo4j.py --uri bolt://localhost:7687 --user neo4j --password your_password

    # Clear existing data before import
    python import_to_neo4j.py --clear
"""

import argparse
import json
import os
import sys
from typing import Any


def check_neo4j_driver():
    """Check if neo4j driver is installed."""
    try:
        from neo4j import GraphDatabase
        return GraphDatabase
    except ImportError:
        print("Error: neo4j driver not installed.")
        print("Please install it with: pip install neo4j")
        sys.exit(1)


def load_config(path: str) -> dict:
    """Load YAML config, fallback to simple parser if PyYAML not available."""
    try:
        import yaml
    except ImportError:
        yaml = None

    if yaml:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    # Simple fallback parser
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


def read_jsonl(path: str) -> list[dict]:
    """Read a JSONL file and return list of records."""
    items = []
    if not os.path.exists(path):
        print(f"Warning: File not found: {path}")
        return items
    with open(path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"Warning: Invalid JSON at line {line_num}: {e}")
    return items


def pick_dataset(seed_path: str, processed_path: str) -> list[dict]:
    """Prefer processed data if available, otherwise use seed data."""
    if os.path.exists(processed_path) and os.path.getsize(processed_path) > 0:
        print(f"Using processed data: {processed_path}")
        return read_jsonl(processed_path)
    print(f"Using seed data: {seed_path}")
    return read_jsonl(seed_path)


def sanitize_label(label: str) -> str:
    """Sanitize label for Neo4j (remove special characters)."""
    return "".join(c if c.isalnum() or c == "_" else "_" for c in label)


def props_to_cypher(props: dict[str, Any]) -> str:
    """Convert a dict of properties to Cypher map syntax."""
    parts = []
    for key, value in props.items():
        safe_key = sanitize_label(key)
        if isinstance(value, str):
            escaped = value.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")
            parts.append(f"{safe_key}: '{escaped}'")
        elif isinstance(value, bool):
            parts.append(f"{safe_key}: {str(value).lower()}")
        elif isinstance(value, (int, float)):
            parts.append(f"{safe_key}: {value}")
        elif isinstance(value, (list, dict)):
            escaped = json.dumps(value, ensure_ascii=False).replace("\\", "\\\\").replace("'", "\\'")
            parts.append(f"{safe_key}: '{escaped}'")
        elif value is not None:
            parts.append(f"{safe_key}: '{value}'")
    return "{" + ", ".join(parts) + "}"


class Neo4jImporter:
    """Import knowledge base data to Neo4j."""

    def __init__(self, uri: str, user: str, password: str):
        GraphDatabase = check_neo4j_driver()
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self._verify_connection()

    def _verify_connection(self):
        """Verify the connection to Neo4j."""
        try:
            with self.driver.session() as session:
                session.run("RETURN 1")
            print("✓ Connected to Neo4j successfully")
        except Exception as e:
            print(f"✗ Failed to connect to Neo4j: {e}")
            sys.exit(1)

    def close(self):
        """Close the Neo4j driver."""
        self.driver.close()

    def clear_database(self):
        """Clear all nodes and relationships in the database."""
        with self.driver.session() as session:
            # Delete all relationships first, then nodes
            session.run("MATCH (n) DETACH DELETE n")
            print("✓ Cleared existing data")

    def create_constraints(self, entity_types: list[str]):
        """Create uniqueness constraints for entity IDs."""
        with self.driver.session() as session:
            for entity_type in entity_types:
                label = sanitize_label(entity_type)
                try:
                    session.run(f"""
                        CREATE CONSTRAINT IF NOT EXISTS
                        FOR (n:{label})
                        REQUIRE n.id IS UNIQUE
                    """)
                except Exception:
                    # Older Neo4j versions use different syntax
                    try:
                        session.run(f"""
                            CREATE CONSTRAINT ON (n:{label})
                            ASSERT n.id IS UNIQUE
                        """)
                    except Exception:
                        pass  # Constraint may already exist
            print(f"✓ Created constraints for {len(entity_types)} entity types")

    def import_entities(self, entities: list[dict]) -> dict[str, int]:
        """Import entities as nodes. Returns count per type."""
        type_counts = {}
        with self.driver.session() as session:
            for entity in entities:
                entity_id = entity.get("id", "")
                entity_type = entity.get("type", "Entity")
                label = sanitize_label(entity_type)

                # Build properties
                props = {
                    "id": entity_id,
                    "name": entity.get("name", ""),
                    "description": entity.get("description", ""),
                }

                # Add optional fields
                for key in ["aliases", "taxonomy", "pathogen", "active_ingredient",
                            "thresholds", "uri", "geo", "image_refs", "source_refs",
                            "license", "notes", "caption", "timestamp"]:
                    if key in entity:
                        value = entity[key]
                        if isinstance(value, (list, dict)):
                            props[key] = json.dumps(value, ensure_ascii=False)
                        else:
                            props[key] = value

                # Use MERGE to avoid duplicates
                cypher = f"""
                    MERGE (n:{label} {{id: $id}})
                    SET n += $props
                """
                session.run(cypher, id=entity_id, props=props)

                type_counts[entity_type] = type_counts.get(entity_type, 0) + 1

        return type_counts

    def import_relations(self, relations: list[dict]) -> dict[str, int]:
        """Import relations as edges. Returns count per type."""
        type_counts = {}
        failed = 0

        with self.driver.session() as session:
            for rel in relations:
                rel_id = rel.get("id", "")
                rel_type = rel.get("type", "RELATED_TO")
                from_id = rel.get("from", "")
                to_id = rel.get("to", "")

                if not from_id or not to_id:
                    failed += 1
                    continue

                # Build properties
                props = {"id": rel_id}
                for key in ["notes", "severity", "method", "dosage", "timing",
                            "formulation", "region", "thresholds", "confidence",
                            "source_refs"]:
                    if key in rel:
                        value = rel[key]
                        if isinstance(value, (list, dict)):
                            props[key] = json.dumps(value, ensure_ascii=False)
                        else:
                            props[key] = value

                # Sanitize relationship type
                safe_rel_type = sanitize_label(rel_type).upper()

                # Use MERGE to create relationship
                cypher = f"""
                    MATCH (a {{id: $from_id}})
                    MATCH (b {{id: $to_id}})
                    MERGE (a)-[r:{safe_rel_type} {{id: $rel_id}}]->(b)
                    SET r += $props
                """
                try:
                    result = session.run(cypher, from_id=from_id, to_id=to_id,
                                          rel_id=rel_id, props=props)
                    summary = result.consume()
                    if summary.counters.relationships_created > 0:
                        type_counts[rel_type] = type_counts.get(rel_type, 0) + 1
                    elif summary.counters.properties_set > 0:
                        # Relationship existed, was updated
                        type_counts[rel_type] = type_counts.get(rel_type, 0) + 1
                    else:
                        # Source or target node not found
                        failed += 1
                except Exception as e:
                    print(f"Warning: Failed to create relation {rel_id}: {e}")
                    failed += 1

        if failed > 0:
            print(f"  Warning: {failed} relations could not be created (missing nodes)")

        return type_counts

    def create_indexes(self):
        """Create indexes for common query patterns."""
        with self.driver.session() as session:
            indexes = [
                "CREATE INDEX IF NOT EXISTS FOR (n:Pest) ON (n.name)",
                "CREATE INDEX IF NOT EXISTS FOR (n:Disease) ON (n.name)",
                "CREATE INDEX IF NOT EXISTS FOR (n:Crop) ON (n.name)",
                "CREATE INDEX IF NOT EXISTS FOR (n:Pesticide) ON (n.name)",
                "CREATE INDEX IF NOT EXISTS FOR (n:Symptom) ON (n.name)",
            ]
            for idx in indexes:
                try:
                    session.run(idx)
                except Exception:
                    pass  # Index may already exist or syntax differs
            print("✓ Created search indexes")

    def get_stats(self) -> dict:
        """Get database statistics."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (n)
                RETURN labels(n)[0] AS label, count(*) AS count
                ORDER BY count DESC
            """)
            nodes = {record["label"]: record["count"] for record in result}

            result = session.run("""
                MATCH ()-[r]->()
                RETURN type(r) AS type, count(*) AS count
                ORDER BY count DESC
            """)
            edges = {record["type"]: record["count"] for record in result}

        return {"nodes": nodes, "edges": edges}


def main():
    parser = argparse.ArgumentParser(
        description="Import knowledge base to Neo4j",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument("--uri", default=os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
                        help="Neo4j connection URI")
    parser.add_argument("--user", default=os.environ.get("NEO4J_USER", "neo4j"),
                        help="Neo4j username")
    parser.add_argument("--password", default=os.environ.get("NEO4J_PASSWORD", "Neo4j!12345"),
                        help="Neo4j password")
    parser.add_argument("--clear", action="store_true",
                        help="Clear existing data before import")
    parser.add_argument("--dry-run", action="store_true",
                        help="Only load data, don't import to Neo4j")

    args = parser.parse_args()

    if not args.password and not args.dry_run:
        print("Error: Neo4j password required.")
        print("Set NEO4J_PASSWORD environment variable or use --password")
        sys.exit(1)

    # Load configuration
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, "configs", "kb_config.yaml")
    config = load_config(config_path)
    paths = config.get("paths", {})

    # Build paths
    seed_entities_path = os.path.join(base_dir, paths.get("seed_entities", "data/seed/seed_entities.jsonl"))
    seed_relations_path = os.path.join(base_dir, paths.get("seed_relations", "data/seed/seed_relations.jsonl"))
    processed_entities_path = os.path.join(base_dir, paths.get("processed_entities", "data/processed/entities.jsonl"))
    processed_relations_path = os.path.join(base_dir, paths.get("processed_relations", "data/processed/relations.jsonl"))

    # Load data
    print("\n📂 Loading data...")
    entities = pick_dataset(seed_entities_path, processed_entities_path)
    relations = pick_dataset(seed_relations_path, processed_relations_path)

    print(f"  Loaded {len(entities)} entities")
    print(f"  Loaded {len(relations)} relations")

    if args.dry_run:
        print("\n🔍 Dry run - showing data summary:")
        entity_types = {}
        for e in entities:
            t = e.get("type", "Unknown")
            entity_types[t] = entity_types.get(t, 0) + 1
        print("  Entity types:", entity_types)

        rel_types = {}
        for r in relations:
            t = r.get("type", "Unknown")
            rel_types[t] = rel_types.get(t, 0) + 1
        print("  Relation types:", rel_types)
        return

    # Import to Neo4j
    print(f"\n🔌 Connecting to Neo4j at {args.uri}...")
    importer = Neo4jImporter(args.uri, args.user, args.password)

    try:
        if args.clear:
            print("\n🗑️  Clearing existing data...")
            importer.clear_database()

        # Get unique entity types
        entity_types = list(set(e.get("type", "Entity") for e in entities))

        print("\n📝 Creating constraints...")
        importer.create_constraints(entity_types)

        print("\n📥 Importing entities...")
        entity_counts = importer.import_entities(entities)
        for etype, count in sorted(entity_counts.items()):
            print(f"  • {etype}: {count}")

        print("\n🔗 Importing relations...")
        rel_counts = importer.import_relations(relations)
        for rtype, count in sorted(rel_counts.items()):
            print(f"  • {rtype}: {count}")

        print("\n📊 Creating indexes...")
        importer.create_indexes()

        print("\n✅ Import complete!")
        stats = importer.get_stats()
        total_nodes = sum(stats["nodes"].values())
        total_edges = sum(stats["edges"].values())
        print(f"   Total nodes: {total_nodes}")
        print(f"   Total edges: {total_edges}")

        print("\n💡 Try these Cypher queries in Neo4j Browser:")
        print("   // View all pests")
        print("   MATCH (p:Pest) RETURN p LIMIT 25")
        print("")
        print("   // Find pesticides for a specific pest")
        print("   MATCH (p:Pest)-[:CONTROLLED_BY]->(m:Pesticide)")
        print("   RETURN p.name, m.name LIMIT 25")
        print("")
        print("   // Explore pest-crop relationships")
        print("   MATCH (p:Pest)-[:AFFECTS]->(c:Crop)")
        print("   RETURN p.name, c.name")

    finally:
        importer.close()


if __name__ == "__main__":
    main()
