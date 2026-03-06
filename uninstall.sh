#!/bin/bash
# ══════════════════════════════════════════════════════════════
# 三省六部 · OpenClaw Multi-Agent System 一键卸载脚本
# ══════════════════════════════════════════════════════════════
set -e

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OC_HOME="$HOME/.openclaw"
OC_CFG="$OC_HOME/openclaw.json"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'

PURGE=false

banner() {
  echo ""
  echo -e "${BLUE}╔══════════════════════════════════════════╗${NC}"
  echo -e "${BLUE}║  🧹  三省六部 · OpenClaw Multi-Agent    ║${NC}"
  echo -e "${BLUE}║       卸载向导                            ║${NC}"
  echo -e "${BLUE}╚══════════════════════════════════════════╝${NC}"
  echo ""
}

usage() {
  echo "用法: ./uninstall.sh [--purge]"
  echo ""
  echo "选项:"
  echo "  --purge   执行严格深度清理（尽可能彻底移除安装/首次同步产物）"
  echo "  -h, --help  显示帮助"
}

log()   { echo -e "${GREEN}✅ $1${NC}"; }
warn()  { echo -e "${YELLOW}⚠️  $1${NC}"; }
error() { echo -e "${RED}❌ $1${NC}"; }
info()  { echo -e "${BLUE}ℹ️  $1${NC}"; }

AGENTS=(taizi zhongshu menxia shangshu hubu libu bingbu xingbu gongbu libu_hr zaochao)
ALL_RUNTIME_IDS=(taizi zhongshu menxia shangshu hubu libu bingbu xingbu gongbu libu_hr zaochao main)

parse_args() {
  while [ "$#" -gt 0 ]; do
    case "$1" in
      --purge)
        PURGE=true
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        error "未知参数: $1"
        usage
        exit 1
        ;;
    esac
    shift
  done
}

# ── Step 0: 依赖检查 ──────────────────────────────────────────
check_deps() {
  info "检查依赖..."

  if ! command -v python3 &>/dev/null; then
    error "未找到 python3"
    exit 1
  fi
  log "Python3: $(python3 --version)"

  if [ ! -d "$OC_HOME" ]; then
    warn "未找到 OpenClaw 目录: $OC_HOME（可能已卸载）"
  else
    log "OpenClaw 目录: $OC_HOME"
  fi

  if [ ! -f "$OC_CFG" ]; then
    warn "未找到 openclaw.json（将跳过注销步骤）"
  else
    log "openclaw.json: $OC_CFG"
  fi
}

# ── Step 1: 备份已有数据 ──────────────────────────────────────
backup_existing() {
  BACKUP_DIR="$OC_HOME/backups/pre-uninstall-$(date +%Y%m%d-%H%M%S)"
  NEED_BACKUP=false

  for d in "$OC_HOME"/workspace-*/; do
    if [ -d "$d" ]; then
      NEED_BACKUP=true
      break
    fi
  done

  if [ -f "$OC_CFG" ] || [ -d "$OC_HOME/agents" ]; then
    NEED_BACKUP=true
  fi

  if $NEED_BACKUP; then
    info "检测到已有数据，自动备份中..."
    mkdir -p "$BACKUP_DIR"

    for d in "$OC_HOME"/workspace-*/; do
      if [ -d "$d" ]; then
        ws_name=$(basename "$d")
        cp -R "$d" "$BACKUP_DIR/$ws_name"
      fi
    done

    if [ -f "$OC_CFG" ]; then
      cp "$OC_CFG" "$BACKUP_DIR/openclaw.json"
    fi

    if [ -d "$OC_HOME/agents" ]; then
      cp -R "$OC_HOME/agents" "$BACKUP_DIR/agents"
    fi

    log "已备份到: $BACKUP_DIR"
  else
    warn "未发现可备份内容，跳过"
  fi
}

# ── Step 2: 删除 Workspace ───────────────────────────────────
remove_workspaces() {
  info "删除三省六部 Workspace..."
  removed=0

  for agent in "${AGENTS[@]}"; do
    ws="$OC_HOME/workspace-$agent"
    if [ -d "$ws" ]; then
      rm -rf "$ws"
      removed=$((removed+1))
      log "已删除: $ws"
    fi
  done

  if [ "$removed" -eq 0 ]; then
    warn "未找到三省六部 Workspace（可能已删除）"
  fi
}

# ── Step 3: 注销 Agents ─────────────────────────────────────
unregister_agents() {
  info "从 openclaw.json 注销三省六部 Agents..."

  if [ ! -f "$OC_CFG" ]; then
    warn "openclaw.json 不存在，跳过注销"
    return
  fi

  cp "$OC_CFG" "$OC_CFG.bak.sansheng-uninstall-$(date +%Y%m%d-%H%M%S)"
  log "已备份配置: $OC_CFG.bak.*"

  python3 << 'PYEOF'
import json
import pathlib

cfg_path = pathlib.Path.home() / '.openclaw' / 'openclaw.json'
cfg = json.loads(cfg_path.read_text())

remove_ids = {
    'taizi', 'zhongshu', 'menxia', 'shangshu',
    'hubu', 'libu', 'bingbu', 'xingbu', 'gongbu',
    'libu_hr', 'zaochao',
}

agents_cfg = cfg.get('agents', {})
agents_list = agents_cfg.get('list', [])
before = len(agents_list)

agents_cfg['list'] = [a for a in agents_list if a.get('id') not in remove_ids]
cfg['agents'] = agents_cfg

cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2))
print(f'Done: {before - len(agents_cfg["list"])} agents removed')
PYEOF

  log "Agents 注销完成"
}

# ── Step 4: 清理仓库数据 ─────────────────────────────────────
cleanup_repo_data() {
  info "清理仓库 data 初始化文件..."

  if [ ! -d "$REPO_DIR/data" ]; then
    warn "未找到 $REPO_DIR/data，跳过"
    return
  fi

  FILES=(
    "$REPO_DIR/data/live_status.json"
    "$REPO_DIR/data/agent_config.json"
    "$REPO_DIR/data/model_change_log.json"
    "$REPO_DIR/data/pending_model_changes.json"
    "$REPO_DIR/data/tasks_source.json"
  )

  removed_any=false
  for f in "${FILES[@]}"; do
    if [ -f "$f" ]; then
      rm -f "$f"
      log "已删除: $f"
      removed_any=true
    fi
  done

  if ! $removed_any; then
    warn "未发现需要清理的初始化文件"
  fi
}

# ── Step 5: 严格深度清理（--purge）───────────────────────────
purge_cleanup() {
  if ! $PURGE; then
    return
  fi

  info "执行 --purge 严格深度清理..."

  # 1) 删除 ~/.openclaw/agents 下相关目录（含 legacy main）
  for agent in "${ALL_RUNTIME_IDS[@]}"; do
    if [ -d "$OC_HOME/agents/$agent" ]; then
      rm -rf "$OC_HOME/agents/$agent"
      log "已删除: $OC_HOME/agents/$agent"
    fi
  done

  # 2) 清理首次同步写入的 workspace scripts（含 legacy main）
  for runtime_id in "${ALL_RUNTIME_IDS[@]}"; do
    ws_scripts="$OC_HOME/workspace-$runtime_id/scripts"
    if [ -d "$ws_scripts" ]; then
      rm -rf "$ws_scripts"
      log "已删除: $ws_scripts"
    fi
  done

  # 3) 删除可能由首次同步创建的 legacy 兼容目录
  if [ -d "$OC_HOME/workspace-main" ]; then
    rmdir "$OC_HOME/workspace-main" 2>/dev/null || true
  fi

  # 4) 清理本项目生成的配置备份
  rm -f "$OC_CFG".bak.sansheng-* "$OC_CFG".bak.sansheng-uninstall-* 2>/dev/null || true
  log "已清理 openclaw.json 相关备份（sansheng 前缀）"

  # 5) 清理本仓库 data 目录（若为空则删除）
  if [ -d "$REPO_DIR/data" ] && [ -z "$(ls -A "$REPO_DIR/data" 2>/dev/null)" ]; then
    rmdir "$REPO_DIR/data" 2>/dev/null || true
    log "data 目录为空，已删除: $REPO_DIR/data"
  fi

  # 6) 清理 pre-uninstall/pre-install 备份（仅本项目脚本创建）
  if [ -d "$OC_HOME/backups" ]; then
    rm -rf "$OC_HOME/backups"/pre-uninstall-* 2>/dev/null || true
    rm -rf "$OC_HOME/backups"/pre-install-* 2>/dev/null || true
    log "已清理 pre-uninstall/pre-install 备份"
  fi
}

# ── Step 6: 重启 Gateway ────────────────────────────────────
restart_gateway() {
  info "重启 OpenClaw Gateway..."
  if command -v openclaw &>/dev/null; then
    if openclaw gateway restart 2>/dev/null; then
      log "Gateway 重启成功"
    else
      warn "Gateway 重启失败，请手动重启：openclaw gateway restart"
    fi
  else
    warn "未找到 openclaw CLI，跳过 Gateway 重启"
  fi
}

# ── Main ────────────────────────────────────────────────────
parse_args "$@"
banner
check_deps
backup_existing
remove_workspaces
unregister_agents
cleanup_repo_data
purge_cleanup
restart_gateway

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════╗${NC}"
if $PURGE; then
  echo -e "${GREEN}║  🧹  三省六部严格深度卸载完成（--purge）！         ║${NC}"
else
  echo -e "${GREEN}║  🧹  三省六部卸载完成！                           ║${NC}"
fi
echo -e "${GREEN}╚══════════════════════════════════════════════════╝${NC}"
echo ""
echo "说明："
echo "  1. 已移除三省六部 agents 注册与 workspace"
echo "  2. 已清理本仓库 data 下初始化文件"
if $PURGE; then
  echo "  3. 已执行严格深度清理（含 legacy main 兼容产物、同步脚本产物、备份清理）"
else
  echo "  3. 如需严格深度清理，请执行: ./uninstall.sh --purge"
fi
echo ""
