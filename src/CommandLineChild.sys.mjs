/* Runs in each content frame; never reads or transmits page text. */
export class FocusCommandLineChild extends JSWindowActorChild {
  hasVisibleModal() {
    const doc = this.document;
    // Consent managers can leave aria-modal=true on a hidden, full-screen
    // dialog. Its mere presence must not disable the browsing shortcut.
    return [...doc.querySelectorAll('dialog:modal, [aria-modal="true"]')].some(modal => {
      if (modal.closest('[hidden], [aria-hidden="true"]') ||
          !modal.checkVisibility({checkOpacity:true, checkVisibilityCSS:true})) return false;
      const rect = modal.getBoundingClientRect();
      return rect.width > 0 && rect.height > 0 && rect.bottom > 0 && rect.right > 0 &&
        rect.top < this.contentWindow.innerHeight && rect.left < this.contentWindow.innerWidth;
    });
  }

  receiveMessage(message) {
    if (message.name !== 'CanOpen') return false;
    // A nested browser/frame owns its own keyboard handling.
    return !this.document.activeElement?.matches('iframe, frame, browser') &&
      this.canOpen();
  }

  canOpen(path = [], allowEditing = false) {
    const doc = this.document;
    // Check focus before reserving the key. Capture priority prevents a page
    // from auto-focusing its composer while browsing, but must not take keys
    // from a composer the user is already typing in.
    const nodes = [...path];
    const visited = new Set();
    let active = doc.activeElement;
    while (active && !visited.has(active)) {
      visited.add(active);
      nodes.push(active);
      active = active.openOrClosedShadowRoot?.activeElement || active.parentElement ||
        active.getRootNode()?.host;
    }
    const editing = doc.designMode === 'on' || nodes.some(node => node.nodeType === 1 && (
      node.isContentEditable || node.matches(
        'input, textarea, select, object, embed, [role="textbox"], [role="searchbox"], ' +
        '[role="combobox"], [role="spinbutton"], [role="slider"], [role="grid"], ' +
        '.monaco-editor, .cm-editor, .CodeMirror, [data-slate-editor], [data-lexical-editor]'
      )));
    return (!editing || allowEditing) && !doc.fullscreenElement && !doc.pointerLockElement &&
      !this.hasVisibleModal();
  }

  handleEvent(event) {
    if (!this.browsingContext.top.isContent || !event.isTrusted) return;
    const colon = event.key === ':' && !event.ctrlKey && !event.altKey && !event.metaKey;
    const internalShortcut = this.document.documentURI.startsWith('about:') &&
      event.code === 'Period' && event.ctrlKey && event.shiftKey &&
      !event.altKey && !event.metaKey;
    if ((!colon && !internalShortcut) || event.isComposing || event.keyCode === 229 ||
        !this.canOpen(event.composedPath(), internalShortcut)) return;
    // Reserve the key before page listeners can redirect it into an editor.
    event.preventDefault();
    event.stopImmediatePropagation();
    if (!event.repeat) this.sendAsyncMessage('Open');
  }
}
