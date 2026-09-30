import hashlib
import json
from pathlib import Path
import zlib

from sqlalchemy import text
from app.database import engine

MIGRATIONS = Path(__file__).resolve().parent.parent / 'db' / 'migration'


def flyway_checksum(source):
    crc = zlib.crc32(''.join(source.splitlines()).encode('utf-8'))
    return crc if crc < 2**31 else crc - 2**32


def migrate():
    files = sorted(MIGRATIONS.glob('V*__*.sql'), key=lambda p: int(p.name.split('__')[0][1:]))
    with engine.begin() as connection:
        connection.execute(text('SELECT pg_advisory_xact_lock(748391201)'))
        connection.execute(text('''CREATE TABLE IF NOT EXISTS app_schema_migrations (
            version INTEGER PRIMARY KEY, script TEXT NOT NULL, checksum TEXT NOT NULL,
            applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )'''))
        applied = {row.version: row for row in connection.execute(text(
            'SELECT version, script, checksum FROM app_schema_migrations'
        ))}
        legacy = {}
        if connection.scalar(text("SELECT to_regclass('public.flyway_schema_history')")):
            legacy = {int(row.version): row for row in connection.execute(text(
                'SELECT version, script, checksum, success FROM flyway_schema_history WHERE version IS NOT NULL'
            ))}
        available = {int(p.name.split('__')[0][1:]) for p in files}
        if (set(applied) | set(legacy)) - available:
            raise RuntimeError('Database schema is newer than this release')
        for path in files:
            version = int(path.name.split('__')[0][1:])
            source = path.read_text(encoding='utf-8')
            checksum = hashlib.sha256(source.encode()).hexdigest()
            if version in applied:
                if applied[version].checksum != checksum or applied[version].script != path.name:
                    raise RuntimeError(f'Applied migration changed: {path.name}')
                continue
            if version in legacy:
                row = legacy[version]
                if not row.success or row.script != path.name or row.checksum != flyway_checksum(source):
                    raise RuntimeError(f'Flyway history mismatch: {path.name}')
                action = 'adopted'
            else:
                connection.exec_driver_sql(source)
                action = 'applied'
            connection.execute(text('''INSERT INTO app_schema_migrations (version, script, checksum)
                VALUES (:version, :script, :checksum)'''),
                {'version': version, 'script': path.name, 'checksum': checksum})
            print(json.dumps({'event': 'migration', 'script': path.name, 'action': action}), flush=True)
    print(json.dumps({'event': 'migrations_complete', 'versions': len(files)}), flush=True)


if __name__ == '__main__':
    try:
        migrate()
    finally:
        engine.dispose()
