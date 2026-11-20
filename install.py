#!/usr/bin/env python3
"""Install removable Custom Focus Mode into an explicitly selected Floorp runtime."""
import argparse
import configparser
import datetime
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parent
ASSETS = ['focus-mode.js', 'focus-mode.css', 'command-line.js',
          'CommandLineChild.sys.mjs', 'CommandLineParent.sys.mjs', 'palette.mjs']
MARKER = 'custom-focus-mode.enabled'
OWNERSHIP = 'Custom Focus Mode loader.'


def inspect(runtime, config):
    ini = configparser.ConfigParser()
    if not ini.read(runtime / 'platform.ini'):
        raise ValueError('No platform.ini: --runtime must be the directory containing Floorp binaries and omni.ja.')
    build = ini.get('Build', 'BuildID')
    if build != config['testedPackageBuildId']:
        raise ValueError('Untested Floorp package build ' + build + '. Revalidate before enabling it.')
    with zipfile.ZipFile(runtime / 'omni.ja') as archive:
        registry = archive.read('chrome/noraneko/nora-content/assets/js/gestures.js').decode()
        if 'gestureActions as g' not in registry or 'registerAction(action)' not in registry:
            raise ValueError('Floorp action registry changed; installation cancelled.')
    with (runtime / 'omni.ja').open('rb') as archive:
        checksum = hashlib.file_digest(archive, 'sha256').hexdigest()
    return {'packageBuildId': build, 'archiveSha256': checksum}


def render_bootstrap(config, data_dir):
    text = (ROOT / 'src/bootstrap.cfg').read_text()
    text = text.replace('__SUPPORTED_BUILD_ID__', config['testedAppBuildId'])
    text = text.replace('__SUPPORTED_PACKAGE_BUILD_ID__', config['testedPackageBuildId'])
    text = text.replace('__DATA_DIRECTORY__', json.dumps(str(data_dir)))
    return text.replace('  const supportedBuild =',
                        '  Services.prefs.getDefaultBranch("").setIntPref("user.focusMode.revealMs", ' +
                        str(int(config['revealMs'])) + ');\n  const supportedBuild =')


def owned(path):
    if not path.exists():
        return True
    text = path.read_text()
    if path.name == 'custom-focus-mode.cfg':
        return text.startswith('// ' + OWNERSHIP)
    return text.startswith('// Load only the explicitly installed local Custom Focus Mode configuration.')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['install', 'check', 'uninstall'])
    parser.add_argument('--runtime', type=Path, required=True,
                        help='Directory containing Floorp binaries, platform.ini and omni.ja')
    parser.add_argument('--profiles', nargs='+', type=Path,
                        help='Profile directories from about:profiles (required for install/uninstall)')
    parser.add_argument('--data-dir', type=Path,
                        help='Asset subdirectory inside the runtime (default: RUNTIME/custom-focus-mode-assets)')
    args = parser.parse_args(argv)
    runtime = args.runtime.expanduser().resolve()
    data_dir = (args.data_dir or runtime / 'custom-focus-mode-assets').expanduser().resolve()
    if args.action == 'install' and runtime not in data_dir.parents:
        parser.error('--data-dir must be a subdirectory of --runtime so content actors can load their modules')
    profiles = [p.expanduser().resolve() for p in (args.profiles or [])]
    config = json.loads((ROOT / 'config.json').read_text())
    loader = runtime / 'defaults/pref/custom-focus-mode.js'
    cfg = runtime / 'custom-focus-mode.cfg'
    if args.action != 'check' and not profiles:
        parser.error('--profiles is required for install and uninstall')
    # Validate every destination before performing any writes or removals.
    for profile in profiles:
        if not profile.is_dir() or not any((profile / name).is_file() for name in ['prefs.js', 'user.js']):
            parser.error('Not a prepared Floorp profile: ' + str(profile))
        if args.action == 'install' and (data_dir == profile or profile in data_dir.parents):
            parser.error('--data-dir must be outside profile directories so content actors can load their modules')
    if args.action in ['install', 'uninstall']:
        for path in [loader, cfg]:
            if not owned(path):
                parser.error('Refusing to replace/remove unrelated configuration: ' + str(path))
    if args.action == 'uninstall':
        loader.unlink(missing_ok=True)
        cfg.unlink(missing_ok=True)
        for profile in profiles:
            (profile / MARKER).unlink(missing_ok=True)
        print('Disabled. Restart all Floorp processes. Installed assets and backups remain in ' + str(data_dir))
        return
    try:
        info = inspect(runtime, config)
    except (ValueError, OSError, KeyError, configparser.Error, zipfile.BadZipFile) as error:
        parser.error(str(error))
    if args.action == 'check':
        print(json.dumps({'compatible': True, **info}, indent=2))
        return
    for other in (runtime / 'defaults/pref').glob('*.js'):
        if other != loader and 'general.config.filename' in other.read_text(errors='replace'):
            parser.error('Existing AutoConfig found at ' + str(other) + '; refusing to replace it.')
    if not (runtime / 'defaults/pref').is_dir():
        parser.error('Missing defaults/pref directory in runtime')
    # Validate source assets before touching the installation.
    payloads = {name: (ROOT / 'src' / name).read_bytes() for name in ASSETS}
    bootstrap = render_bootstrap(config, data_dir)
    loader_text = (ROOT / 'src/loader.js').read_bytes()
    data_dir.mkdir(parents=True, exist_ok=True)
    backup = data_dir / 'backups' / datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    backup.mkdir(parents=True)
    existing = [cfg, loader] + [data_dir / name for name in ASSETS]
    for index, path in enumerate(existing):
        if path.is_file():
            shutil.copy2(path, backup / (str(index) + '-' + path.name))
    # Profile CSS, preferences and extension settings are deliberately untouched.
    for name, payload in payloads.items():
        (data_dir / name).write_bytes(payload)
    cfg.write_text(bootstrap)
    loader.write_bytes(loader_text)
    for profile in profiles:
        (profile / MARKER).write_text('Custom Focus Mode: remove this marker and restart to disable for this profile.\n')
    report = {'runtime': str(runtime), 'profiles': [str(p) for p in profiles],
              'dataDir': str(data_dir), 'backup': str(backup), **info}
    (data_dir / 'installation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    print('Installed. Restart all Floorp processes to activate.')


if __name__ == '__main__':
    main()
