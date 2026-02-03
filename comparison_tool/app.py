# -*- coding: utf-8 -*-
"""
Pest Comparison Tool - Flask Application
Compare Standard LLM vs ADCDF System for pest diagnosis
"""
import os
import sys
import uuid
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import UPLOAD_FOLDER, ALLOWED_EXTENSIONS, MAX_CONTENT_LENGTH, YOLO_CLASS_NAMES
from services.yolo_detector import get_detector
from services.baseline_llm import get_glm_client
from services.knowledge_query import get_knowledge_service

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    """Render the main comparison page."""
    return render_template('index.html')


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Serve uploaded files."""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/api/compare', methods=['POST'])
def compare():
    """
    Main comparison API endpoint.
    Runs both Baseline VLM and ADCDF system on the uploaded image.
    """
    # Check if image was uploaded
    if 'image' not in request.files:
        return jsonify({'error': '没有上传图片'}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': '没有选择文件'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': '不支持的文件格式'}), 400
    
    # Save uploaded file
    filename = secure_filename(file.filename)
    unique_filename = f"{uuid.uuid4().hex}_{filename}"
    
    # Ensure upload directory exists
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
        
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
    file.save(filepath)
    
    results = {
        'image_url': f'/uploads/{unique_filename}',
        'timestamp': datetime.now().isoformat(),
        'baseline': None,
        'adcdf': None
    }
    
    # === Run Baseline VLM (GLM-4V) - Direct Image Analysis ===
    # GLM-4V 直接分析图片，无领域知识库支持
    try:
        print("[Baseline] 调用 GLM-4V 分析图片...")
        glm_client = get_glm_client()
        
        # 直接发送图片给 GLM-4V
        baseline_response = glm_client.analyze_pest_image(
            filepath,
            prompt="请识别这张图片中的害虫，并给出防治建议。"
        )
        
        results['baseline'] = {
            'success': baseline_response.get('success', False),
            'response': baseline_response.get('response', ''),
            'source': 'GLM-4V (通用视觉大模型，无领域知识库)',
            'model': baseline_response.get('model', 'glm-4.6v')
        }
        print(f"[Baseline] GLM-4V 响应: {baseline_response.get('success')}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        results['baseline'] = {
            'success': False,
            'response': f'Baseline VLM调用失败: {str(e)}',
            'source': 'GLM-4V (通用视觉大模型)'
        }
    
    # === Run ADCDF System (YOLO + Knowledge Base) ===
    try:
        # Step 1: YOLO Detection
        print("[ADCDF] Step 1: 运行 YOLO 深度学习检测...")
        detector = get_detector()
        detections = detector.detect(filepath)
        
        print(f"[ADCDF] 检测到 {len(detections)} 个害虫")
        for d in detections:
            print(f"  - {d['class_name_zh']} ({d['confidence']}%)")
        
        if not detections:
            results['adcdf'] = {
                'success': False,
                'detections': [],
                'recommendations': None,
                'response': '未检测到害虫',
                'source': 'ADCDF (YOLO + 知识库)',
                'detection_image_url': None
            }
        else:
            # Save annotated image with Chinese labels
            annotated_filename = f"annotated_{unique_filename}"
            annotated_path = os.path.join(app.config['UPLOAD_FOLDER'], annotated_filename)
            detector.save_annotated_image_chinese(filepath, annotated_path)
            detection_image_url = f'/uploads/{annotated_filename}'
            print(f"[ADCDF] 检测结果图已保存: {annotated_path}")
            
            # Step 2: Query Knowledge Base for ALL detections
            print("[ADCDF] Step 2: 查询 Neo4j 知识图谱...")
            kb_service = get_knowledge_service()
            all_recommendations = []
            
            for detection in detections:
                if detection.get('kb_id'):
                    recs = kb_service.get_pest_recommendations(detection['kb_id'])
                    all_recommendations.append({
                        'detection': detection,
                        'recommendations': recs,
                        'kb_id': detection['kb_id']
                    })
                    print(f"[Neo4j] 查询害虫 {detection['kb_id']}: 找到 {len(recs.get('pesticides', []))} 个农药推荐")
            
            # Step 3: LLM Enhanced Generation (RAG + LLM)
            print("[ADCDF] Step 3: LLM 增强生成...")
            llm_enhanced_answer = generate_enhanced_answer(detections, all_recommendations)
            
            # Step 4: Format step-by-step ADCDF response
            print("[ADCDF] Step 4: 整合诊断结果...")
            adcdf_response = format_adcdf_step_by_step(detections, all_recommendations, llm_enhanced_answer)
            
            results['adcdf'] = {
                'success': True,
                'detections': detections,
                'all_recommendations': all_recommendations,
                'response': adcdf_response,
                'source': 'ADCDF (YOLO检测 + Neo4j知识库 + LLM增强)',
                'detection_image_url': detection_image_url,
                'data_sources': {
                    'detection': 'YOLO模型 (pest.pt)',
                    'recommendations': 'Neo4j知识图谱',
                    'enhanced_answer': 'GLM-4 LLM'
                }
            }
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        results['adcdf'] = {
            'success': False,
            'detections': [],
            'recommendations': None,
            'response': f'ADCDF系统调用失败: {str(e)}',
            'source': 'ADCDF (YOLO + 知识库)',
            'detection_image_url': None
        }
    
    return jsonify(results)


def generate_enhanced_answer(detections, all_recommendations):
    """Use LLM to generate a comprehensive answer based on KB results."""
    try:
        # Build context from detections and KB results
        pest_info_list = []
        for rec_item in all_recommendations:
            detection = rec_item['detection']
            recommendations = rec_item['recommendations']
            pest_name = detection['class_name_zh']
            
            pest_context = f"害虫: {pest_name}"
            if recommendations and 'error' not in recommendations:
                pesticides = recommendations.get('pesticides', [])
                if pesticides:
                    pesticide_names = [p.get('name', '') for p in pesticides[:5] if p.get('name')]
                    pest_context += f", 推荐农药: {', '.join(pesticide_names)}"
                symptoms = recommendations.get('symptoms', [])
                if symptoms:
                    pest_context += f", 危害症状: {', '.join(symptoms[:3])}"
            pest_info_list.append(pest_context)
        
        context = "\n".join(pest_info_list)
        
        # Build prompt for LLM
        prompt = f"""你是一位专业的农业技术顾问。根据以下害虫检测结果和知识库信息，为农户提供详细、实用、易懂的防治建议。

检测到的害虫信息:
{context}

请用通俗易懂的语言，分点回答以下内容:
1. 简要介绍这些害虫的特点和危害
2. 推荐具体的防治方法（包括农药使用方法和注意事项）
3. 给出预防措施建议

注意：回答要专业但通俗，让普通农户能看懂。不要超过300字。"""

        # Call GLM API (text only, not vision)
        glm_client = get_glm_client()
        
        import requests
        headers = {
            "Authorization": f"Bearer {glm_client.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "glm-4-flash",  # Use faster text model
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1024
        }
        
        response = requests.post(
            f"{glm_client.base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        message = result["choices"][0]["message"]
        content = message.get("content", "") or message.get("reasoning_content", "")
        
        print(f"[LLM] 生成增强回答，长度: {len(content)} 字符")
        return content
        
    except Exception as e:
        print(f"[LLM] 增强生成失败: {e}")
        return None  # Return None if LLM fails, will use KB-only answer


def format_adcdf_step_by_step(detections, all_recommendations, llm_enhanced_answer=None):
    """Format ADCDF system response with step-by-step output."""
    lines = []
    
    # Header
    lines.append("╔══════════════════════════════════════════════════════╗")
    lines.append("║          ADCDF 农业病虫害诊断系统                    ║")
    lines.append("║     Agricultural Diagnostic & Control Decision Framework   ║")
    lines.append("╚══════════════════════════════════════════════════════╝")
    lines.append("")
    
    # User Query
    lines.append("📝 用户查询: 这里面是什么虫子？")
    lines.append("")
    
    # ===== STEP 1: YOLO Detection =====
    lines.append("═══════════════════════════════════════════════════════")
    lines.append("【STEP 1】深度学习害虫检测 (YOLO模型)")
    lines.append("───────────────────────────────────────────────────────")
    lines.append(f"  ▶ 模型: pest.pt (自训练害虫检测模型)")
    lines.append(f"  ▶ 检测结果: 识别到 {len(detections)} 个害虫目标")
    lines.append("")
    
    # Group by class
    detection_counts = {}
    for d in detections:
        name = d['class_name_zh']
        if name not in detection_counts:
            detection_counts[name] = {'count': 0, 'max_conf': 0, 'kb_id': d['kb_id']}
        detection_counts[name]['count'] += 1
        detection_counts[name]['max_conf'] = max(detection_counts[name]['max_conf'], d['confidence'])
    
    for name, info in detection_counts.items():
        lines.append(f"  ✓ {name}")
        lines.append(f"    数量: {info['count']} 只 | 置信度: {info['max_conf']:.1f}%")
    lines.append("")
    
    # ===== STEP 2: Knowledge Graph Query =====
    lines.append("═══════════════════════════════════════════════════════")
    lines.append("【STEP 2】知识图谱查询 (Neo4j数据库)")
    lines.append("───────────────────────────────────────────────────────")
    
    for rec_item in all_recommendations:
        detection = rec_item['detection']
        recommendations = rec_item['recommendations']
        kb_id = rec_item['kb_id']
        
        lines.append(f"  ▶ 查询节点: {kb_id}")
        
        if recommendations and 'error' not in recommendations:
            pest_info = recommendations.get('pest_info', {})
            pesticides = recommendations.get('pesticides', [])
            
            lines.append(f"    害虫名称: {detection['class_name_zh']}")
            if pest_info.get('scientific_name'):
                lines.append(f"    学名: {pest_info['scientific_name']}")
            lines.append(f"    关联农药数量: {len(pesticides)} 种")
        else:
            lines.append(f"    ⚠ 知识库中未找到该害虫详细信息")
        lines.append("")
    
    # ===== STEP 3: Generate Recommendations =====
    lines.append("═══════════════════════════════════════════════════════")
    lines.append("【STEP 3】综合诊断与防治建议")
    lines.append("───────────────────────────────────────────────────────")
    
    for rec_item in all_recommendations:
        detection = rec_item['detection']
        recommendations = rec_item['recommendations']
        
        if recommendations and 'error' not in recommendations:
            lines.append(f"")
            lines.append(f"  ▶▶▶ {detection['class_name_zh']} 防治方案 ◀◀◀")
            
            # Biological control
            bio = recommendations.get('control_methods', {}).get('biological', [])
            if bio:
                lines.append(f"  ┌─ 生物防治:")
                for b in bio[:3]:
                    lines.append(f"  │   • {b}")
            
            # Chemical control
            chem = recommendations.get('control_methods', {}).get('chemical', [])
            if chem:
                lines.append(f"  ├─ 化学防治:")
                for c in chem[:3]:
                    lines.append(f"  │   • {c}")
            
            # Pesticides with dosage
            pesticides = recommendations.get('pesticides', [])
            if pesticides:
                lines.append(f"  ├─ 推荐农药及用量:")
                for p in pesticides[:5]:
                    name = p.get('name', '')
                    dosage = p.get('dosage', '')
                    if dosage:
                        lines.append(f"  │   • {name}: {dosage}")
                    else:
                        lines.append(f"  │   • {name}")
            
            # Symptoms
            symptoms = recommendations.get('symptoms', [])
            if symptoms:
                lines.append(f"  └─ 典型危害症状: {', '.join(symptoms[:3])}")
    
    lines.append("")
    
    # ===== Final Answer (Comprehensive for Farmers) =====
    lines.append("═══════════════════════════════════════════════════════")
    lines.append("【最终回答】")
    lines.append("═══════════════════════════════════════════════════════")
    
    # Use LLM enhanced answer if available
    if llm_enhanced_answer:
        lines.append("")
        lines.append(llm_enhanced_answer)
        lines.append("")
    else:
        # Fallback to template-based answer
        pest_names = list(detection_counts.keys())
        
        # Part 1: What pests were found
        lines.append("")
        if len(pest_names) == 1:
            name = pest_names[0]
            count = detection_counts[name]['count']
            lines.append(f"  您好！图片中的害虫是【{name}】，共发现 {count} 只。")
        else:
            lines.append(f"  您好！图片中共发现 {len(pest_names)} 种害虫：")
            for name in pest_names:
                count = detection_counts[name]['count']
                lines.append(f"    • {name} ({count}只)")
        
        lines.append("")
        
        # Part 2: Treatment recommendations for each pest
        lines.append("  📋 针对性防治建议：")
        lines.append("")
        
        for rec_item in all_recommendations:
            detection = rec_item['detection']
            recommendations = rec_item['recommendations']
            pest_name = detection['class_name_zh']
            
            if recommendations and 'error' not in recommendations:
                lines.append(f"  【{pest_name}】")
                
                # Chemical control methods
                pesticides = recommendations.get('pesticides', [])
                if pesticides:
                    top_pesticides = pesticides[:3]  # Top 3 recommendations
                    pesticide_names = [p.get('name', '') for p in top_pesticides if p.get('name')]
                    if pesticide_names:
                        lines.append(f"    推荐农药：{' / '.join(pesticide_names)}")
                    
                    # Show dosage if available
                    for p in top_pesticides[:2]:
                        dosage = p.get('dosage', '')
                        if dosage:
                            lines.append(f"    用量参考：{p.get('name')} - {dosage}")
                            break
                
                # Symptoms to watch for
                symptoms = recommendations.get('symptoms', [])
                if symptoms:
                    lines.append(f"    危害症状：{', '.join(symptoms[:2])}")
                
                lines.append("")
            else:
                lines.append(f"  【{pest_name}】")
                lines.append(f"    该害虫暂无详细防治信息，建议咨询当地农技站。")
                lines.append("")
        
        # Part 3: General advice
        lines.append("  ⚠️ 用药提示：")
        lines.append("    1. 请在病虫害发生初期及时用药")
        lines.append("    2. 严格按照说明书剂量使用，避免产生抗药性")
        lines.append("    3. 注意安全间隔期，确保农产品安全")
        lines.append("    4. 建议轮换使用不同类型农药")
        lines.append("")
    
    lines.append("═══════════════════════════════════════════════════════")
    
    return '\n'.join(lines)


@app.route('/api/yolo_classes', methods=['GET'])
def get_yolo_classes():
    """Return the list of YOLO class names."""
    return jsonify(YOLO_CLASS_NAMES)


if __name__ == '__main__':
    print("=" * 50)
    print("Pest Comparison Tool")
    print("Compare Standard LLM vs ADCDF System")
    print("=" * 50)
    print(f"Upload folder: {UPLOAD_FOLDER}")
    print("Starting Flask server...")
    app.run(host='0.0.0.0', port=5001, debug=True)
