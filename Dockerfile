# CodeTutor 容器化部署
FROM python:3.10-slim

WORKDIR /app

# 先装依赖(利用镜像层缓存)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 再拷代码
COPY . .

ENV PORT=5050
EXPOSE 5050

# gunicorn 启动;timeout 120 适配 LLM 较慢调用
CMD ["gunicorn", "web_app:app", "--bind", "0.0.0.0:5050", "--workers", "1", "--threads", "4", "--timeout", "120"]
