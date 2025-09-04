from flask import Flask, request, jsonify
from flask_cors import CORS
from tasks import run_scan_task, get_gemini_analysis_task
from celery.result import AsyncResult

app = Flask(__name__)
CORS(app) # 允許跨來源請求，這樣我們的 index.html 檔案才能順利溝通

@app.route('/scan', methods=['POST'])
def start_scan_endpoint():
    data = request.json
    task = run_scan_task.delay(
        exchange_name=data.get('exchange'), market_type=data.get('market'),
        quote=data.get('quote'), timeframe=data.get('timeframe'),
        pattern=data.get('pattern'), limit=data.get('limit')
    )
    return jsonify({"task_id": task.id}), 202

@app.route('/status/<task_id>', methods=['GET'])
def get_task_status_endpoint(task_id):
    task_result = AsyncResult(task_id, app=run_scan_task.app)
    
    response = {}
    if task_result.state == 'PENDING':
        response = {'state': task_result.state, 'status': 'Pending...'}
    elif task_result.state == 'FAILURE':
        status_text = 'Task failed with an unknown error.'
        if isinstance(task_result.info, Exception): status_text = str(task_result.info)
        elif isinstance(task_result.info, dict) and 'exc' in task_result.info: status_text = task_result.info['exc']
        response = {'state': task_result.state, 'status': status_text}
    else: # SUCCESS, PROGRESS, or other states
        response = {
            'state': task_result.state,
            'current': task_result.info.get('current', 0) if isinstance(task_result.info, dict) else 0,
            'total': task_result.info.get('total', 1) if isinstance(task_result.info, dict) else 1,
            'status': task_result.info.get('status', '') if isinstance(task_result.info, dict) else task_result.state
        }
        if isinstance(task_result.info, dict) and 'result' in task_result.info:
            response['result'] = task_result.info['result']
    return jsonify(response)

@app.route('/analyze', methods=['POST'])
def start_analysis_endpoint():
    signal_info = request.json
    task = get_gemini_analysis_task.delay(signal_info)
    return jsonify({"analysis_task_id": task.id}), 202

# 在本地端開發時，我們使用這個來啟動伺服器
if __name__ == '__main__':
    app.run(debug=True, port=5001)
