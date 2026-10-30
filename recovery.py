"""Cópias consistentes antes de mudanças de estrutura, sem restauração automática."""
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
import time
import uuid

def snapshot(source,target):
    source,target=Path(source).resolve(),Path(target).resolve()
    if source==target or target.exists():raise ValueError('A cópia deve usar um arquivo novo, diferente do banco original')
    target.parent.mkdir(parents=True,exist_ok=True)
    started=time.monotonic()
    def progress(*args):
        if time.monotonic()-started>10:raise ValueError('Banco ocupado; a cópia de segurança não foi concluída')
    try:
        with closing(sqlite3.connect(source.as_uri()+'?mode=ro',uri=True,timeout=3)) as original,closing(sqlite3.connect(target)) as copy:
            original.backup(copy,pages=256,progress=progress,sleep=.05)
            if copy.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Cópia com falha de integridade')
    except Exception:
        target.unlink(missing_ok=True)
        raise
    return target

def prepare_migration_backup(path):
    path=Path(path).resolve()
    if not path.exists() or path.stat().st_size==0:return None
    with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True,timeout=3)) as db:
        tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        needed={'fiscal_cases','fiscal_rules','fiscal_entries','fiscal_events','fiscal_reviews','fiscal_finding_reviews','fiscal_closures'}
        if needed.issubset(tables) and {'code','invoice_id'}.issubset({r[1] for r in db.execute('PRAGMA table_info(findings)')}) and {'reviewed_at','revision'}.issubset({r[1] for r in db.execute('PRAGMA table_info(fiscal_events)')}):
            return None
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    target=path.parent/'backups'/('antes-piloto-go-'+stamp+'-'+uuid.uuid4().hex[:8]+'.sqlite3')
    return snapshot(path,target)
