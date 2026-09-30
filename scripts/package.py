from pathlib import Path
import hashlib
import zipfile

root = Path(__file__).resolve().parent.parent
output = root / 'artifacts' / 'marketplace-homework.zip'
output.parent.mkdir(exist_ok=True)
excluded = {'.git', '.agents', '.codex', 'venv', '.venv', 'env', 'node_modules',
            '__pycache__', '.pytest_cache', '.idea', '.vscode', 'artifacts', 'generated',
            'build', 'dist', '.DS_Store'}
files = []
for path in root.rglob('*'):
    relative = path.relative_to(root)
    if any(part in excluded for part in relative.parts) or path.is_symlink() or not path.is_file():
        continue
    if (path.name.startswith('.env') and path.name != '.env.example') or path.suffix in {'.pyc', '.log', '.zip', '.db', '.sqlite3'}:
        continue
    files.append(path)
assert root / 'Отчёт.md' in files
with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(files):
        archive.write(path, Path('marketplace') / path.relative_to(root))
checksum = hashlib.sha256(output.read_bytes()).hexdigest()
output.with_suffix('.zip.sha256').write_text(f'{checksum}  {output.name}\n')
print(f'{output} ({len(files)} files, {output.stat().st_size} bytes)')
print(f'SHA-256: {checksum}')
