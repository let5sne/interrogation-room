FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
# 优先默认 PyPI 索引（魔搭构建机在境外，清华源往往不可达），失败再回退阿里云源
RUN pip install --no-cache-dir -r requirements.txt \
    || pip install --no-cache-dir -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple
COPY . .
EXPOSE 7860
CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]