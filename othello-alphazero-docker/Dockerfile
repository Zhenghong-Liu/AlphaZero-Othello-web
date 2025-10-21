# 使用 Miniconda 基础镜像，它已经预装了 PyTorch、NumPy 等科学计算库所需的全部系统依赖。
# 这会使构建过程更稳定，并避免许多 'slim' 镜像带来的运行时错误。
FROM continuumio/miniconda3:latest

# 设置工作目录
WORKDIR /app

# 复制依赖文件并安装 Python 库
# 注意：Miniconda 镜像通常自带 pip
COPY requirements.txt .
# 使用 pip 安装我们需要的库
RUN pip install --no-cache-dir -r requirements.txt

# 复制所有应用代码和模型 (包括 temp/best.pth.tar)
COPY . .

# 暴露 Hugging Face Spaces 要求的端口
EXPOSE 7860

# 容器启动时运行 app.py
# CMD 会在容器启动时执行
CMD ["python", "app.py"]
