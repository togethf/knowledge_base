#!/usr/bin/env python3
"""
Visualize the knowledge graph as an interactive HTML network diagram.

Usage:
    python visualize_kg.py [--output FILE]

Output:
    Creates an interactive HTML file that can be opened in a browser.
"""

import argparse
import json
import os
import sys


def check_dependencies():
    """Check if required packages are installed."""
    missing = []
    try:
        from pyvis.network import Network
    except ImportError:
        missing.append("pyvis")
    try:
        import networkx as nx
    except ImportError:
        missing.append("networkx")
    
    if missing:
        print(f"Error: Missing packages: {', '.join(missing)}")
        print(f"Install with: pip install {' '.join(missing)}")
        sys.exit(1)


def load_config(path: str) -> dict:
    """Load YAML config."""
    try:
        import yaml
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except ImportError:
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
    """Read a JSONL file."""
    items = []
    if not os.path.exists(path):
        return items
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


def pick_dataset(seed_path: str, processed_path: str) -> list[dict]:
    """Prefer processed data if available."""
    if os.path.exists(processed_path) and os.path.getsize(processed_path) > 0:
        return read_jsonl(processed_path)
    return read_jsonl(seed_path)


# Color scheme for different entity types
ENTITY_COLORS = {
    "Pest": "#e74c3c",           # Red
    "Disease": "#9b59b6",        # Purple
    "Crop": "#27ae60",           # Green
    "GrowthStage": "#f39c12",    # Orange
    "Pesticide": "#3498db",      # Blue
    "WeatherEvent": "#1abc9c",   # Teal
    "Symptom": "#e67e22",        # Dark Orange
    "Location": "#95a5a6",       # Gray
    "Image": "#34495e",          # Dark Gray
    "Source": "#7f8c8d",         # Light Gray
    "Observation": "#2c3e50",    # Navy
}

# Edge colors for different relation types
RELATION_COLORS = {
    "AFFECTS": "#e74c3c",
    "CAUSES": "#e67e22",
    "OCCURS_IN_STAGE": "#f39c12",
    "CONTROLLED_BY": "#3498db",
    "FAVORED_BY_WEATHER": "#1abc9c",
    "OBSERVED_AT": "#95a5a6",
    "OBSERVES": "#9b59b6",
    "HAS_IMAGE": "#34495e",
    "CITED_FROM": "#7f8c8d",
}


def create_visualization(entities: list[dict], relations: list[dict], output_path: str):
    """Create an interactive network visualization."""
    from pyvis.network import Network
    import networkx as nx

    # Create NetworkX graph first for layout
    G = nx.DiGraph()

    # Add nodes
    entity_map = {}
    for entity in entities:
        node_id = entity.get("id", "")
        node_type = entity.get("type", "Entity")
        node_name = entity.get("name", node_id)
        node_desc = entity.get("description", "")
        
        entity_map[node_id] = {
            "type": node_type,
            "name": node_name,
            "description": node_desc
        }
        G.add_node(node_id, label=node_name, type=node_type)

    # Add edges
    for rel in relations:
        from_id = rel.get("from", "")
        to_id = rel.get("to", "")
        rel_type = rel.get("type", "RELATED_TO")
        
        if from_id in entity_map and to_id in entity_map:
            G.add_edge(from_id, to_id, type=rel_type)

    # Create PyVis network
    net = Network(
        height="800px",
        width="100%",
        bgcolor="#ffffff",
        font_color="#333333",
        directed=True,
        select_menu=True,
        filter_menu=True,
    )

    # Configure physics
    net.set_options("""
    {
        "nodes": {
            "font": {
                "size": 14,
                "face": "Arial"
            },
            "borderWidth": 2,
            "borderWidthSelected": 4,
            "shadow": true
        },
        "edges": {
            "arrows": {
                "to": {
                    "enabled": true,
                    "scaleFactor": 0.5
                }
            },
            "smooth": {
                "type": "curvedCW",
                "roundness": 0.2
            },
            "shadow": true,
            "font": {
                "size": 10,
                "align": "middle"
            }
        },
        "physics": {
            "enabled": true,
            "solver": "forceAtlas2Based",
            "forceAtlas2Based": {
                "gravitationalConstant": -100,
                "centralGravity": 0.01,
                "springLength": 150,
                "springConstant": 0.08,
                "damping": 0.4
            },
            "stabilization": {
                "enabled": true,
                "iterations": 200
            }
        },
        "interaction": {
            "hover": true,
            "tooltipDelay": 100,
            "navigationButtons": true,
            "keyboard": true
        }
    }
    """)

    # Add nodes to PyVis
    for node_id in G.nodes():
        entity = entity_map.get(node_id, {})
        node_type = entity.get("type", "Entity")
        node_name = entity.get("name", node_id)
        node_desc = entity.get("description", "")
        
        color = ENTITY_COLORS.get(node_type, "#bdc3c7")
        
        # Size based on degree (connections)
        degree = G.degree(node_id)
        size = 15 + min(degree * 3, 30)
        
        # Tooltip
        title = f"<b>{node_name}</b><br>Type: {node_type}<br>ID: {node_id}"
        if node_desc:
            title += f"<br><br>{node_desc[:200]}..."
        
        net.add_node(
            node_id,
            label=node_name,
            title=title,
            color=color,
            size=size,
            group=node_type
        )

    # Add edges to PyVis
    for from_id, to_id, data in G.edges(data=True):
        rel_type = data.get("type", "RELATED_TO")
        color = RELATION_COLORS.get(rel_type, "#bdc3c7")
        
        net.add_edge(
            from_id,
            to_id,
            title=rel_type,
            label=rel_type,
            color=color,
            width=2
        )

    # Generate HTML with custom title and legend
    net.save_graph(output_path)
    
    # Add custom legend to the HTML
    with open(output_path, "r", encoding="utf-8") as f:
        html = f.read()
    
    legend_html = """
    <style>
        .legend {
            position: fixed;
            top: 10px;
            right: 10px;
            background: rgba(255, 255, 255, 0.95);
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 15px;
            z-index: 1000;
            font-family: Arial, sans-serif;
            color: #333;
            max-height: 400px;
            overflow-y: auto;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .legend h3 {
            margin: 0 0 10px 0;
            font-size: 14px;
            border-bottom: 1px solid #ddd;
            padding-bottom: 5px;
            color: #333;
        }
        .legend-item {
            display: flex;
            align-items: center;
            margin: 5px 0;
            font-size: 12px;
        }
        .legend-color {
            width: 16px;
            height: 16px;
            border-radius: 50%;
            margin-right: 8px;
            border: 1px solid #ccc;
        }
        .stats {
            position: fixed;
            top: 10px;
            left: 10px;
            background: rgba(255, 255, 255, 0.95);
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 15px;
            z-index: 1000;
            font-family: Arial, sans-serif;
            color: #333;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .stats h3 {
            margin: 0 0 10px 0;
            font-size: 14px;
            color: #333;
        }
        .stats p {
            margin: 5px 0;
            font-size: 12px;
        }
        /* Collapsible filter panel */
        .filter-toggle {
            position: fixed;
            top: 60px;
            left: 50%;
            transform: translateX(-50%);
            background: #3498db;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 20px;
            cursor: pointer;
            z-index: 1001;
            font-size: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
        }
        .filter-toggle:hover {
            background: #2980b9;
        }
        .filter-collapsed .card {
            display: none !important;
        }
    </style>
    <div class="stats">
        <h3>📊 Knowledge Graph Stats</h3>
        <p>🔵 Nodes: """ + str(len(entities)) + """</p>
        <p>🔗 Edges: """ + str(len([r for r in relations if r.get("from") in entity_map and r.get("to") in entity_map])) + """</p>
    </div>
    <div class="legend">
        <h3>🏷️ Entity Types</h3>
    """
    
    for entity_type, color in ENTITY_COLORS.items():
        count = sum(1 for e in entities if e.get("type") == entity_type)
        if count > 0:
            legend_html += f'<div class="legend-item"><div class="legend-color" style="background:{color}"></div>{entity_type} ({count})</div>\n'
    
    legend_html += """
        <h3 style="margin-top:15px;">↔️ Relation Types</h3>
    """
    
    rel_counts = {}
    for r in relations:
        t = r.get("type", "")
        if r.get("from") in entity_map and r.get("to") in entity_map:
            rel_counts[t] = rel_counts.get(t, 0) + 1
    
    for rel_type, color in RELATION_COLORS.items():
        if rel_type in rel_counts:
            legend_html += f'<div class="legend-item"><div class="legend-color" style="background:{color}; border-radius:2px;"></div>{rel_type} ({rel_counts[rel_type]})</div>\n'
    
    legend_html += "</div>"
    
    # Add collapsible filter toggle button and script
    toggle_html = """
    <button class="filter-toggle" onclick="toggleFilter()">📋 显示/隐藏筛选面板</button>
    <script>
        function toggleFilter() {
            var headers = document.querySelectorAll('.card-header');
            headers.forEach(function(header) {
                if (header.style.display === 'none') {
                    header.style.display = 'block';
                } else {
                    header.style.display = 'none';
                }
            });
        }
        // Initially hide the filter panel
        window.onload = function() {
            setTimeout(function() {
                var headers = document.querySelectorAll('.card-header');
                headers.forEach(function(header) {
                    header.style.display = 'none';
                });
            }, 500);
        };
    </script>
    """
    
    # Insert legend and toggle before closing body tag
    html = html.replace("</body>", legend_html + toggle_html + "</body>")
    
    # Update title
    html = html.replace("<title>", "<title>🌾 Agricultural Pest Knowledge Graph - ")
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    
    return len(entities), len([r for r in relations if r.get("from") in entity_map and r.get("to") in entity_map])


def main():
    parser = argparse.ArgumentParser(description="Visualize knowledge graph")
    parser.add_argument("--output", "-o", default="kg_visualization.html",
                        help="Output HTML file path")
    args = parser.parse_args()

    check_dependencies()

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
    print("📂 Loading data...")
    entities = pick_dataset(seed_entities_path, processed_entities_path)
    relations = pick_dataset(seed_relations_path, processed_relations_path)
    print(f"   Loaded {len(entities)} entities")
    print(f"   Loaded {len(relations)} relations")

    # Determine output path
    if not os.path.isabs(args.output):
        output_path = os.path.join(base_dir, args.output)
    else:
        output_path = args.output

    # Create visualization
    print("\n🎨 Creating visualization...")
    node_count, edge_count = create_visualization(entities, relations, output_path)
    
    print(f"\n✅ Visualization saved to: {output_path}")
    print(f"   • {node_count} nodes")
    print(f"   • {edge_count} edges")
    print(f"\n💡 Open the HTML file in a browser to view the interactive graph.")
    print(f"   Tips:")
    print(f"   • Drag nodes to rearrange")
    print(f"   • Scroll to zoom in/out")
    print(f"   • Click a node to highlight connections")
    print(f"   • Use the filter menu to show/hide node types")


if __name__ == "__main__":
    main()
