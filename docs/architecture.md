# Architecture

## Loading

`install.py` renders `src/bootstrap.cfg` with exact tested build IDs and a JSON-escaped asset-directory path. It copies the runtime assets to that directory. No machine-specific absolute path is committed in the bootstrap template.

At browser startup, the AutoConfig loader checks both application and package build IDs. It registers `resource://custom-focus-mode/`, then only enables the window actor and UI bootstrap when the profile marker exists. A failed build check leaves the customization inactive.

The early `palette.mjs` adapter registers five existing Focus Mode actions with Floorp's internal action registry. Once browser delayed startup and the adapter are ready, `focus-mode.js` attaches, then `focus-mode.css` loads. The mode becomes ready after stylesheet load; the command line is attached at that point.

## Runtime files

| File | Responsibility |
|---|---|
| `loader.js` | AutoConfig activation preferences |
| `bootstrap.cfg` | Build gates, profile marker, resources, actors, window startup |
| `palette.mjs` | Adapter to Floorp's private native action registry |
| `focus-mode.js` | Per-window appearance state, reveal timers, browser/tab activity, native Zen coordination |
| `focus-mode.css` | Browser chrome, overlay geometry, separator, command UI presentation |
| `command-line.js` | Fixed command catalogue, fuzzy ranking, recency, selected-row execution, native input editing |
| `CommandLineChild.sys.mjs` | Trusted Ctrl+; handling in content frames |
| `CommandLineParent.sys.mjs` | Route requests from the focused selected tab to its browser-owned command UI |

## Input boundary

The command field and suggestions are in browser chrome; a webpage cannot inspect the input or execute commands through the public page DOM. The actor's `Open` message asks only to open the command line, not to dispatch arbitrary actions. The parent checks the selected tab and browser focus and can follow embedded internal browsers back to the actual tab.

The child reserves trusted Ctrl+; in capture phase before ordinary page handlers, regardless of editor focus. Plain punctuation is never intercepted. This avoids relying on a caret's visibility or editor implementation, including iframe/design-mode and open/closed shadow editors. The explicit Ctrl+Shift+Period internal-page shortcut remains available. Internal tabs that retain keyboard focus on the browser element use a browser-key fallback: it asks the content actor for a boolean eligibility result and rechecks the selected tab, window global, and focus before opening. Nested frame/browser focus is left to the frame's own keyboard handling. Browser chrome fields do not trigger the content shortcut.

Modal eligibility checks visibility rather than just DOM presence. Native `dialog:modal` and ARIA modal candidates block entry only while rendered visibly in the viewport; hidden/inaccessible ancestors, zero opacity, zero-sized boxes and offscreen placeholders are ignored. Modeless native dialogs do not globally block browsing shortcuts. This prevents permanently mounted but hidden consent managers, such as the one observed on Scientific American, from disabling the menu.

Command input shortcuts are intercepted in capture phase only while that input is focused. Deletion selects the relevant text and invokes the focused editor's native delete operation so Ctrl+Z works. No shell execution or local-app launcher is included.

## Appearance and geometry

The custom mode's `focus-*` attributes belong to this package and are distinct from native `zenmode`. Timers, temporary visibility and interaction holds are per window. Only saved appearance choices and recent command names are profile preferences.

Temporary horizontal tabs and the navbar stack as overlays. Temporary vertical tabs overlay the page at its existing width. Permanent bar choices use native space reservation. The address separator is a `#nav-bar::after` pseudo-element inside the same transformed/transparent box; the stationary toolbox border and ordinary-tab content outline/shadow are removed only in custom mode. Split-view focus outlines retain native styling.

## Site and tab context peeks

A per-window tabs-progress listener receives the originating browser explicitly. A weak map stores the last committed HTTP(S) site for each browser. The site key uses `Services.eTLD.getBaseDomain`, falling back to the exact ASCII host for IP addresses and local hosts; scheme and port are deliberately ignored. Top-level location callbacks update context, including background and history navigations. Non-web destinations reset that context without automatic reveal.

Only a foreground, different-site destination reveals the address bar. `LOCATION_CHANGE_SAME_DOCUMENT`, reload, session-store and error-page flags suppress automatic reveals, as do `webProgress.loadType` history/reload commands. This handles full documents, SPA updates, hashes, redirects and cross-site Back/Forward without guessing from URL text. Comparing confirmed destinations avoids showing intermediate server redirects or restarting the timer at completion. The browser contracts are documented in Mozilla's [progress interface](https://github.com/mozilla-firefox/firefox/blob/main/uriloader/base/nsIWebProgress.idl) and [location-change flags](https://github.com/mozilla-firefox/firefox/blob/main/uriloader/base/nsIWebProgressListener.idl).

Tab open/close/select/move/pin/group and session-restoring events reveal only tabs. Duplicate and restored tabs use the native tab/session-store events. Page navigation never calls the tab reveal function. Browser progress bookkeeping never moves focus or changes pinned choices. Ctrl+L/address focus still holds the address bar, followed by a grace period on blur.

## Ranking and recency

The fixed catalogue contains three commands: `focus toggle`, `address toggle` and `tabs toggle`. The menu uses the existing mode/bar toggle methods; redundant on/off, show/hide and temporary peek entries are removed. Saved recency filters out retired names. Fuzzy matching uses ordered characters and favors word starts and contiguous matches. Exact names outrank prefixes; aligned query words receive a bonus. Relevance ranks before recency; recency breaks ties; the catalogue order resolves remaining ties.

The empty query uses most-recent-first ordering. A successful command moves to the front of the per-profile list; cancellation, merely selecting a row, and unmatched input do not record usage. Input queries are not saved. Enter runs the highlighted row, even for empty or partial input. If there is no row, it reports no match and stays open.

## Updating Floorp

This package uses private browser APIs and DOM selectors, including Floorp's action registry. Compatibility checks are deliberate:

1. Obtain the new application's actual `Services.appinfo.appBuildID` and runtime `platform.ini` package BuildID.
2. Inspect the action-registry module and exports and the affected browser DOM/CSS.
3. Update `config.json` only as part of validation for that actual runtime.
4. Run installer checks and all isolated browser suites, including optional Vimium checks when available.
5. Verify hidden/temporary/pinned states visually and check native Zen and normal-mode restoration.

Do not simply remove build guards to make an untested release load. Other OS builds need their own validation even if the visible version number matches.

## Limitations

- Tested on one Linux build; this is not a stable cross-version browser API.
- The Ctrl+; entry shortcut and native Ctrl+Shift+P adapter are currently fixed in source. `config.json` records the native shortcut; it is not a general key-remapping system.
- Fullscreen, pointer lock, composing, modal-dialog and other input guards intentionally take priority over command entry.
- No Vim command chaining, external programs, shell commands, arbitrary JavaScript commands, command-line Normal mode, or full command history is implemented.
- Native undo covers input editing. Programmatic suggestion completion is not a full Vim undo/history implementation.
