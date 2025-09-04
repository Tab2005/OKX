from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from tasks import run_scan_task, get_gemini_analysis_task
from celery.result import AsyncResult
import os

# 告訴 Flask，我們的靜態檔案 (網頁) 存放在 'static' 資料夾中
app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)

# --- 網頁服務路由 ---
@app.route('/')
def serve_index():
    """當使用者訪問網站根目錄時，回傳 index.html 網頁。"""
    return send_from_directory(app.static_folder, 'index.html')

# --- API 端點 ---
@app.route('/scan', methods=['POST'])
def start_scan_endpoint():
    """接收前端的掃描請求，並啟動一個背景任務。"""
    data = request.json
    task = run_scan_task.delay(
        exchange_name=data.get('exchange'),
        market_type=data.get('market'),
        quote=data.get('quote'),
        timeframe=data.get('timeframe'),
        pattern=data.get('pattern'),
        limit=data.get('limit')
    )
    return jsonify({"task_id": task.id}), 202

@app.route('/status/<task_id>', methods=['GET'])
def get_task_status_endpoint(task_id):
    """根據任務 ID，查詢掃描任務的狀態。"""
    task_result = AsyncResult(task_id, app=run_scan_task.app)
    
    response = {}
    if task_result.state == 'PENDING':
        response = {'state': task_result.state, 'status': 'Pending...'}
    elif task_result.state == 'FAILURE':
        if isinstance(task_result.info, Exception): status_text = str(task_result.info)
        elif isinstance(task_result.info, dict) and 'exc' in task_result.info: status_text = task_result.info['exc']
        else: status_text = 'Task failed with an unknown error or was ignored.'
        response = {'state': task_result.state, 'status': status_text}
    else: # SUCCESS or PROGRESS
        response = {
            'state': task_result.state,
            'current': task_result.info.get('current', 0),
            'total': task_result.info.get('total', 1),
            'status': task_result.info.get('status', '')
        }
        if 'result' in task_result.info:
            response['result'] = task_result.info['result']
            
    return jsonify(response)

@app.route('/analyze', methods=['POST'])
def start_analysis_endpoint():
    """接收前端的 AI 分析請求。"""
    signal_info = request.json
    task = get_gemini_analysis_task.delay(signal_info)
    return jsonify({"analysis_task_id": task.id}), 202

# Gunicorn 會自動尋找名為 'app' 的 Flask 物件