from flask import Flask, request, jsonify
from flask_cors import CORS
from tasks import run_scan_task
from celery.result import AsyncResult
import os

# 建立 Flask 應用
app = Flask(__name__)
CORS(app)

# --- API 端點 ---
@app.route('/scan', methods=['POST'])
def start_scan():
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
def get_task_status(task_id):
    """根據任務 ID，查詢掃描任務的狀態。"""
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
    else: # 任務失敗
        response = {
            'state': task_result.state,
            'status': str(task_result.info), # 錯誤訊息
        }
    return jsonify(response)

# 在生產環境中 (如 Render)，我們會使用 Gunicorn 來啟動伺服器，
# Gunicorn 會自動尋找名為 'app' 的 Flask 物件。
# 因此，我們不再需要 if __name__ == '__main__': app.run() 這段程式碼。
# 這也讓檔案更專注於定義應用本身，而不是如何運行它。