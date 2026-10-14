# 终端一：API
python -X utf8 -m uvicorn api:app --host 127.0.0.1 --port 8000
# 终端二：页面
python -X utf8 -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501