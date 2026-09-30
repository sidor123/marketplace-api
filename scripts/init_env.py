from pathlib import Path
import secrets
import sys

root = Path(__file__).resolve().parent.parent
output = Path(sys.argv[1] if len(sys.argv) > 1 else '.env')
password = secrets.token_hex(24)
source = (root / '.env.example').read_text()
source = source.replace('replace-with-random-hex-password', password)
source = source.replace('replace-with-at-least-32-random-characters', secrets.token_hex(32))
with output.open('x') as stream:
    output.chmod(0o600)
    stream.write(source)
print(f'Created {output}; secrets are not printed')
