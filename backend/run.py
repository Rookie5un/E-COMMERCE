#!/usr/bin/env python3
"""
应用启动脚本
"""
import os
from dotenv import load_dotenv
from app import create_app, db

# 自动加载 backend/.env，确保 PORT、DATABASE_URL 等配置生效
# override=True: 允许 .env 覆盖已存在环境变量，避免热重载时继续使用旧值
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'), override=True)

app = create_app()

if __name__ == '__main__':
    # 开发环境运行
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
