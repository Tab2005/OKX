from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from tasks import run_scan_task
from celery.result import AsyncResult
import os

# 告訴 Flask，我們的靜態檔案 (網頁) 存放在 'static' 資料夾中
app = Flask(__name__, static_folder='static')
CORS(app)

# --- 新增的網頁服務路由 ---
@app.route('/')
def serve_index():
    """當使用者訪問網站根目錄時，回傳 index.html 網頁。"""
    return send_from_directory(app.static_folder, 'index.html')

# --- API 端點 (保持不變) ---
@app.route('/scan', methods=['POST'])
def start_scan():
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
def get_task_status(task_id):
    task_result = AsyncResult(task_id, app=run_scan_task.app)
    
    response = {}
    if task_result.state == 'PENDING':
        response = {'state': task_result.state, 'status': 'Pending...'}
    elif task_result.state != 'FAILURE':
        response = {
            'state': task_result.state,
            'current': task_result.info.get('current', 0),
            'total': task_result.info.get('total', 1),
            'status': task_result.info.get('status', '')
        }
        if 'result' in task_result.info:
            response['result'] = task_result.info['result']
    else:
        response = {'state': task_result.state, 'status': str(task_result.info)}
    return jsonify(response)

# Gunicorn 會自動尋找名為 'app' 的 Flask 物件