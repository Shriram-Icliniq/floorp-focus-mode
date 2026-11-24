# Testing

## Fast checks

Python 3.11+ is required (`hashlib.file_digest` is used). Node.js is optional for source syntax checks. The unit tests create fake runtime/profile directories and verify explicit paths, read-only checks, build rejection, AutoConfig ownership, preflight validation, backups, and uninstall behavior.

```sh
python3 -m unittest discover -s tests -p 'test_installer.py' -v
python3 -m compileall -q install.py tests
for file in src/*.js src/*.mjs; do node --check "$file"; done
```

Do not run generic test discovery over every `test_*.py` file: the browser suites are executable integration scripts and require their disposable runner. The CI workflow deliberately selects only `test_installer.py`.

## Browser suites

```sh
python3 tests/run_browser_tests.py --runtime /path/to/floorp
```

For Vimium coexistence and extension-page coverage, supply your own legally obtained XPI; the repository does not bundle extensions:

```sh
python3 tests/run_browser_tests.py \
  --runtime /path/to/floorp \
  --vimium-xpi /path/to/vimium-c.xpi
```

The runner checks the provided runtime, copies it into a temporary directory, and adds a disposable-test sentinel. The fixture installer requires that sentinel before writing to the copied runtime. Fresh profiles are created for the command and separator suites. Installed assets stay outside those protected profiles, under the copied runtime itself. No real profile is launched or modified. Allow disk space for a complete runtime copy and local socket access for automation/HTTP fixtures. Native browser startup or an optional extension can make background network requests; the fixtures and assertions use local pages and internal browser pages, not signed-in sites.

For focused command-line and editor/modal-guard checks, add `--commands-only`. For focused navigation checks in both horizontal and vertical layouts, add `--navigation-only` to the browser runner.

The runner enables `MOZ_REMOTE_ALLOW_SYSTEM_ACCESS=1` only in its test subprocess environment, because Marionette needs browser-chrome access. Ports `2892`, `2893` and `2894` must be free; direct mode suites share the active test session. Automation is not enabled in real profiles by this package.

### Coverage

| Suite | Coverage |
|---|---|
| `test_command_line.py` | Selected-row execution, recency, fuzzy ranking, native editing/undo, shortcut isolation, focus guards, frames/shadow DOM, tab protocols, new/existing tabs, optional Vimium |
| `test_integration.py` | Native palette actions, timed address reveal, pinning, navigation/reload/tab activity, horizontal/vertical layout, native Zen, native palette shortcut |
| `test_tabs_overlay.py` | Overlay geometry, separate permanent choices, interaction hold, expiry, no hover-only reveal |
| `test_navigation_peek.py` | Both bars in horizontal/vertical layouts: same-document URL updates, new documents/reload, slow HTTP redirects, completion, background/subframe loads, tab actions, explicit address focus |
| `test_address_separator.py` | Hidden/temporary/pinned separator ownership, both tab layouts, fixed-container border removal, normal/Zen restoration |

JSON reports and PNG previews are generated in `tests/` and ignored by Git. Reports can include disposable local paths and extension identifiers and should not be committed without review. Fixture profiles are created under the system temporary directory and can be inspected after a failure; delete them when no longer needed. The copied runtime is removed when the runner exits.

## Validation record

On 21 November 2026, the portable package passed **12 installer tests and 258 browser checks** on the tested Linux build, using a copied runtime and the optional Vimium C XPI: 114 command-line checks, 27 mode integration checks, 21 tab-overlay checks, 30 separator checks and 66 shared address/tab navigation checks (33 each in horizontal and vertical layouts). This record does not imply support for other builds or that CI runs the browser. Counts differ when optional Vimium checks are omitted.

On 22 November 2026, the modal-visibility fix passed **124 command-line checks and 12 installer tests**, and the command menu was verified on Scientific American's public homepage in a fresh isolated browser. The fixtures cover hidden full-screen consent dialogs, display-none/hidden/transparent ancestors, offscreen/zero-sized placeholders, visible ARIA/native modals, and native modeless dialogs. Editor punctuation and browsing capture priority remain covered. The navigation/layout suites were not rerun for this focused input-guard change.

On 23 November 2026, switching command entry to **Ctrl+;** passed **135 command-line checks and 12 installer tests** with the optional Vimium C XPI. The suite verifies entry from focused fields, rich editors, closed shadow inputs, iframe inputs and a design-mode iframe with an invisible caret, plus modal guards, plain punctuation, native editing, Vimium coexistence and tab protocols. A signed-in live Google Docs document was not tested. Navigation/layout suites were not rerun for this keyboard-only change.

On 24 November 2026, simplifying the menu to three toggles passed **137 command-line checks and 12 installer tests**, including Vimium C coexistence. Coverage includes both directions of each toggle, entering custom mode from the normal browser, removal of the eight retired commands, clearing temporary reveals on unpinning, fuzzy matching, recency, completion and editor shortcut handling. Navigation reveal behavior was not changed in this update, and navigation/layout suites were not rerun.

GitHub Actions runs the fast checks on pushes and pull requests. It does not download Floorp, fetch extensions, launch a signed-in browser, or publish generated reports.
