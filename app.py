from flask import Flask, request, jsonify
from flask_cors import CORS
from tasks import run_scan_task
from celery.result import AsyncResult

# 建立 Flask 應用
app = Flask(__name__)
# 允許所有來源的跨域請求，方便前端開發
CORS(app)

# --- API 端點 (我們的「下單窗口」) ---

@app.route('/scan', methods=['POST'])
def start_scan():
    """接收前端的掃描請求，並啟動一個背景任務。"""
    data = request.json
    
    # 執行背景任務，並取得任務 ID
    task = run_scan_task.delay(
        exchange_name=data.get('exchange'),
        market_type=data.get('market'),
        quote=data.get('quote'),
        timeframe=data.get('timeframe'),
        pattern=data.get('pattern'),
        limit=data.get('limit')
    )
    
    # 立刻回傳任務 ID 給前端
    return jsonify({"task_id": task.id}), 202

@app.route('/status/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """根據任務 ID，查詢掃描任務的狀態。"""
    task_result = AsyncResult(task_id, app=run_scan_task.app)
    
    if task_result.state == 'PENDING':
        # 任務尚未開始
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
        # 任務失敗
        response = {
            'state': task_result.state,
            'status': str(task_result.info), # 錯誤訊息
        }
        
    return jsonify(response)

# --- 啟動伺服器 ---
if __name__ == '__main__':
    # debug=True 會在您修改程式碼後自動重啟伺服器
    app.run(debug=True, port=5001)

