#!/bin/bash
# Edict 快速部署脚本
# 一键启动所有服务

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🏛️  Edict 启动中..."

# 1. 检查 Python
if ! command -v python3 &>/dev/null; then
    echo "❌ 未找到 python3"
    exit 1
fi

# 2. 运行健康检查
echo "🔍 运行健康检查..."
python3 "$REPO_DIR/scripts/health_check.py"

# 3. 启动看板服务器
echo "📊 启动看板服务器..."
cd "$REPO_DIR/dashboard"
python3 server.py --port 7891 &
SERVER_PID=$!

echo "✅ 启动完成!"
echo "   看板: http://localhost:7891"
echo "   PID: $SERVER_PID"

# 4. 启动数据刷新循环
echo "🔄 启动数据刷新..."
cd "$REPO_DIR"
bash scripts/run_loop.sh &

echo "🎉 Edict 已就绪!"
