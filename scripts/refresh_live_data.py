#!/usr/bin/env python3
"""
Edict Live Data Refresh - 增强版
增加错误处理、数据验证、统计信息
"""
import json
import pathlib
import datetime
import logging
import time
import traceback
from typing import Any, Dict, Optional

from file_lock import atomic_json_write, atomic_json_read
from utils import read_json, retry, write_json

log = logging.getLogger('refresh')
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(levelname)s: %(message)s', datefmt='%H:%M:%S')

BASE = pathlib.Path(__file__).parent.parent
DATA = BASE / 'data'


def output_meta(path: str) -> Dict[str, Any]:
    """获取输出文件元数据"""
    if not path:
        return {"exists": False, "lastModified": None, "size": None}
    
    p = pathlib.Path(path)
    if not p.exists():
        return {"exists": False, "lastModified": None, "size": None}
    
    try:
        stat = p.stat()
        ts = datetime.datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
        return {"exists": True, "lastModified": ts, "size": stat.st_size}
    except Exception as e:
        log.warning(f"获取文件元数据失败: {e}")
        return {"exists": False, "lastModified": None, "size": None}


def check_heartbeat(updated_raw: Optional[str]) -> Dict[str, Any]:
    """检测任务心跳状态"""
    if not updated_raw:
        return {'status': 'unknown', 'label': '⚪ 未知', 'ageSec': None}
    
    try:
        now = datetime.datetime.now(datetime.timezone.utc)
        
        if isinstance(updated_raw, (int, float)):
            updated = datetime.datetime.fromtimestamp(updated_raw / 1000, tz=datetime.timezone.utc)
        else:
            updated = datetime.datetime.fromisoformat(str(updated_raw).replace('Z', '+00:00'))
        
        age_sec = (now - updated).total_seconds()
        age_min = int(age_sec // 60)
        
        if age_sec < 180:
            return {'status': 'active', 'label': f'🟢 活跃 {age_min}分钟前', 'ageSec': int(age_sec)}
        elif age_sec < 600:
            return {'status': 'warn', 'label': f'🟡 可能停滞 {age_min}分钟前', 'ageSec': int(age_sec)}
        else:
            return {'status': 'stalled', 'label': f'🔴 已停滞 {age_min}分钟', 'ageSec': int(age_sec)}
    except Exception:
        return {'status': 'unknown', 'label': '⚪ 未知', 'ageSec': None}


@retry(max_attempts=3, delay=1)
def main():
    """主函数 - 带重试"""
    start_time = time.time()
    log.info("开始刷新实时状态...")
    
    try:
        # 读取数据
        officials_data = read_json(DATA / 'officials_stats.json', {})
        officials = officials_data.get('officials', []) if isinstance(officials_data, dict) else []
        
        # 读取任务（优先 tasks_source.json）
        tasks = atomic_json_read(DATA / 'tasks_source.json', [])
        if not tasks:
            tasks = read_json(DATA / 'tasks.json', [])
        
        # 读取同步状态
        sync_status = read_json(DATA / 'sync_status.json', {})
        
        # 构建组织映射
        org_map = {o.get('label', o.get('name', '')): o.get('label', o.get('name', '')) 
                   for o in officials if o.get('label') or o.get('name')}
        
        # 处理任务
        active_count = 0
        stalled_count = 0
        
        for t in tasks:
            # 关联组织
            t['org'] = t.get('org') or org_map.get(t.get('official', ''), '')
            
            # 输出元数据
            t['outputMeta'] = output_meta(t.get('output', ''))
            
            # 心跳检测
            if t.get('state') in ('Doing', 'Assigned', 'Review'):
                updated_raw = t.get('updatedAt') or t.get('sourceMeta', {}).get('updatedAt')
                heartbeat = check_heartbeat(updated_raw)
                t['heartbeat'] = heartbeat
                
                if heartbeat['status'] == 'active':
                    active_count += 1
                elif heartbeat['status'] == 'stalled':
                    stalled_count += 1
            else:
                t['heartbeat'] = None
        
        # 统计
        today_str = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d')
        
        def is_today_done(t):
            if t.get('state') != 'Done':
                return False
            ua = t.get('updatedAt', '')
            if isinstance(ua, str) and ua[:10] == today_str:
                return True
            lm = t.get('outputMeta', {}).get('lastModified', '')
            if isinstance(lm, str) and lm[:10] == today_str:
                return True
            return False
        
        today_done = sum(1 for t in tasks if is_today_done(t))
        total_done = sum(1 for t in tasks if t.get('state') == 'Done')
        in_progress = sum(1 for t in tasks if t.get('state') in ['Doing', 'Review', 'Next', 'Blocked'])
        blocked = sum(1 for t in tasks if t.get('state') == 'Blocked')
        
        # 历史记录
        history = []
        for t in tasks:
            if t.get('state') == 'Done':
                lm = t.get('outputMeta', {}).get('lastModified')
                history.append({
                    'at': lm or '未知',
                    'official': t.get('official'),
                    'task': t.get('title'),
                    'out': t.get('output'),
                    'qa': '通过' if t.get('outputMeta', {}).get('exists') else '待补成果'
                })
        
        # 构建输出
        payload = {
            'generatedAt': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'refreshTimeMs': int((time.time() - start_time) * 1000),
            'taskSource': 'tasks_source.json' if (DATA / 'tasks_source.json').exists() else 'tasks.json',
            'officials': officials,
            'tasks': tasks,
            'history': history,
            'metrics': {
                'officialCount': len(officials),
                'todayDone': today_done,
                'totalDone': total_done,
                'inProgress': in_progress,
                'blocked': blocked,
                'activeTasks': active_count,
                'stalledTasks': stalled_count,
            },
            'syncStatus': sync_status,
            'health': {
                'syncOk': bool(sync_status.get('ok', False)),
                'syncLatencyMs': sync_status.get('durationMs'),
                'dataFresh': active_count > 0 or stalled_count == 0,
            }
        }
        
        # 写入文件
        atomic_json_write(DATA / 'live_status.json', payload)
        
        elapsed = time.time() - start_time
        log.info(f"✅ 刷新完成 ({len(tasks)} 任务, {elapsed:.2f}s)")
        
        # 告警
        if stalled_count > 0:
            log.warning(f"⚠️  有 {stalled_count} 个任务停滞超过 10 分钟")
        
        return payload
        
    except Exception as e:
        log.error(f"刷新失败: {e}")
        traceback.print_exc()
        raise


if __name__ == '__main__':
    main()
