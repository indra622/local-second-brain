"""Rebuild the opt-in comparison in an explicit external Node workspace."""
import argparse
from pathlib import Path
import os
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'frontend/astryx'
DIST = ROOT / 'src/local_knowledge_wiki/web/astryx'
ASSETS = ('index.html', 'app.js', 'app.css', 'notices.txt', 'build-manifest.json')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace', required=True, type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--write', action='store_true')
    mode.add_argument('--check', action='store_true')
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    if workspace == ROOT or ROOT in workspace.parents:
        parser.error('Use an external build workspace, never the checkout')
    stage = workspace / 'staging'
    (stage / 'src').mkdir(parents=True, exist_ok=True)
    for name in ('package.json', 'package-lock.json', 'build.mjs', 'index.html', 'test.mjs'):
        shutil.copyfile(SOURCE / name, stage / name)
    for file in (SOURCE / 'src').iterdir():
        shutil.copyfile(file, stage / 'src' / file.name)
    shutil.copytree(SOURCE / 'licenses', stage / 'licenses', dirs_exist_ok=True)
    shared = (ROOT / 'src/local_knowledge_wiki/web/map.js').read_text()
    (stage / 'src/shared-map.mjs').write_text(shared + '\nexport {KnowledgeMap};\n')
    temp = workspace / 'tmp'
    temp.mkdir(exist_ok=True)
    env = dict(os.environ, TMPDIR=str(temp), npm_config_cache=str(workspace / 'npm-cache'))
    subprocess.run(['npm', 'ci', '--ignore-scripts', '--no-audit', '--no-fund'], cwd=stage, env=env, check=True)
    subprocess.run(['npm', 'run', 'build'], cwd=stage, env=env, check=True)
    for name in ASSETS:
        actual = stage / 'dist' / name
        if args.write:
            DIST.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(actual, DIST / name)
        elif not (DIST / name).is_file() or actual.read_bytes() != (DIST / name).read_bytes():
            raise SystemExit('Source/dist mismatch: ' + name)
    print('Astryx source/dist verified' if args.check else 'Astryx fixed assets written')


if __name__ == '__main__':
    main()
