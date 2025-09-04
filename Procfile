web: gunicorn app:app
worker: celery -A tasks.celery_app worker -l info -P eventlet