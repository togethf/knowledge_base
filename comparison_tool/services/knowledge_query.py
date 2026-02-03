# -*- coding: utf-8 -*-
"""
Neo4j Knowledge Base Query Service
"""
import os
import sys

# Add parent directory to path for config import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
from neo4j import GraphDatabase


class KnowledgeQueryService:
    def __init__(self, uri=None, user=None, password=None):
        """Initialize Neo4j connection."""
        self.uri = uri or NEO4J_URI
        self.user = user or NEO4J_USER
        self.password = password or NEO4J_PASSWORD
        self.driver = None
        self._connect()
    
    def _connect(self):
        """Establish connection to Neo4j."""
        try:
            self.driver = GraphDatabase.driver(
                self.uri, 
                auth=(self.user, self.password)
            )
            # Test connection
            with self.driver.session() as session:
                session.run("RETURN 1")
            print(f"Connected to Neo4j at {self.uri}")
        except Exception as e:
            print(f"Failed to connect to Neo4j: {e}")
            raise ConnectionError(f"无法连接到Neo4j数据库: {e}")
    
    def close(self):
        """Close the Neo4j connection."""
        if self.driver:
            self.driver.close()
    
    def get_pest_info(self, pest_id):
        """Get detailed pest information from the knowledge base."""
        if not self.driver:
            raise ConnectionError("Neo4j连接未建立")
        
        with self.driver.session() as session:
            # Query pest node
            result = session.run("""
                MATCH (p:Pest {id: $pest_id})
                RETURN p
            """, pest_id=pest_id)
            
            pest_record = result.single()
            if not pest_record:
                return {"error": f"未在知识库中找到害虫: {pest_id}"}
            
            pest_node = dict(pest_record["p"])
            
            # Query related pesticides
            pesticides_result = session.run("""
                MATCH (p:Pest {id: $pest_id})-[:CONTROLLED_BY]->(m:Pesticide)
                RETURN m
                LIMIT 10
            """, pest_id=pest_id)
            
            pesticides = [dict(record["m"]) for record in pesticides_result]
            
            # Query symptoms
            symptoms_result = session.run("""
                MATCH (p:Pest {id: $pest_id})-[:CAUSES]->(s:Symptom)
                RETURN s
            """, pest_id=pest_id)
            
            symptoms = [dict(record["s"]) for record in symptoms_result]
            
            # Query affected crops
            crops_result = session.run("""
                MATCH (p:Pest {id: $pest_id})-[:AFFECTS]->(c:Crop)
                RETURN c
            """, pest_id=pest_id)
            
            crops = [dict(record["c"]) for record in crops_result]
            
            return {
                "pest": pest_node,
                "pesticides": pesticides,
                "symptoms": symptoms,
                "crops": crops
            }
    
    def get_pest_recommendations(self, pest_id):
        """Get pest control recommendations in a formatted way."""
        info = self.get_pest_info(pest_id)
        
        if "error" in info:
            return info
        
        pest = info.get("pest", {})
        pesticides = info.get("pesticides", [])
        symptoms = info.get("symptoms", [])
        crops = info.get("crops", [])
        
        # Format recommendations
        recommendations = {
            "pest_info": {
                "name": pest.get("name", "未知"),
                "scientific_name": pest.get("scientific_name", ""),
                "description": pest.get("description", ""),
            },
            "control_methods": {
                "biological": [],
                "chemical": [],
                "cultural": []
            },
            "pesticides": [],
            "application_timing": "低龄幼虫高峰期",
            "symptoms": [s.get("name", "") for s in symptoms if s.get("name")],
            "affected_crops": [c.get("name", "") for c in crops if c.get("name")]
        }
        
        # Process pesticides
        for p in pesticides:
            pesticide_info = {
                "name": p.get("name", ""),
                "dosage": p.get("dosage", ""),
                "concentration": p.get("concentration", ""),
                "application_method": p.get("application_method", "")
            }
            recommendations["pesticides"].append(pesticide_info)
            
            # Classify control method
            name = p.get("name", "").lower()
            if any(bio in name for bio in ["杆菌", "僵菌", "生物", "bt", "苏云金"]):
                recommendations["control_methods"]["biological"].append(p.get("name", ""))
            else:
                recommendations["control_methods"]["chemical"].append(p.get("name", ""))
        
        return recommendations
    
    def search_pest_by_name(self, name):
        """Search for a pest by Chinese or English name."""
        if not self.driver:
            raise ConnectionError("Neo4j连接未建立")
        
        with self.driver.session() as session:
            result = session.run("""
                MATCH (p:Pest)
                WHERE p.name CONTAINS $name OR p.scientific_name CONTAINS $name
                RETURN p
                LIMIT 5
            """, name=name)
            
            return [dict(record["p"]) for record in result]


# Singleton instance
_service = None

def get_knowledge_service():
    """Get or create the singleton KnowledgeQueryService instance."""
    global _service
    if _service is None:
        _service = KnowledgeQueryService()
    return _service
