.PHONY: test run docker-build docker-run clean

# 运行测试（27+ 用例）
test:
	cd backend && .venv/bin/python -m pytest -q

# 本地启动（需先 pip install -r backend/requirements.txt；设置 MODELSPACE_API_KEY 才能真调 AI）
run:
	cd backend && .venv/bin/python -m uvicorn app:app --host 0.0.0.0 --port 7860

# 构建 Docker 镜像
docker-build:
	cd backend && docker build -t interrogation:latest .

# 运行 Docker 容器（映射到 7860）
docker-run:
	docker run --rm -p 7860:7860 interrogation:latest

# 清理缓存
clean:
	find backend -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
	find backend -name .pytest_cache -type d -exec rm -rf {} + 2>/dev/null || true