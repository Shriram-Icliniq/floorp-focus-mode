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

Restart Floorp. Click a page, press **Ctrl+;**, and type a command such as `address toggle` or `focus toggle`. With the field empty, **Enter runs the highlighted default command**.

The installer copies runtime assets to `RUNTIME/custom-focus-mode-assets`. This keeps content-side actor modules inside the browser runtime, where its process sandbox can load them. Override this only with another runtime subdirectory using `--data-dir /path/to/floorp/assets`. The repository clone can move after installation because the browser loads the installed copy. Local edits in the installed asset directory are backed up on reinstall; edit `src/` and reinstall to make repository changes active.

The installer adds two AutoConfig files to the runtime and an activation marker to each selected profile. It does not edit shipped archives, profile preferences, profile CSS, extension settings, or native Zen's implementation. Unrelated AutoConfig configurations are rejected. See [installation and rollback](docs/installation.md) for details and existing-CSS conflicts.

## Commands

| Command | Result |
|---|---|
| `focus toggle` | Toggle custom Focus Mode; turning it off restores the normal browser |
| `address toggle` | Toggle address-bar pinning; unpinning hides the bar and separator |
| `tabs toggle` | Toggle pinning of the horizontal strip or native vertical tab rail |

A bar command issued from the normal browser enters custom Focus Mode while preserving the other bar's visible state. For example, `tabs toggle` hides tabs and leaves the address bar pinned. The menu contains these three toggles only; on/off, show/hide and temporary peek commands have been removed. Old command names in saved recency are ignored.

## When the address bar and tabs peek

| Event | Address bar | Tab bar |
|---|---|---|
| Foreground navigation to a different website | One peek when the destination is confirmed | Hidden |
| Full document navigation within the same website | Hidden | Hidden |
| SPA navigation, History API or hash changes | Hidden | Hidden |
| Reload, including one that redirects | Hidden | Hidden |
| Back/Forward, even across websites | Hidden | Hidden |
| HTTP redirect chain | Compare the final website; one peek at most | Hidden |
| Background-tab or subframe navigation | Hidden | Hidden |
| Open, close, switch, duplicate or restore a tab | No automatic address peek | Peek |
| Move, pin, unpin or group tabs | No automatic address peek | Peek |
| Ctrl+L / focusing the address field | Reveal and hold while focused | Hidden |

A website means its registrable domain, using the browser's public suffix service: `www.example.com` and `account.example.com` share a site, while `example.com` and `example.org` differ. Scheme and port changes alone do not change site context. IP addresses and local hostnames fall back to their exact host. Only HTTP(S) destinations trigger automatic site reveals; internal and local-file tabs retain explicit address access.

Site context is tracked separately per tab and updated silently on history, reloads and background loads. Switching tabs does not cause a delayed address peek. Redirect destinations are compared when committed, rather than revealing provisional intermediate sites. A confirmed site peek lasts two seconds; completion does not restart it. Tab interaction can hold tabs open independently. Explicitly pinned bars remain visible, and the address field retains its normal grace period after focus leaves it. Browser new-tab UI can focus the address field itself, which also reveals it.

## Command-line behavior

- **Ctrl+;** opens the command line from tab content, including when a text field or rich editor has focus. It overlays the bottom of the page without shifting it.
- On `about:` pages, **Ctrl+Shift+Period** also opens the command line as an alternate shortcut.
- **Enter executes the highlighted suggestion**, including with an empty or incomplete query. If nothing matches, the line stays open for correction.
- Empty input lists the most recently executed commands first. Only known command names are saved, separately per profile; raw search queries and page data are not stored.
- Search is fuzzy and case-insensitive: `adr tg` finds `address toggle`; `tbtg` finds `tabs toggle`. Match quality ranks first; recency breaks ties.
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

The command line reserves **Ctrl+;** in capture phase before ordinary page shortcut handlers, including in focused inputs, rich editors, frames and open/closed shadow editors. This deliberately claims that key combination from websites. Plain `:` and `;` always remain available to the page. Browser fields such as the address bar retain their own keyboard behavior. The alternate Ctrl+Shift+Period shortcut on internal pages remains available.

The binding uses the semicolon character with Ctrl only; Shift, Alt and Meta combinations are excluded. Both entry shortcuts stay inactive for synthetic events, IME composition, fullscreen, pointer lock, and visible active modal dialogs. Hidden consent dialogs, transparent/offscreen modal placeholders, and modeless panels do not disable the shortcut. Held keys open the menu once.

Editor focus is deliberately allowed: a hidden caret does not reliably mean a document editor has released keyboard focus. This addresses the focus restriction encountered with Google Docs; automated tests cover focused iframe/design-mode editors with invisible carets, rather than a signed-in live Google Docs document.

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
