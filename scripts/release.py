import argparse
import json
from pathlib import Path
import re
import subprocess

parser = argparse.ArgumentParser(description='Freeze a built Docker image ID and environment under a unique release ID.')
parser.add_argument('release_id')
parser.add_argument('--env-file', default='.env')
parser.add_argument('--image', required=True, help='Previously built image tag')
args = parser.parse_args()
if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', args.release_id):
    parser.error('release_id must contain only letters, digits, dots, underscores and dashes')
root = Path(__file__).resolve().parent.parent
source = Path(args.env_file).read_text()
image_id = json.loads(subprocess.check_output(
    ['docker', 'image', 'inspect', args.image], text=True))[0]['Id']
directory = root / 'artifacts' / 'releases'
directory.mkdir(parents=True, exist_ok=True)
path = directory / f'{args.release_id}.env'
with path.open('x') as output:
    path.chmod(0o600)
    output.write(source.rstrip() + '\n')
    output.write(f'APP_IMAGE={image_id}\nRELEASE_ID={args.release_id}\n')
    output.write(f'APP_ENV_FILE="{path}"\n')
print(f'Release {args.release_id}: {image_id}')
print(f'Configuration snapshot: {path} (contains secrets; do not commit or distribute)')
