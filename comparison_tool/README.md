# Pest Comparison Tool

A web application for comparing Standard LLM vs ADCDF System for pest diagnosis.

## Requirements

```bash
pip install flask ultralytics neo4j requests Pillow
```

## Usage

1. Make sure Neo4j is running with the knowledge base imported
2. Set environment variables if needed:
   ```bash
   export NEO4J_URI=bolt://localhost:7687
   export NEO4J_USER=neo4j
   export NEO4J_PASSWORD=your_password
   ```
3. Run the application:
   ```bash
   cd knowledge_base/comparison_tool
   python app.py
   ```
4. Open http://localhost:5000 in your browser

## Features

- Upload pest images
- Compare Standard LLM (DeepSeek) vs ADCDF System responses
- YOLO-based pest detection
- Neo4j knowledge base recommendations
- Export comparison for academic papers
