"""Install repository assets into the runner's disposable runtime and profile."""
import os
from pathlib import Path
import subprocess
import sys


def prepare(profile):
    configured = os.environ.get('FLOORP_TEST_RUNTIME')
    if not configured:
        raise SystemExit('Use python3 tests/run_browser_tests.py --runtime /path/to/floorp')
    runtime = Path(configured).resolve()
    # The runner creates this sentinel before copying a runtime. Never use a
    # real installation through the lower-level fixture helper.
    if not (runtime.parent / '.disposable-floorp-tests').is_file():
        raise SystemExit('Refusing to modify a runtime without the disposable-test sentinel')
    subprocess.run([sys.executable, str(Path(__file__).resolve().parents[1] / 'install.py'),
                    'install', '--runtime', str(runtime), '--profiles', str(profile),
                    '--data-dir', str(runtime / 'custom-focus-mode-assets')], check=True, stdout=subprocess.DEVNULL)
    return str(runtime / 'floorp')
