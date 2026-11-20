#!/usr/bin/env python3
"""Run the repository's integration suites with a disposable copy of Floorp."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--runtime', type=Path, required=True)
parser.add_argument('--vimium-xpi', type=Path, help='Optional locally downloaded Vimium C XPI for coexistence checks')
parser.add_argument('--navigation-only', action='store_true', help='Run only document-navigation peek checks')
args = parser.parse_args()
runtime = args.runtime.expanduser().resolve()
subprocess.run([sys.executable, str(ROOT.parent / 'install.py'), 'check', '--runtime', str(runtime)], check=True)
if args.vimium_xpi and not args.vimium_xpi.expanduser().is_file():
    parser.error('--vimium-xpi must point to an existing XPI file')
with tempfile.TemporaryDirectory(prefix='floorp-public-tests-') as temporary:
    folder = Path(temporary)
    (folder / '.disposable-floorp-tests').touch()
    print('Copying browser runtime for isolation...', flush=True)
    shutil.copytree(runtime, folder / 'runtime', symlinks=True)
    env = {**os.environ, 'FLOORP_TEST_RUNTIME': str(folder / 'runtime'),
           'MOZ_HEADLESS': '1', 'MOZ_REMOTE_ALLOW_SYSTEM_ACCESS': '1'}
    if args.vimium_xpi:
        env['FLOORP_VIMIUM_XPI'] = str(args.vimium_xpi.expanduser().resolve())
    else:
        env.pop('FLOORP_VIMIUM_XPI', None)
    suites = ['test_navigation_peek.py'] if args.navigation_only else ['test_command_line.py', 'test_address_separator.py', 'test_navigation_peek.py']
    for suite in suites:
        subprocess.run([sys.executable, str(ROOT / suite)], env=env, check=True)
    names = ['navigation-peek-results.json'] if args.navigation_only else ['command-line-results.json', 'test-results.json', 'tabs-overlay-results.json', 'address-separator-results.json', 'navigation-peek-results.json']
    results = {name: json.loads((ROOT / name).read_text())['passed'] for name in names}
    print(json.dumps({'passed': sum(results.values()), 'suites': results}, indent=2))
