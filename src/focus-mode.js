/* Local browser-chrome customization. Loaded only in explicitly enabled profiles. */
(() => {
  if (window.FocusMode || !window.gBrowser) return;
  const PREF = "user.focusMode.";
  const root = document.documentElement;
  const nav = document.getElementById("nav-bar");
  const urlbar = document.getElementById("urlbar");
  if (!nav || !urlbar || !gBrowser.tabContainer) return;
  const get = (name, fallback) => Services.prefs.getBoolPref(PREF + name, fallback);
  const state = {
    enabled: get("enabled", true),
    addressPinned: get("addressPinned", false),
    tabsVisible: get("tabsVisible", false),
    ready: false,
    temporary: false,
    hold: false,
    timer: null,
    tabsTemporary: false,
    tabsHold: false,
    tabsTimer: null,
    tabsDeadline: 0,
    verticalWidth: 250,
    verticalExpanded: null,
    lastActivity: null,
    lastTabActivity: null,
  };
  const cleanup = [];
  const delay = () => Math.max(100, Services.prefs.getIntPref(PREF + "revealMs", 2000));
  const attr = (name, value) => {
    if (root.hasAttribute(name) !== !!value) root.toggleAttribute(name, !!value);
  };
  function focusInBar() {
    const active = document.activeElement;
    return !!(urlbar.hasAttribute("focused") || urlbar.contains(active) ||
      nav.contains(active) || urlbar.hasAttribute("open"));
  }
  function apply() {
    const enabled = state.enabled && state.ready && !root.hasAttribute("zenmode");
    attr("focus-mode", enabled);
    attr("focus-address-visible", enabled && (state.addressPinned || state.temporary || state.hold));
    attr("focus-address-pinned", enabled && state.addressPinned);
    const vertical = !!gBrowser.tabContainer.verticalMode;
    const tabsOverlay = enabled && !state.tabsVisible && state.tabsTemporary;
    const rail = document.querySelector("sidebar-main");
    if (vertical && rail) {
      const expanded = rail.hasAttribute("expanded");
      if (expanded !== state.verticalExpanded) {
        state.verticalExpanded = expanded;
        state.verticalWidth = expanded ? 250 : 52;
      }
      if (!root.hasAttribute("focus-tabs-overlay")) {
        const measured = rail.getBoundingClientRect().width;
        if (measured > 0 && measured < window.innerWidth * 0.9) state.verticalWidth = measured;
      }
      root.style.setProperty("--focus-vertical-overlay-width", state.verticalWidth + "px");
    }
    attr("focus-tabs-visible", enabled && (state.tabsVisible || state.tabsTemporary));
    attr("focus-tabs-pinned", enabled && state.tabsVisible);
    attr("focus-tabs-overlay", tabsOverlay);
    attr("focus-vertical", vertical);
    attr("focus-tabs-on-right", !Services.prefs.getBoolPref("sidebar.position_start", true));
    // Keep the two temporary horizontal bars stacked, not on top of each other.
    const height = tabsOverlay && !vertical && !state.addressPinned
      ? document.getElementById("TabsToolbar")?.getBoundingClientRect().height || 0 : 0;
    root.style.setProperty("--focus-tab-overlay-height", height + "px");
    const addressShown = state.addressPinned || state.temporary || state.hold;
    const top = document.getElementById("navigator-toolbox").getBoundingClientRect().bottom +
      (vertical && addressShown && !state.addressPinned ? nav.getBoundingClientRect().height : 0);
    root.style.setProperty("--focus-vertical-overlay-top", Math.max(0, top) + "px");
  }
  function save() {
    for (const key of ["enabled", "addressPinned", "tabsVisible"])
      Services.prefs.setBoolPref(PREF + key, state[key]);
  }
  function clearTimer() {
    if (state.timer !== null) window.clearTimeout(state.timer);
    state.timer = null;
  }
  function expire() {
    clearTimer();
    if (state.hold || state.addressPinned) return;
    state.timer = window.setTimeout(() => {
      state.timer = null;
      state.temporary = false;
      apply();
    }, delay());
  }
  function reveal(reason = "command") {
    if (!state.enabled || !state.ready) return;
    state.lastActivity = reason;
    state.temporary = true;
    apply();
    expire();
  }
  function clearTabsTimer() {
    if (state.tabsTimer !== null) window.clearTimeout(state.tabsTimer);
    state.tabsTimer = null;
  }
  function expireTabs() {
    clearTabsTimer();
    if (state.tabsVisible) return;
    const tick = () => {
      state.tabsTimer = null;
      if (!state.tabsTemporary || !state.enabled || state.tabsVisible) return;
      const held = tabsInUse();
      if (state.tabsHold && !held) state.tabsDeadline = performance.now() + delay();
      state.tabsHold = held;
      const remaining = state.tabsDeadline - performance.now();
      if (held || remaining > 0) {
        state.tabsTimer = window.setTimeout(tick, held ? 100 : Math.min(100, remaining));
      } else {
        state.tabsTemporary = false;
        apply();
      }
    };
    state.tabsTimer = window.setTimeout(tick, 100);
  }
  function revealTabs(reason = "tab activity") {
    if (!state.enabled || !state.ready) return;
    state.lastTabActivity = reason;
    state.tabsTemporary = true;
    state.tabsDeadline = performance.now() + delay();
    apply();
    expireTabs();
  }
  function tabsInUse() {
    const active = document.activeElement;
    const bars = gBrowser.tabContainer.verticalMode
      ? [document.getElementById("sidebar-container"), document.querySelector("sidebar-main"),
         document.getElementById("vertical-tabs"), gBrowser.tabContainer]
      : [document.getElementById("TabsToolbar")];
    return bars.some(bar => bar &&
      (bar.matches(":hover") || bar.contains(active) || bar.matches(":focus-within"))) ||
      document.getElementById("tabContextMenu")?.state === "open";
  }
  function enable() {
    // Explicitly entering this mode exits native Zen; never replaces its implementation.
    if (root.hasAttribute("zenmode"))
      window.__floorpZenModeController?.setEnabledFromUser(false);
    state.enabled = true;
    state.hold = focusInBar();
    save();
    apply();
  }
  function normal() {
    state.enabled = false;
    state.temporary = false;
    state.tabsTemporary = false;
    state.tabsHold = false;
    clearTimer();
    clearTabsTimer();
    save();
    apply();
  }
  function toggleAddress() {
    if (!state.enabled) {
      // Preserve the other bar when hiding one bar from the normal interface.
      state.tabsVisible = true;
      state.addressPinned = true;
      enable();
    }
    state.addressPinned = !state.addressPinned;
    if (!state.addressPinned) {
      state.temporary = false;
      clearTimer();
    }
    save();
    apply();
  }
  function toggleTabs() {
    if (!state.enabled) {
      state.tabsVisible = true;
      state.addressPinned = true;
      enable();
    }
    state.tabsVisible = !state.tabsVisible;
    if (!state.tabsVisible) {
      state.tabsTemporary = false;
      state.tabsHold = false;
      clearTabsTimer();
    }
    save();
    apply();
  }
  function refreshFocus() {
    const held = focusInBar() || !!document.querySelector(
      '#mainPopupSet panel[panelopen="true"], #mainPopupSet menupopup[open="true"]');
    if (held === state.hold) return;
    state.hold = held;
    if (held) {
      clearTimer();
      apply();
    } else reveal("address-bar focus left");
  }
  function listen(target, event, handler, capture = false) {
    target.addEventListener(event, handler, capture);
    cleanup.push(() => target.removeEventListener(event, handler, capture));
  }
  for (const event of ["TabOpen", "TabClose", "TabSelect", "TabMove", "TabPinned", "TabUnpinned",
    "TabGrouped", "TabUngrouped", "TabGroupCreate", "TabGroupRemoved"])
    listen(gBrowser.tabContainer, event, () => { reveal(event); revealTabs(event); });
  for (const event of ["focusin", "focusout", "popupshown", "popuphidden"])
    listen(document, event, () => window.setTimeout(refreshFocus, 0), true);
  const progress = {
    onLocationChange(webProgress) {
      if (webProgress?.isTopLevel) { reveal("navigation"); revealTabs("navigation"); }
    },
    onStateChange(webProgress, request, flags) {
      const W = Ci.nsIWebProgressListener;
      if (webProgress?.isTopLevel && (flags & W.STATE_IS_NETWORK) &&
          (flags & (W.STATE_START | W.STATE_STOP))) {
        reveal("page load/reload");
        revealTabs("page load/reload");
      }
    },
    QueryInterface: ChromeUtils.generateQI(["nsIWebProgressListener", "nsISupportsWeakReference"]),
  };
  gBrowser.addProgressListener(progress);
  cleanup.push(() => gBrowser.removeProgressListener(progress));
  const observer = new MutationObserver((records) => {
    if (records.some(r => r.target === root && r.attributeName === "zenmode") &&
        root.hasAttribute("zenmode")) normal();
    refreshFocus();
    apply();
  });
  observer.observe(root, { attributes: true, attributeFilter: ["zenmode"] });
  observer.observe(urlbar, { attributes: true, attributeFilter: ["focused", "open"] });
  observer.observe(gBrowser.tabContainer, { attributes: true, attributeFilter: ["orient", "vertical"] });
  const rail = document.querySelector("sidebar-main");
  if (rail) observer.observe(rail, { attributes: true, attributeFilter: ["expanded"] });
  cleanup.push(() => observer.disconnect());
  const verticalObserver = () => window.setTimeout(apply, 0);
  Services.prefs.addObserver("sidebar.verticalTabs", verticalObserver);
  cleanup.push(() => Services.prefs.removeObserver("sidebar.verticalTabs", verticalObserver));
  listen(window, "customizationstarting", normal);

  window.FocusMode = {
    state,
    enable, toggleAddress, toggleTabs, reveal, revealTabs,
    setAddressPinned(value) {
      state.addressPinned = !!value;
      if (!value) { state.temporary = false; clearTimer(); }
      save(); apply();
    },
    setTabsVisible(value) {
      state.tabsVisible = !!value;
      if (!value) { state.tabsTemporary = false; state.tabsHold = false; clearTabsTimer(); }
      save(); apply();
    },
    normal() {
      if (root.hasAttribute("zenmode"))
        window.__floorpZenModeController?.setEnabledFromUser(false);
      normal();
    },
    toggle() { state.enabled ? normal() : enable(); },
    ready() {
      state.ready = true;
      state.hold = focusInBar();
      // One-time migration away from the previously modified native Zen setup.
      if (!Services.prefs.getBoolPref(PREF + "migrated", false)) {
        if (root.hasAttribute("zenmode"))
          window.__floorpZenModeController?.setEnabledFromUser(false);
        Services.prefs.setBoolPref("floorp.zenmode.enabled", false);
        Services.prefs.setBoolPref(PREF + "migrated", true);
      }
      apply();
      Services.scriptloader.loadSubScript("resource://custom-focus-mode/command-line.js", window, "UTF-8");
      // A real XUL binding, rather than synthetic page keystrokes. Preserve the
      // private-window menu command, but give the chosen key to the palette.
      const nativeKey = document.getElementById("key_privatebrowsing");
      const previousDisabled = nativeKey?.getAttribute("disabled");
      nativeKey?.setAttribute("disabled", "true");
      const keys = document.createXULElement("keyset");
      keys.id = "custom-focus-mode-keyset";
      const key = document.createXULElement("key");
      key.id = "custom-focus-mode-palette-key";
      key.setAttribute("key", "P");
      key.setAttribute("modifiers", "accel,shift");
      key.addEventListener("command", () =>
        window.dispatchEvent(new Event("floorp-command-palette-toggle")));
      keys.appendChild(key);
      const mainKeys = document.getElementById("mainKeyset");
      if (mainKeys) mainKeys.parentNode.insertBefore(keys, mainKeys);
      else root.appendChild(keys);
      cleanup.push(() => {
        keys.remove();
        if (nativeKey) {
          if (previousDisabled === null) nativeKey.removeAttribute("disabled");
          else nativeKey.setAttribute("disabled", previousDisabled);
        }
      });
    },
    destroy() {
      window.FocusCommandLine?.destroy();
      clearTimer();
      clearTabsTimer();
      for (const fn of cleanup.splice(0)) { try { fn(); } catch {} }
      for (const a of ["focus-mode", "focus-address-visible", "focus-address-pinned", "focus-tabs-visible",
        "focus-tabs-pinned", "focus-tabs-overlay", "focus-tabs-on-right", "focus-vertical"])
        root.removeAttribute(a);
      root.style.removeProperty("--focus-tab-overlay-height");
      root.style.removeProperty("--focus-vertical-overlay-top");
      root.style.removeProperty("--focus-vertical-overlay-width");
      document.getElementById("custom-focus-mode-style")?.remove();
      delete window.FocusMode;
    },
  };
  listen(window, "unload", () => window.FocusMode?.destroy(), { once: true });
})();
