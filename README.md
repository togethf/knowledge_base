# 农业害虫知识图谱与智能问诊系统 (Agricultural Pest Knowledge Graph & Diagnosis System)

以害虫防治为核心的农业知识图谱知识库，支持多源数据导入、知识图谱构建、可视化以及智能问诊对比功能。

## 项目简介

本项目是一个面向农业害虫诊断和防治的完整系统，包含：
- **知识图谱 Schema**：定义实体类型和关系类型
- **数据处理工具**：从 Wikipedia、PDF 文档等来源提取和规范化知识
- **知识图谱可视化**：基于 Vis.js 的交互式图谱浏览
- **Neo4j 集成**：支持导入到 Neo4j 图数据库进行查询和应用
- **智能问诊对比工具**：比较 baseline LLM 与知识图谱增强系统 (ADCDF) 的诊断效果

## 快速开始

### 1. 验证知识库数据

```bash
cd knowledge_base
python tools/validate_kb.py
```

### 2. 查看知识图谱可视化

直接在浏览器中打开 `kg_visualization.html` 文件即可查看交互式知识图谱。

### 3. 导出为 CSV（用于 Neo4j 导入）

```bash
python tools/build_kg_csv.py
```

### 4. 导入到 Neo4j

```bash
# 设置环境
export NEO4J_URI=bolt://localhost:7687
export NEO4J_USER=neo4j
export NEO4J_PASSWORD=your_password

# 导入数据
python tools/import_to_neo4j.py

# 或者清空现有数据后导入
python tools/import_to_neo4j.py --clear
```

### 5. 启动智能问诊对比工具

```bash
cd comparison_tool
python app.py
```

然后访问 http://localhost:5000 使用问诊对比功能。

## 目录结构

```
knowledge_base/
├── schema/                     # 知识图谱 Schema 定义
│   ├── entities.json           # 实体类型定义
│   └── relations.json          # 关系类型定义
├── data/
│   ├── seed/                   # 种子数据（手动编写）
│   │   ├── seed_entities.jsonl
│   │   └── seed_relations.jsonl
│   ├── processed/              # 处理后的数据
│   │   ├── entities.jsonl      # 实体数据
│   │   ├── relations.jsonl     # 关系数据
│   │   └── *.csv               # 导出的 CSV 文件
│   ├── raw/                    # 原始数据
│   │   ├── sources/            # PDF、网页等原始资料
│   │   └── wikipedia_raw.jsonl # Wikipedia 原始数据
│   └── sources/                # 来源元数据
├── tools/                      # 数据处理工具
│   ├── validate_kb.py          # 验证知识库
│   ├── build_kg_csv.py         # 导出 CSV
│   ├── crawl_wikipedia.py      # 爬取 Wikipedia
│   ├── extract_pest_facts.py   # 从 PDF 提取害虫事实
│   ├── extract_relations_from_wikipedia_pages.py  # 从 Wikipedia 提取关系
│   ├── merge_ppp_relations.py  # 合并 PPP 事实表关系
│   ├── import_to_neo4j.py      # 导入 Neo4j
│   └── visualize_kg.py         # 生成可视化 HTML
├── comparison_tool/            # 智能问诊对比工具
│   ├── app.py                  # Flask 主应用
│   ├── config.py               # 配置文件
│   ├── services/               # 服务模块
│   │   ├── yolo_detector.py    # YOLO 害虫检测
│   │   ├── baseline_llm.py     # Baseline LLM (DeepSeek)
│   │   └── knowledge_query.py  # 知识图谱查询服务
│   ├── templates/              # HTML 模板
│   ├── static/                 # 静态资源
│   └── uploads/                # 上传图片目录
├── configs/
│   └── kb_config.yaml          # 配置文件
└── kg_visualization.html       # 知识图谱可视化页面
```

## 知识图谱 Schema

### 实体类型

| 类型 | 描述 | 必填字段 |
|------|------|----------|
| Pest | 害虫物种 | id, name |
| Disease | 植物病害 | id, name |
| Crop | 作物物种 | id, name |
| GrowthStage | 生长阶段 | id, name |
| Pesticide | 农药/杀菌剂 | id, name |
| WeatherEvent | 天气事件 | id, name |
| Symptom | 症状 | id, name |
| Location | 地理位置 | id, name |
| Image | 图片引用 | id, uri |
| Source | 数据来源 | id, name |
| Observation | 观测记录 | id, name |

### 关系类型

| 关系 | 描述 | From | To |
|------|------|------|-----|
| AFFECTS | 害虫危害作物 | Pest, Disease | Crop |
| CAUSES | 害虫导致症状 | Pest, Disease | Symptom |
| OCCURS_IN_STAGE | 害虫出现在生长阶段 | Pest, Disease | GrowthStage |
| CONTROLLED_BY | 害虫可被农药防治 | Pest, Disease | Pesticide |
| FAVORED_BY_WEATHER | 害虫/病害被天气促进 | Pest, Disease | WeatherEvent |
| OBSERVED_AT | 观测记录地点 | Observation | Location |
| OBSERVES | 观测记录害虫 | Observation | Pest, Disease |
| HAS_IMAGE | 实体有图片 | Pest, Disease, Symptom, Crop | Image |
| CITED_FROM | 引用来源 | 所有实体 | Source |

## 智能问诊对比工具 (Comparison Tool)

### 功能说明

该工具用于对比两种诊断方法的效果：

| 方法 | 描述 |
|------|------|
| **Baseline LLM** | 直接使用 DeepSeek 等大语言模型进行诊断 |
| **ADCDF System** | 知识图谱增强的诊断系统（YOLO 检测 + Neo4j 查询） |

### 系统架构

```
上传图片
   │
   ├──→ YOLO 检测器 ──→ 识别害虫类别
   │                        │
   │                        ↓
   │                   Neo4j 知识图谱 ──→ 查询防治方案
   │                        │
   │                        ↓
   └──→ Baseline LLM ←──────┘
            │
            ↓
       对比结果展示
```

### 核心模块

- `yolo_detector.py`: 基于 Ultralytics YOLO 的害虫检测
- `knowledge_query.py`: Neo4j 知识图谱查询服务
- `baseline_llm.py`: DeepSeek LLM 客户端

### 使用方法

1. 确保 Neo4j 已启动并导入了知识库数据
2. 设置环境变量：
   ```bash
   export NEO4J_URI=bolt://localhost:7687
   export NEO4J_USER=neo4j
   export NEO4J_PASSWORD=your_password
   ```
3. 启动应用：
   ```bash
   cd comparison_tool
   python app.py
   ```
4. 访问 http://localhost:5000 上传图片进行测试

## 数据格式

### JSONL 格式

实体和关系均采用 JSONL（JSON Lines）格式存储，每行一个 JSON 对象。

**实体示例**：
```json
{"id": "pest.chilo_suppressalis", "type": "Pest", "name": "二化螟", "aliases": ["Chilo suppressalis"], "description": "水稻钻蛀性害虫", "source_refs": ["source.manual_seed"]}
```

**关系示例**：
```json
{"id": "rel.pest.chilo_suppressalis.affects.crop.rice", "type": "AFFECTS", "from": "pest.chilo_suppressalis", "to": "crop.rice", "source_refs": ["source.ppp_rice_striped_stem_borer_412"]}
```

## 工具说明

| 工具 | 功能 |
|------|------|
| `validate_kb.py` | 验证知识库数据的完整性 |
| `build_kg_csv.py` | 导出为 Neo4j 导入格式的 CSV |
| `crawl_wikipedia.py` | 爬取 Wikipedia 摘要 |
| `download_wikipedia_pages.py` | 下载完整 Wikipedia 页面 |
| `extract_pest_facts.py` | 从 PDF 提取害虫防治事实 |
| `extract_relations_from_wikipedia_pages.py` | 从 Wikipedia 提取实体关系 |
| `merge_ppp_relations.py` | 合并 PPP 事实表的关系 |
| `import_to_neo4j.py` | 将数据导入 Neo4j |
| `visualize_kg.py` | 生成知识图谱可视化 HTML |

## Neo4j 查询示例

```cypher
// 查询所有害虫
MATCH (p:Pest) RETURN p.name LIMIT 25;

// 查询防治某种害虫的农药
MATCH (p:Pest)-[:CONTROLLED_BY]->(m:Pesticide)
WHERE p.name = "二化螟"
RETURN m.name;

// 查询害虫的危害作物和症状
MATCH (p:Pest)-[:AFFECTS]->(c:Crop)
MATCH (p)-[:CAUSES]->(s:Symptom)
RETURN p.name, c.name, collect(s.name) as symptoms;

// 查询某生长阶段的害虫
MATCH (p:Pest)-[:OCCURS_IN_STAGE]->(s:GrowthStage)
WHERE s.name = "Seedling"
RETURN p.name;
```

## 依赖安装

```bash
# 基础依赖
pip install neo4j pyyaml

# 知识图谱可视化
pip install vis-network

# 对比工具依赖
pip install flask ultralytics pillow requests

# 可选：PDF 处理
pip install PyPDF2

# 可选：Wikipedia 爬取
pip install requests beautifulsoup4
```

## 数据来源

- **手动种子数据**：`data/seed/` 目录下的手工编写数据
- **Wikipedia**：英文和中文 Wikipedia 页面
- **政府文档**：各地农业农村部门的害虫防治指南 PDF
- **PPP 事实表**：植物保护产品事实表

## License

本项目数据采用 [指定 License]。
