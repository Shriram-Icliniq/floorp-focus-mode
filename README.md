# Floorp Focus Mode

A removable, keyboard-driven browser customization for Floorp: hide the browser chrome, reveal it when needed, and control it from a Vim-inspired `:` command line.

This repository contains the customization source, a portable installer, documentation, and automated browser checks. It contains **no browser profiles, browsing history, credentials, extension packages, or personal configuration backups**.

## What it does

- Hides the address bar and horizontal or native vertical tabs in custom Focus Mode.
- Peeks the address bar and tabs once when a foreground document load or reload starts. Fragments and History API URL updates stay quiet; HTTP redirects and load completion do not restart their timers. Tab activity remains a separate reveal trigger. Address-field focus and interaction with visible tabs hold their bars open.
- Pins the address bar and tabs independently. Pinned bars reserve space; temporary reveals overlay the page.
- Treats the address bar and its separator as one unit, leaving no stationary one-pixel line when hidden.
- Opens a browser-owned command line with `:` from browsing context, including regular pages, internal tabs, extension pages, local files, source view, and PDFs.
- Offers fuzzy matching, recent-command ordering, keyboard selection, and Vim-style input editing.
- Keeps native Zen Mode separate. Activating native Zen exits custom Focus Mode; entering custom Focus Mode exits native Zen.

## Compatibility

**Tested on Linux x86-64 with Floorp 12.21.2 / Gecko 160.0.1**, using:

| Guard | Tested value |
|---|---|
| Application build ID | `20261112140843` |
| Floorp package build ID | `20261113033321` |

These are exact compatibility guards, not a claim of support for every Floorp version. An unrecognized build leaves the customization inactive. See [architecture and update validation](docs/architecture.md) before changing the guards. Windows and macOS have not been validated.

## Install

Requires Python 3.11+ and a writable Floorp installation. No Python packages are needed.

1. Clone this repository.
2. Find your profile directory in `about:profiles` and the installation directory in `about:support`. The runtime directory must contain `floorp`, `omni.ja`, `platform.ini`, and `defaults/pref/`.
3. Close all Floorp processes using that installation, including other profiles.
4. Check compatibility, then install for the profiles you explicitly select:

```sh
git clone https://github.com/Shriram-Icliniq/floorp-focus-mode.git
cd floorp-focus-mode

python3 install.py check --runtime /path/to/floorp
python3 install.py install \
  --runtime /path/to/floorp \
  --profiles /path/to/profile
```

To enable multiple profiles, list them after `--profiles`:

```sh
python3 install.py install \
  --runtime /path/to/floorp \
  --profiles /path/to/first-profile /path/to/second-profile
```

Restart Floorp. Click a page, press `:`, and type a command such as `address show` or `focus off`. With the field empty, **Enter runs the highlighted default command**.

The installer copies runtime assets to `RUNTIME/custom-focus-mode-assets`. This keeps content-side actor modules inside the browser runtime, where its process sandbox can load them. Override this only with another runtime subdirectory using `--data-dir /path/to/floorp/assets`. The repository clone can move after installation because the browser loads the installed copy. Local edits in the installed asset directory are backed up on reinstall; edit `src/` and reinstall to make repository changes active.

The installer adds two AutoConfig files to the runtime and an activation marker to each selected profile. It does not edit shipped archives, profile preferences, profile CSS, extension settings, or native Zen's implementation. Unrelated AutoConfig configurations are rejected. See [installation and rollback](docs/installation.md) for details and existing-CSS conflicts.

## Commands

| Command | Result |
|---|---|
| `focus on` | Enable custom Focus Mode, retaining saved bar choices |
| `focus off` | Restore the normal browser, also exiting native Zen |
| `focus toggle` | Toggle custom Focus Mode |
| `address show` | Pin the address bar |
| `address hide` | Unpin and hide the address bar and separator |
| `address toggle` | Toggle address-bar pinning |
| `address peek` | Unpin and reveal the address bar temporarily |
| `tabs show` | Pin the horizontal strip or native vertical tab rail |
| `tabs hide` | Unpin and hide tabs |
| `tabs toggle` | Toggle tab pinning |
| `tabs peek` | Unpin and reveal tabs temporarily |

A bar command issued from the normal browser enters custom Focus Mode while preserving the other bar's visible state. For example, `tabs hide` hides tabs and leaves the address bar pinned. `peek` explicitly unpins that bar so it can hide again after its timer.

## When the address bar and tabs peek

| Event | Address-bar and tabs behavior |
|---|---|
| New foreground document or reload | One peek at load start |
| HTTP redirects within that load | Same peek; timer is not restarted |
| Load completes | No additional peek |
| Fragment (`#section`) change | No peek |
| `pushState` / `replaceState`, including path/query changes | No peek |
| Back/Forward within the same document | No peek |
| Back/Forward to another document | A new document-navigation peek |
| Background-tab or subframe document loads | No peek over the current page |
| Ctrl+L / focusing the address field | Reveal the address bar only; hold while focused, then the normal grace period |

Both bars use the same navigation threshold. Their default peek lasts two seconds from load start, even if loading or redirects take longer. Tab interaction can hold the tabs open independently. A later independent document navigation gets its own peek. Tab opening/closing/switching and the explicit `address` commands keep their existing behavior; these are separate triggers from navigation.

## Command-line behavior

- `:` opens the command line from tab content, including when a text field has focus. It overlays the bottom of the page without shifting it.
- On `about:` pages, **Ctrl+Shift+Period** also opens the command line as an alternate shortcut.
- **Enter executes the highlighted suggestion**, including with an empty or incomplete query. If nothing matches, the line stays open for correction.
- Empty input lists the most recently executed commands first. Only known command names are saved, separately per profile; raw search queries and page data are not stored.
- Search is fuzzy and case-insensitive: `adr sh` finds `address show`; `tbpk` finds `tabs peek`. Match quality ranks first; recency breaks ties.
- A changed query selects the top result. Up/Down or Ctrl+P/Ctrl+N moves the highlight without changing the query. Tab/Shift+Tab completes and cycles matches. Clicking a result completes it without running it.
- Execution closes the line and briefly confirms the result. Escape/Ctrl+C cancels and returns focus to the page. Switching tabs or moving focus elsewhere dismisses the line.

| Key | Effect while the command input is focused |
|---|---|
| Ctrl+W | Delete the previous whitespace-separated word, including trailing whitespace |
| Ctrl+U | Delete from the cursor to the beginning |
| Ctrl+H / Backspace | Delete the previous character |
| Ctrl+Z | Undo input edits, including deletion |
| Ctrl+N / Ctrl+P | Select next / previous suggestion |
| Left/Right, Home/End | Move the cursor normally |
| Escape / Ctrl+C | Cancel command mode |

Deletion respects selected text and preserves text after the cursor. The overridden Ctrl shortcuts take priority only inside the command input; Ctrl+W closes tabs normally outside it.

### Shortcut priority

While browsing, the command line receives `:` before a site can auto-focus an editor. If a text field, rich editor, frame input, or Settings search is already focused, `:` and `;` pass through normally. Open/closed shadow editors and ARIA input widgets are protected too. Browser fields such as the address bar retain their own typing behavior. The explicit Ctrl+Shift+Period shortcut on internal pages remains available even from a focused search field.

The plain `:` shortcut ignores Ctrl, Alt, and Meta combinations. Both shortcuts stay inactive for synthetic events, IME composition, fullscreen, pointer lock, and visible active modal dialogs. Hidden consent dialogs, transparent/offscreen modal placeholders, and modeless panels do not disable browsing shortcuts. Held keys open the menu once.

### Native palette

Ctrl+Shift+P still opens Floorp's native palette. Search for **Focus Mode** to access the original five custom actions. This binding replaces the browser's Private Window shortcut; Private Window remains available from the browser menu. Ctrl+Alt+Z is not installed by this package; native shortcut configuration remains yours to manage.

## Settings

| `about:config` preference | Meaning |
|---|---|
| `user.focusMode.enabled` | Saved custom-mode choice |
| `user.focusMode.addressPinned` | Saved address-bar pinning choice |
| `user.focusMode.tabsVisible` | Saved tab pinning choice |
| `user.focusMode.revealMs` | Reveal delay, default `2000` milliseconds; minimum `100` |
| `user.focusMode.commandLine.recentCommands` | JSON list of recent known command names |

The status row reports pinned/hidden choices; a temporary reveal does not change those choices. Saved appearance choices and command-name recency are profile-wide, including commands issued in private windows; page activity timers remain window-local.

## Disable or uninstall

To disable one profile, remove its `custom-focus-mode.enabled` marker and restart Floorp. To remove the runtime loader and selected profile markers:

```sh
python3 install.py uninstall \
  --runtime /path/to/floorp \
  --profiles /path/to/profile
```

Restart all Floorp processes. Installed assets and backups remain for inspection. Removing the shared runtime loader disables the customization in every profile using that installation. Saved appearance/recency preferences remain inert. No old CSS is automatically restored.

## Development and tests

```sh
python3 -m unittest discover -s tests -p 'test_installer.py' -v
python3 -m compileall -q install.py tests
for file in src/*.js src/*.mjs; do node --check "$file"; done

# Copies the runtime; uses disposable profiles and local fixture pages.
python3 tests/run_browser_tests.py --runtime /path/to/floorp

# Optional: include Vimium C coexistence and extension-tab checks.
python3 tests/run_browser_tests.py \
  --runtime /path/to/floorp \
  --vimium-xpi /path/to/vimium-c.xpi
```

Node.js is needed only for JavaScript syntax checks. [Testing documentation](docs/testing.md) explains isolation, prerequisites, generated artifacts, and the validation record. GitHub Actions runs installer and syntax checks; it does not download a browser or claim browser integration coverage.

## Contributing and license

Bug reports should include the Floorp version/build IDs, operating system, tab orientation, reproduction steps, and which mode is active. Share a minimal example rather than a real browser profile. Run the checks before proposing changes to runtime loading, focus guards, or keyboard handling.

[MIT license](LICENSE). This is an independent customization, not an official Floorp, Vimium C, qutebrowser, or Tridactyl project. Browser binaries and third-party extensions are not redistributed.
