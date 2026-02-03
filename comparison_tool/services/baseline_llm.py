# -*- coding: utf-8 -*-
"""
GLM-4V API Service (Baseline VLM with Image Support)
"""
import base64
import requests
import os
import sys

# Add parent directory to path for config import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import GLM_API_KEY, GLM_BASE_URL, GLM_MODEL


class GLMVisionClient:
    def __init__(self, api_key=None, base_url=None, model=None):
        """Initialize GLM-4V API client."""
        self.api_key = api_key or GLM_API_KEY
        self.base_url = base_url or GLM_BASE_URL
        self.model = model or GLM_MODEL
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def encode_image(self, image_path):
        """Encode image to base64 with proper format detection."""
        with open(image_path, "rb") as f:
            image_data = f.read()
        
        # Detect image type
        if image_path.lower().endswith('.png'):
            mime_type = 'image/png'
        elif image_path.lower().endswith('.gif'):
            mime_type = 'image/gif'
        elif image_path.lower().endswith('.webp'):
            mime_type = 'image/webp'
        else:
            mime_type = 'image/jpeg'
        
        base64_str = base64.b64encode(image_data).decode("utf-8")
        # Return with data URI prefix as some APIs require it
        return f"data:{mime_type};base64,{base64_str}"
    
    def analyze_pest_image(self, image_path, prompt=None):
        """
        Analyze pest image using GLM-4V Vision API.
        This represents the baseline VLM without domain knowledge.
        
        Args:
            image_path: Path to the pest image
            prompt: Custom prompt (optional)
            
        Returns:
            VLM response dict
        """
        if prompt is None:
            prompt = "请识别这张图片中的害虫，并给出防治建议。"
        
        # Encode image to base64 with data URI
        image_data_uri = self.encode_image(image_path)
        print(f"[GLM-4V] 图片编码完成，长度: {len(image_data_uri)} 字符")
        
        # Build request payload following GLM-4V format
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image_data_uri
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ],
            "max_tokens": 2048
        }
        
        try:
            print(f"[GLM-4V] 调用API分析图片...")
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=120  # VLM may need more time
            )
            response.raise_for_status()
            
            result = response.json()
            message = result["choices"][0]["message"]
            
            # GLM-4V may return content in either 'content' or 'reasoning_content'
            content = message.get("content", "")
            reasoning = message.get("reasoning_content", "")
            
            # Use content if available, otherwise use reasoning_content
            final_content = content if content else reasoning
            
            print(f"[GLM-4V] 响应成功，content: {len(content)}字符, reasoning: {len(reasoning)}字符")
            
            return {
                "success": True,
                "response": final_content,
                "model": result.get("model", self.model)
            }
        except requests.exceptions.RequestException as e:
            print(f"[GLM-4V] API调用失败: {e}")
            error_msg = str(e)
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    error_msg = error_detail.get('error', {}).get('message', str(e))
                except:
                    error_msg = e.response.text[:500] if e.response.text else str(e)
            
            return {
                "success": False,
                "error": error_msg,
                "response": f"GLM-4V API调用失败: {error_msg}"
            }


# Singleton instance
_client = None

def get_glm_client():
    """Get or create the singleton GLM Vision client."""
    global _client
    if _client is None:
        _client = GLMVisionClient()
    return _client


# Keep backward compatibility
def get_deepseek_client():
    """Backward compatibility - now returns GLM client."""
    return get_glm_client()
