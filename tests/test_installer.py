"""Installer checks use fake runtimes and never touch a user's browser."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('installer', ROOT / 'install.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        root = Path(self.temporary.name)
        self.runtime, self.profile = root / 'runtime', root / 'profile'
        self.data = self.runtime / 'custom data'
        (self.runtime / 'defaults/pref').mkdir(parents=True)
        self.profile.mkdir()
        (self.profile / 'prefs.js').write_text('// existing profile preferences\n')
        config = json.loads((ROOT / 'config.json').read_text())
        (self.runtime / 'platform.ini').write_text('[Build]\nBuildID=' + config['testedPackageBuildId'] + '\n')
        with zipfile.ZipFile(self.runtime / 'omni.ja', 'w') as archive:
            archive.writestr('chrome/noraneko/nora-content/assets/js/gestures.js',
                             'registerAction(action) {}\nexport { gestureActions as g };')

    def run_action(self, action, profiles=None):
        args = [action, '--runtime', str(self.runtime), '--data-dir', str(self.data)]
        if action != 'check':
            args += ['--profiles'] + [str(p) for p in (profiles or [self.profile])]
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            installer.main(args)

    def test_install_uses_selected_paths_without_altering_profile_data(self):
        self.run_action('install')
        text = (self.runtime / 'custom-focus-mode.cfg').read_text()
        self.assertIn(json.dumps(str(self.data)), text)
        self.assertNotIn('__SUPPORTED_', text)
        self.assertNotIn('__DATA_DIRECTORY__', text)
        self.assertEqual((self.profile / 'prefs.js').read_text(), '// existing profile preferences\n')
        self.assertTrue((self.profile / installer.MARKER).is_file())
        for asset in installer.ASSETS:
            self.assertEqual((self.data / asset).read_bytes(), (ROOT / 'src' / asset).read_bytes())

    def test_check_does_not_write(self):
        self.run_action('check')
        self.assertFalse(self.data.exists())
        self.assertFalse((self.profile / installer.MARKER).exists())

    def test_profile_cannot_contain_runtime_assets(self):
        self.profile = self.runtime / 'profile'
        self.profile.mkdir()
        (self.profile / 'prefs.js').write_text('// profile\n')
        self.data = self.profile / 'assets'
        with self.assertRaises(SystemExit):
            self.run_action('install')
        self.assertFalse(self.data.exists())

    def test_arbitrary_external_asset_directory_is_rejected(self):
        self.data = self.runtime.parent / 'external-assets'
        with self.assertRaises(SystemExit):
            self.run_action('install')
        self.assertFalse(self.data.exists())

    def test_default_asset_directory_is_inside_runtime(self):
        with contextlib.redirect_stdout(io.StringIO()):
            installer.main(['install', '--runtime', str(self.runtime), '--profiles', str(self.profile)])
        self.assertTrue((self.runtime / 'custom-focus-mode-assets/CommandLineChild.sys.mjs').is_file())

    def test_unsupported_build_does_not_write(self):
        (self.runtime / 'platform.ini').write_text('[Build]\nBuildID=unknown\n')
        with self.assertRaises(SystemExit):
            self.run_action('install')
        self.assertFalse(self.data.exists())
        self.assertFalse((self.profile / installer.MARKER).exists())

    def test_all_profiles_validated_before_any_mutation(self):
        with self.assertRaises(SystemExit):
            self.run_action('install', [self.profile, self.profile.parent / 'missing'])
        self.assertFalse((self.profile / installer.MARKER).exists())
        self.assertFalse(self.data.exists())

    def test_unrelated_autoconfig_is_preserved(self):
        other = self.runtime / 'defaults/pref/other.js'
        other.write_text('pref("general.config.filename", "other.cfg");')
        with self.assertRaises(SystemExit):
            self.run_action('install')
        self.assertFalse(self.data.exists())
        self.assertTrue(other.exists())

    def test_unrelated_owned_filename_is_preserved(self):
        cfg = self.runtime / 'custom-focus-mode.cfg'
        cfg.write_text('// unrelated configuration')
        for action in ['install', 'uninstall']:
            with self.assertRaises(SystemExit):
                self.run_action(action)
        self.assertEqual(cfg.read_text(), '// unrelated configuration')

    def test_reinstall_backs_up_existing_assets(self):
        self.run_action('install')
        (self.data / 'focus-mode.css').write_text('/* local modification */')
        self.run_action('install')
        saved = list((self.data / 'backups').glob('*/*focus-mode.css'))
        self.assertTrue(any(p.read_text() == '/* local modification */' for p in saved))

    def test_uninstall_removes_only_activation_and_retains_backups(self):
        self.run_action('install')
        self.run_action('uninstall')
        self.assertFalse((self.runtime / 'custom-focus-mode.cfg').exists())
        self.assertFalse((self.runtime / 'defaults/pref/custom-focus-mode.js').exists())
        self.assertFalse((self.profile / installer.MARKER).exists())
        self.assertTrue((self.data / 'focus-mode.css').exists())
        self.assertTrue((self.profile / 'prefs.js').exists())

    def test_runtime_guard_and_registry_checks_remain_in_generated_config(self):
        self.run_action('install')
        text = (self.runtime / 'custom-focus-mode.cfg').read_text()
        self.assertIn('Services.appinfo.appBuildID !== supportedBuild', text)
        self.assertIn('platformINI.getString("Build", "BuildID")', text)
        self.assertIn('marker.exists()', text)


if __name__ == '__main__':
    unittest.main()
