/* Browser-owned command UI: page scripts cannot inspect commands or run actions. */
(() => {
  if (window.FocusCommandLine) return;
  const html = name => document.createElementNS('http://www.w3.org/1999/xhtml', name);
  const host = html('section');
  host.id = 'focus-command-line';
  host.hidden = true;
  host.setAttribute('aria-label', 'Focus Mode command line');
  const suggestions = html('div');
  suggestions.id = 'focus-command-suggestions';
  suggestions.setAttribute('role', 'listbox');
  const row = html('div'); row.className = 'focus-command-row';
  const prompt = html('span'); prompt.textContent = ':'; prompt.setAttribute('aria-hidden', 'true');
  const input = html('input');
  input.id = 'focus-command-input'; input.type = 'text'; input.autocomplete = 'off';
  input.spellcheck = false; input.placeholder = 'Type a command';
  input.setAttribute('aria-label', 'Command'); input.setAttribute('role', 'combobox');
  input.setAttribute('aria-controls', suggestions.id); input.setAttribute('aria-autocomplete', 'list');
  const hint = html('span'); hint.className = 'focus-command-hint';
  hint.textContent = 'Tab complete · Enter run · Esc close';
  const status = html('div'); status.id = 'focus-command-status';
  status.setAttribute('role', 'status'); status.setAttribute('aria-live', 'polite');
  row.append(prompt, input, hint); host.append(suggestions, row, status);
  document.documentElement.appendChild(host);
  const toast = html('div'); toast.id = 'focus-command-toast'; toast.hidden = true;
  toast.setAttribute('role', 'status'); document.documentElement.appendChild(toast);
  let matches = [], selected = 0, previous = null, browser = null, timer;
  let completionMatches = null, completionIndex = -1;
  const normalize = text => text.trim().replace(/\s+/g, ' ').toLowerCase();
  function bar(which, action) {
    const mode = window.FocusMode;
    if (!mode.state.enabled) {
      // Starting from normal mode preserves the other bar's visible state.
      mode.state.addressPinned = true; mode.state.tabsVisible = true; mode.enable();
    }
    const address = which === 'address';
    const property = address ? 'addressPinned' : 'tabsVisible';
    const toggle = () => address ? mode.toggleAddress() : mode.toggleTabs();
    if (action === 'toggle') toggle();
    else if (action === 'peek') {
      address ? mode.setAddressPinned(false) : mode.setTabsVisible(false);
      address ? mode.reveal('command line') : mode.revealTabs('command line');
    } else {
      address ? mode.setAddressPinned(action === 'show') : mode.setTabsVisible(action === 'show');
    }
    return (address ? 'Address bar' : 'Tabs') + (action === 'peek' ? ' revealed temporarily' :
      mode.state[property] ? ' pinned' : ' hidden');
  }
  const commands = [
    {name:'focus on', description:'Enable custom Focus Mode', run:() => { FocusMode.enable(); return 'Focus Mode on'; }},
    {name:'focus off', description:'Restore the normal browser', run:() => { FocusMode.normal(); return 'Normal browser restored'; }},
    {name:'focus toggle', description:'Toggle custom Focus Mode', run:() => { FocusMode.toggle(); return 'Focus Mode ' + (FocusMode.state.enabled ? 'on' : 'off'); }},
    ...['address', 'tabs'].flatMap(which => ['show','hide','toggle','peek'].map(action => ({
      name: which + ' ' + action,
      description: ({show:'Pin', hide:'Hide', toggle:'Toggle pinning of', peek:'Temporarily reveal'})[action] +
        (which === 'address' ? ' the address bar' : ' the tabs bar'),
      run: () => bar(which, action),
    }))),
  ];
  const recentPref = 'user.focusMode.commandLine.recentCommands';
  function recentCommands() {
    try {
      const saved = JSON.parse(Services.prefs.getStringPref(recentPref, '[]'));
      return Array.isArray(saved) ? [...new Set(saved)].filter(name => commands.some(command => command.name === name)) : [];
    } catch { return []; }
  }
  function remember(command) {
    Services.prefs.setStringPref(recentPref, JSON.stringify(
      [command.name, ...recentCommands().filter(name => name !== command.name)].slice(0, commands.length)));
  }
  // Score ordered character matches, favoring word starts and consecutive runs.
  function subsequence(query, name) {
    let scores = Array(name.length).fill(-Infinity);
    for (let q = 0; q < query.length; q++) {
      const next = Array(name.length).fill(-Infinity);
      for (let i = 0; i < name.length; i++) {
        if (query[q] !== name[i]) continue;
        const boundary = i === 0 || name[i - 1] === ' ' ? 30 : 0;
        if (q === 0) next[i] = 45 + boundary - i * 2;
        else for (let previous = 0; previous < i; previous++) {
          next[i] = Math.max(next[i], scores[previous] + 45 + boundary +
            (previous === i - 1 ? 25 : -(i - previous - 1) * 4));
        }
      }
      scores = next;
    }
    return Math.max(...scores);
  }
  function ranked(query) {
    const recent = recentCommands();
    return commands.map((command, index) => {
      let score = query ? subsequence(query.replace(/ /g, ''), command.name) : 0;
      if (query && Number.isFinite(score)) {
        if (command.name === query) score += 10000;
        else if (command.name.startsWith(query)) score += 5000;
        const parts = query.split(' '), words = command.name.split(' ');
        if (parts.length > 1 && parts.length === words.length &&
            parts.every((part, i) => Number.isFinite(subsequence(part, words[i])))) score += 1000;
      }
      const used = recent.indexOf(command.name);
      return {command, score, recent: used < 0 ? commands.length : used, index};
    }).filter(item => Number.isFinite(item.score))
      .sort((a, b) => b.score - a.score || a.recent - b.recent || a.index - b.index)
      .map(item => item.command);
  }
  function render() {
    const query = normalize(input.value);
    matches = ranked(query);
    selected = Math.min(selected, Math.max(0, matches.length - 1));
    suggestions.replaceChildren();
    matches.forEach((command, index) => {
      const item = html('div'); item.id = 'focus-command-option-' + index;
      item.className = 'focus-command-option'; item.setAttribute('role', 'option');
      item.setAttribute('aria-selected', String(index === selected));
      const name = html('strong'); name.textContent = command.name;
      const description = html('span'); description.textContent = command.description;
      item.append(name, description);
      item.addEventListener('mousedown', event => {
        event.preventDefault(); input.value = command.name; selected = 0;
        completionMatches = null; render(); input.focus();
      });
      suggestions.appendChild(item);
    });
    input.setAttribute('aria-expanded', String(matches.length > 0));
    if (matches.length) input.setAttribute('aria-activedescendant', 'focus-command-option-' + selected);
    else input.removeAttribute('aria-activedescendant');
    suggestions.children[selected]?.scrollIntoView({block:'nearest'});
    const state = FocusMode.state;
    status.textContent = `Focus ${state.enabled ? 'on' : 'off'} · Address ${!state.enabled || state.addressPinned ? 'pinned' : 'hidden'} · Tabs ${!state.enabled || state.tabsVisible ? 'pinned' : 'hidden'}`;
    status.removeAttribute('data-error');
  }
  function close(restore = true) {
    if (host.hidden) return;
    host.hidden = true;
    if (restore && browser === gBrowser.selectedBrowser) {
      if (previous?.isConnected) previous.focus();
      else browser.focus();
    }
    previous = browser = null;
  }
  function open() {
    if (!FocusMode?.state.ready || !host.hidden ||
        document.getElementById('command-palette-overlay') ||
        document.documentElement.hasAttribute('customizing') ||
        document.querySelector('#mainPopupSet panel[panelopen="true"], #mainPopupSet menupopup[open="true"]')) return;
    previous = document.activeElement; browser = gBrowser.selectedBrowser;
    toast.hidden = true; input.value = ''; selected = 0;
    completionMatches = null; completionIndex = -1;
    host.hidden = false; render(); input.focus();
  }
  function onInput() { selected = 0; completionMatches = null; completionIndex = -1; render(); }
  function erase(kind) {
    let start = input.selectionStart, end = input.selectionEnd;
    if (start === end) {
      if (kind === 'word') start = input.value.slice(0, start).replace(/\S+\s*$|\s+$/, '').length;
      else if (kind === 'line') start = 0;
      else {
        const chars = Array.from(input.value.slice(0, start));
        start -= chars.length ? chars[chars.length - 1].length : 0;
      }
    }
    if (start === end) return;
    input.setSelectionRange(start, end);
    // Use the focused editor so deletions join its native undo history.
    document.execCommand('delete');
  }
  function onKey(event) {
    if (host.hidden || event.target !== input) return;
    if (event.isComposing || event.keyCode === 229) return;
    const control = event.ctrlKey && !event.altKey && !event.metaKey && !event.shiftKey;
    const letter = event.key.toLowerCase();
    const editing = control && ['w','u','h'].includes(letter);
    const down = event.key === 'ArrowDown' || (control && letter === 'n');
    const up = event.key === 'ArrowUp' || (control && letter === 'p');
    const cancel = event.key === 'Escape' || (control && letter === 'c');
    if (!editing && !down && !up && !cancel && !['Tab','Enter'].includes(event.key)) return;
    // Capture before native Ctrl+W/U/H/N/P browser accelerators run.
    event.preventDefault(); event.stopImmediatePropagation();
    if (editing) erase(({w:'word',u:'line',h:'character'})[letter]);
    else if (cancel) close();
    else if (down || up) {
      completionMatches = null;
      if (matches.length) selected = (selected + (down ? 1 : -1) + matches.length) % matches.length;
      render();
    } else if (event.key === 'Tab') {
      event.preventDefault();
      if (!completionMatches) { completionMatches = [...matches]; completionIndex = selected - (event.shiftKey ? -1 : 1); }
      if (!completionMatches.length) return;
      completionIndex = (completionIndex + (event.shiftKey ? -1 : 1) + completionMatches.length) % completionMatches.length;
      input.value = completionMatches[completionIndex].name; selected = 0; render();
    } else if (event.key === 'Enter') {
      event.preventDefault();
      const command = matches[selected];
      if (!command) {
        status.textContent = 'No matching command. Edit it or press Escape.';
        status.setAttribute('data-error', 'true'); return;
      }
      try {
        close(); const message = command.run(); remember(command);
        toast.textContent = message; toast.hidden = false;
        clearTimeout(timer); timer = setTimeout(() => { toast.hidden = true; }, 1800);
      } catch (error) { open(); input.value = command.name; render(); status.textContent = 'Command failed. Try again.'; status.setAttribute('data-error', 'true'); console.error(error); }
    }
  }
  const onTab = () => close(false);
  // Some non-remote internal documents leave keyboard focus on their browser
  // element. Check the content actor before opening from that browser event.
  const onBrowserKey = async event => {
    const target = gBrowser.selectedBrowser;
    if (event.key !== ':' || !event.isTrusted || event.defaultPrevented ||
        event.isComposing || event.keyCode === 229 || event.repeat ||
        event.ctrlKey || event.altKey || event.metaKey || event.target !== target ||
        !host.hidden || document.activeElement !== target) return;
    const global = target.browsingContext.currentWindowGlobal;
    try {
      const allowed = await global.getActor('FocusCommandLine').sendQuery('CanOpen');
      if (allowed && global === target.browsingContext.currentWindowGlobal &&
          target === gBrowser.selectedBrowser && document.activeElement === target &&
          document.hasFocus()) open();
    } catch { /* A closing/navigating tab must retain its normal behavior. */ }
  };
  const onBlur = () => close(false);
  const onOutside = event => { if (!host.hidden && !host.contains(event.target)) close(false); };
  const onFocusOut = () => queueMicrotask(() => {
    if (!host.hidden && !host.contains(document.activeElement)) close(false);
  });
  input.addEventListener('input', onInput); window.addEventListener('keydown', onKey, true);
  host.addEventListener('focusout', onFocusOut);
  gBrowser.tabContainer.addEventListener('TabSelect', onTab);
  window.addEventListener('blur', onBlur);
  document.addEventListener('mousedown', onOutside, true);
  window.addEventListener('keydown', onBrowserKey, {mozSystemGroup:true});
  window.FocusCommandLine = { open, close, destroy() {
    close(); clearTimeout(timer); host.remove(); toast.remove();
    gBrowser.tabContainer.removeEventListener('TabSelect', onTab);
    window.removeEventListener('blur', onBlur); document.removeEventListener('mousedown', onOutside, true);
    window.removeEventListener('keydown', onBrowserKey, {mozSystemGroup:true});
    window.removeEventListener('keydown', onKey, true);
    delete window.FocusCommandLine;
  }};
})();
