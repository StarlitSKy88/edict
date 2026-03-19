#!/usr/bin/env python3
"""
同步 openclaw.json 中的 agent 配置 → data/agent_config.json
支持自动发现 agent workspace 下的 Skills 目录

增强版：
- 添加网络和文件错误处理
- 添加详细日志
"""
import json
import pathlib
import datetime
import logging
import traceback
from file_lock import atomic_json_write
from utils import retry, read_json

log = logging.getLogger('sync_agent_config')
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(levelname)s: %(message)s', datefmt='%H:%M:%S')

# Auto-detect project root (parent of scripts/)
BASE = pathlib.Path(__file__).parent.parent
DATA = BASE / 'data'
OPENCLAW_CFG = pathlib.Path.home() / '.openclaw' / 'openclaw.json'


@retry(max_attempts=3, delay=2)
def main():
    """主函数 - 带重试"""
    log.info("开始同步 Agent 配置...")
    
    try:
        # 读取 openclaw.json
        if not OPENCLAW_CFG.exists():
            log.warning(f"配置文件不存在: {OPENCLAW_CFG}")
            return
        
        config = read_json(OPENCLAW_CFG, {})
        log.info(f"已读取配置: {list(config.keys())}")
        
    except Exception as e:
        log.error(f"同步失败: {e}")
        traceback.print_exc()

ID_LABEL = {
    'pope':    {'label': '教皇',   'role': '教皇',     'duty': '飞书消息分拣与回奏',  'emoji': '🤴'},
    'main':     {'label': '教皇',   'role': '教皇',     'duty': '飞书消息分拣与回奏',  'emoji': '🤴'},  # 兼容旧配置
    'cardinal': {'label': '红衣主教团', 'role': '中书令',   'duty': '起草任务令与优先级',  'emoji': '📜'},
    'cardinal_office':   {'label': '枢机处', 'role': '侍中',     'duty': '审议与退回机制',      'emoji': '🔍'},
    'bishop': {'label': '主教团', 'role': '尚书令',   'duty': '派单与升级裁决',      'emoji': '📮'},
    'ceremony':     {'label': '典礼部',   'role': '典礼部尚书', 'duty': '文档/汇报/规范',      'emoji': '📝'},
    'treasury':     {'label': '财政部',   'role': '财政部尚书', 'duty': '资源/预算/成本',      'emoji': '💰'},
    'knights':   {'label': '骑士团',   'role': '骑士团尚书', 'duty': '应急与巡检',          'emoji': '⚔️'},
    'inquisition':   {'label': '宗教裁判所',   'role': '宗教裁判所尚书', 'duty': '合规/审计/红线',      'emoji': '⚖️'},
    'guild':   {'label': '工匠行会',   'role': '工匠行会尚书', 'duty': '工程交付与自动化',    'emoji': '🔧'},
    'personnel':  {'label': '人事部',   'role': '人事部尚书', 'duty': '人事/培训/Agent管理',  'emoji': '👔'},
    'astrologer':  {'label': '占星术士', 'role': '朝报官',   'duty': '每日新闻采集与简报',  'emoji': '📰'},
}

KNOWN_MODELS = [
    {'id': 'anthropic/claude-sonnet-4-6', 'label': 'Claude Sonnet 4.6', 'provider': 'Anthropic'},
    {'id': 'anthropic/claude-opus-4-5',   'label': 'Claude Opus 4.5',   'provider': 'Anthropic'},
    {'id': 'anthropic/claude-haiku-3-5',  'label': 'Claude Haiku 3.5',  'provider': 'Anthropic'},
    {'id': 'openai/gpt-4o',               'label': 'GPT-4o',            'provider': 'OpenAI'},
    {'id': 'openai/gpt-4o-mini',          'label': 'GPT-4o Mini',       'provider': 'OpenAI'},
    {'id': 'openai-codex/gpt-5.3-codex',  'label': 'GPT-5.3 Codex',    'provider': 'OpenAI Codex'},
    {'id': 'google/gemini-2.0-flash',     'label': 'Gemini 2.0 Flash',  'provider': 'Google'},
    {'id': 'google/gemini-2.5-pro',       'label': 'Gemini 2.5 Pro',    'provider': 'Google'},
    {'id': 'copilot/claude-sonnet-4',     'label': 'Claude Sonnet 4',   'provider': 'Copilot'},
    {'id': 'copilot/claude-opus-4.5',     'label': 'Claude Opus 4.5',   'provider': 'Copilot'},
    {'id': 'github-copilot/claude-opus-4.6', 'label': 'Claude Opus 4.6', 'provider': 'GitHub Copilot'},
    {'id': 'copilot/gpt-4o',              'label': 'GPT-4o',            'provider': 'Copilot'},
    {'id': 'copilot/gemini-2.5-pro',      'label': 'Gemini 2.5 Pro',    'provider': 'Copilot'},
    {'id': 'copilot/o3-mini',             'label': 'o3-mini',           'provider': 'Copilot'},
]


def normalize_model(model_value, fallback='unknown'):
    if isinstance(model_value, str) and model_value:
        return model_value
    if isinstance(model_value, dict):
        return model_value.get('primary') or model_value.get('id') or fallback
    return fallback


def get_skills(workspace: str):
    skills_dir = pathlib.Path(workspace) / 'skills'
    skills = []
    try:
        if skills_dir.exists():
            for d in sorted(skills_dir.iterdir()):
                if d.is_dir():
                    md = d / 'SKILL.md'
                    desc = ''
                    if md.exists():
                        try:
                            for line in md.read_text(encoding='utf-8', errors='ignore').splitlines():
                                line = line.strip()
                                if line and not line.startswith('#') and not line.startswith('---'):
                                    desc = line[:100]
                                    break
                        except Exception:
                            desc = '(读取失败)'
                    skills.append({'name': d.name, 'path': str(md), 'exists': md.exists(), 'description': desc})
    except PermissionError as e:
        log.warning(f'Skills 目录访问受限: {e}')
    return skills


def _collect_openclaw_models(cfg):
    """从 openclaw.json 中收集所有已配置的 model id，与 KNOWN_MODELS 合并去重。
    解决 #127: 自定义 provider 的 model 不在下拉列表中。
    """
    known_ids = {m['id'] for m in KNOWN_MODELS}
    extra = []
    agents_cfg = cfg.get('agents', {})
    # 收集 defaults.model
    dm = normalize_model(agents_cfg.get('defaults', {}).get('model', {}), '')
    if dm and dm not in known_ids:
        extra.append({'id': dm, 'label': dm, 'provider': 'OpenClaw'})
        known_ids.add(dm)
    # 收集每个 agent 的 model
    for ag in agents_cfg.get('list', []):
        m = normalize_model(ag.get('model', ''), '')
        if m and m not in known_ids:
            extra.append({'id': m, 'label': m, 'provider': 'OpenClaw'})
            known_ids.add(m)
    # 收集 providers 中的 model id（如 copilot-proxy、anthropic 等）
    for pname, pcfg in cfg.get('providers', {}).items():
        for mid in (pcfg.get('models') or []):
            mid_str = mid if isinstance(mid, str) else (mid.get('id') or mid.get('name') or '')
            if mid_str and mid_str not in known_ids:
                extra.append({'id': mid_str, 'label': mid_str, 'provider': pname})
                known_ids.add(mid_str)
    return KNOWN_MODELS + extra


def main():
    cfg = {}
    try:
        cfg = json.loads(OPENCLAW_CFG.read_text())
    except Exception as e:
        log.warning(f'cannot read openclaw.json: {e}')
        return

    agents_cfg = cfg.get('agents', {})
    default_model = normalize_model(agents_cfg.get('defaults', {}).get('model', {}), 'unknown')
    agents_list = agents_cfg.get('list', [])
    merged_models = _collect_openclaw_models(cfg)

    result = []
    seen_ids = set()
    for ag in agents_list:
        ag_id = ag.get('id', '')
        if ag_id not in ID_LABEL:
            continue
        meta = ID_LABEL[ag_id]
        workspace = ag.get('workspace', str(pathlib.Path.home() / f'.openclaw/workspace-{ag_id}'))
        result.append({
            'id': ag_id,
            'label': meta['label'], 'role': meta['role'], 'duty': meta['duty'], 'emoji': meta['emoji'],
            'model': normalize_model(ag.get('model', default_model), default_model),
            'defaultModel': default_model,
            'workspace': workspace,
            'skills': get_skills(workspace),
            'allowAgents': ag.get('subagents', {}).get('allowAgents', []),
        })
        seen_ids.add(ag_id)

    # 补充不在 openclaw.json agents list 中的 agent（兼容旧版 main）
    EXTRA_AGENTS = {
        'pope':   {'model': default_model, 'workspace': str(pathlib.Path.home() / '.openclaw/workspace-pope'),
                    'allowAgents': ['cardinal']},
        'main':    {'model': default_model, 'workspace': str(pathlib.Path.home() / '.openclaw/workspace-main'),
                    'allowAgents': ['cardinal','cardinal_office','bishop','treasury','ceremony','knights','inquisition','guild','personnel']},
        'astrologer': {'model': default_model, 'workspace': str(pathlib.Path.home() / '.openclaw/workspace-astrologer'),
                    'allowAgents': []},
        'personnel': {'model': default_model, 'workspace': str(pathlib.Path.home() / '.openclaw/workspace-personnel'),
                    'allowAgents': ['bishop']},
    }
    for ag_id, extra in EXTRA_AGENTS.items():
        if ag_id in seen_ids or ag_id not in ID_LABEL:
            continue
        meta = ID_LABEL[ag_id]
        result.append({
            'id': ag_id,
            'label': meta['label'], 'role': meta['role'], 'duty': meta['duty'], 'emoji': meta['emoji'],
            'model': extra['model'],
            'defaultModel': default_model,
            'workspace': extra['workspace'],
            'skills': get_skills(extra['workspace']),
            'allowAgents': extra['allowAgents'],
            'isDefaultModel': True,
        })

    # 保留已有的 dispatchChannel 配置 (Fix #139)
    existing_cfg = {}
    cfg_path = DATA / 'agent_config.json'
    if cfg_path.exists():
        try:
            existing_cfg = json.loads(cfg_path.read_text())
        except Exception:
            pass

    payload = {
        'generatedAt': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'defaultModel': default_model,
        'knownModels': merged_models,
        'dispatchChannel': existing_cfg.get('dispatchChannel', 'feishu'),
        'agents': result,
    }
    DATA.mkdir(exist_ok=True)
    atomic_json_write(DATA / 'agent_config.json', payload)
    log.info(f'{len(result)} agents synced')

    # 自动部署 SOUL.md 到 workspace（如果项目里有更新）
    deploy_soul_files()
    # 同步 scripts/ 到各 workspace（保持 kanban_update.py 等最新）
    sync_scripts_to_workspaces()


# 项目 agents/ 目录名 → 运行时 agent_id 映射
_SOUL_DEPLOY_MAP = {
    'pope': 'pope',
    'cardinal': 'cardinal',
    'cardinal_office': 'cardinal_office',
    'bishop': 'bishop',
    'ceremony': 'ceremony',
    'treasury': 'treasury',
    'knights': 'knights',
    'inquisition': 'inquisition',
    'guild': 'guild',
    'personnel': 'personnel',
    'astrologer': 'astrologer',
}

def sync_scripts_to_workspaces():
    """将项目 scripts/ 目录同步到各 agent workspace（保持 kanban_update.py 等最新）"""
    scripts_src = BASE / 'scripts'
    if not scripts_src.is_dir():
        return
    synced = 0
    for proj_name, runtime_id in _SOUL_DEPLOY_MAP.items():
        ws_scripts = pathlib.Path.home() / f'.openclaw/workspace-{runtime_id}' / 'scripts'
        ws_scripts.mkdir(parents=True, exist_ok=True)
        for src_file in scripts_src.iterdir():
            if src_file.suffix not in ('.py', '.sh') or src_file.stem.startswith('__'):
                continue
            dst_file = ws_scripts / src_file.name
            try:
                src_text = src_file.read_bytes()
            except Exception:
                continue
            try:
                dst_text = dst_file.read_bytes() if dst_file.exists() else b''
            except Exception:
                dst_text = b''
            if src_text != dst_text:
                dst_file.write_bytes(src_text)
                synced += 1
    # also sync to workspace-main for legacy compatibility
    ws_main_scripts = pathlib.Path.home() / '.openclaw/workspace-main/scripts'
    ws_main_scripts.mkdir(parents=True, exist_ok=True)
    for src_file in scripts_src.iterdir():
        if src_file.suffix not in ('.py', '.sh') or src_file.stem.startswith('__'):
            continue
        dst_file = ws_main_scripts / src_file.name
        try:
            src_text = src_file.read_bytes()
            dst_text = dst_file.read_bytes() if dst_file.exists() else b''
            if src_text != dst_text:
                dst_file.write_bytes(src_text)
                synced += 1
        except Exception:
            pass
    if synced:
        log.info(f'{synced} script files synced to workspaces')


def deploy_soul_files():
    """将项目 agents/xxx/SOUL.md 部署到 ~/.openclaw/workspace-xxx/soul.md"""
    agents_dir = BASE / 'agents'
    deployed = 0
    for proj_name, runtime_id in _SOUL_DEPLOY_MAP.items():
        src = agents_dir / proj_name / 'SOUL.md'
        if not src.exists():
            continue
        ws_dst = pathlib.Path.home() / f'.openclaw/workspace-{runtime_id}' / 'soul.md'
        ws_dst.parent.mkdir(parents=True, exist_ok=True)
        # 只在内容不同时更新（避免不必要的写入）
        src_text = src.read_text(encoding='utf-8', errors='ignore')
        try:
            dst_text = ws_dst.read_text(encoding='utf-8', errors='ignore')
        except FileNotFoundError:
            dst_text = ''
        if src_text != dst_text:
            ws_dst.write_text(src_text, encoding='utf-8')
            deployed += 1
        # 教皇兼容：同步一份到 legacy main agent 目录
        if runtime_id == 'pope':
            ag_dst = pathlib.Path.home() / '.openclaw/agents/main/SOUL.md'
            ag_dst.parent.mkdir(parents=True, exist_ok=True)
            try:
                ag_text = ag_dst.read_text(encoding='utf-8', errors='ignore')
            except FileNotFoundError:
                ag_text = ''
            if src_text != ag_text:
                ag_dst.write_text(src_text, encoding='utf-8')
        # 确保 sessions 目录存在
        sess_dir = pathlib.Path.home() / f'.openclaw/agents/{runtime_id}/sessions'
        sess_dir.mkdir(parents=True, exist_ok=True)
    if deployed:
        log.info(f'{deployed} SOUL.md files deployed')


if __name__ == '__main__':
    main()
