# Installation and rollback

## Destinations

The installer requires an explicit runtime and explicit profiles for installation or removal. `check` is read-only. All selected profiles and ownership constraints are checked before installation writes begin.

| Location | Purpose |
|---|---|
| `RUNTIME/defaults/pref/custom-focus-mode.js` | Selects the local AutoConfig loader |
| `RUNTIME/custom-focus-mode.cfg` | Build guards, resource registration, profile opt-in, browser-window bootstrap |
| `DATA_DIR/` | Six runtime JavaScript/CSS/module assets copied from `src/` |
| `PROFILE/custom-focus-mode.enabled` | Profile opt-in marker |
| `DATA_DIR/backups/TIMESTAMP/` | Previous loader/config/assets backed up before reinstall |
| `DATA_DIR/installation.json` | Local installation paths and package fingerprint |

Keep `--data-dir` inside the selected runtime directory and outside any profile directory. The default is `RUNTIME/custom-focus-mode-assets`. Arbitrary temporary/home locations can be unreadable to sandboxed content processes even when parent-process scripts load successfully. The installer enforces the runtime subdirectory boundary and rejects assets inside a selected profile.

Do not publish installation reports or backups: local paths and user-edited assets can identify a machine or contain personal data. They are excluded from version control.

## Permissions and trust

This is browser-chrome code, not a normal website stylesheet or sandboxed WebExtension. The AutoConfig loader sets `general.config.sandbox_enabled` to `false` so the local customization can use browser APIs. This changes the **AutoConfig execution sandbox**; it does not turn off Firefox's web-content process sandbox or extension signature checks. Review the source before installing code with this level of access.

Use a user-owned extracted/runtime installation that you can write to. The installer does not invoke `sudo`, download a browser, bypass OS protections, or make a system installation writable. Flatpak/Snap confinement and OS-specific packaging have not been validated. Keep the runtime and installed asset directory writable only by trusted users.

## Existing CSS and AutoConfig

The public installer deliberately leaves `userChrome.css`, Floorp Style Sheets, and all profile preferences untouched. Earlier local experiments used other CSS; those are not part of this repository. If your own CSS already hides/moves the same bars, back it up and disable those conflicting rules yourself before testing this package.

Installation rejects another `general.config.filename` declaration in `defaults/pref/*.js` and refuses to overwrite unrelated files at this package's loader/config names. It does not automatically merge multiple AutoConfig systems.

## Updates

1. Close all processes using the runtime.
2. Update the repository.
3. Run `install.py check` against the actual runtime.
4. Reinstall with the same runtime, profile list, and data directory.
5. Restart Floorp.

Assets are copied, not linked to the clone. Pulling repository changes alone does not change the installed customization. Reinstall backs up prior installed assets. The version guard intentionally refuses unknown browser builds; see [update validation](architecture.md#updating-floorp).

## Disable and uninstall

Removing one profile marker disables loading for that profile after restart. It does not affect other opted-in profiles.

`install.py uninstall` removes the shared AutoConfig loader/config and the supplied profile markers. Removing the shared loader disables all profiles using that runtime, including ones not listed in that uninstall command. Assets, backups, and saved preferences remain; old CSS is not restored. Uninstall refuses unrelated loader/config files and does not require a compatible current browser build, so removal remains possible after an update.

For manual removal, close Floorp, remove `RUNTIME/defaults/pref/custom-focus-mode.js` first, then `RUNTIME/custom-focus-mode.cfg`, and remove profile markers as appropriate. Preserve unrelated configuration.

## Recovering from a failed installation

If initialization or a build check fails, the normal browser UI should remain available. If a runtime update removes the activation loader, the customization stays inactive. Disable the loader and restart before investigating a startup problem. Backups live under the selected data directory and are never automatically applied.
