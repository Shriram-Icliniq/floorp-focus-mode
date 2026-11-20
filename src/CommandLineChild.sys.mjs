/* Runs in each content frame; never reads or transmits page text. */
export class FocusCommandLineChild extends JSWindowActorChild {
  receiveMessage(message) {
    if (message.name !== 'CanOpen') return false;
    // A nested browser/frame owns its own keyboard handling.
    return !this.document.activeElement?.matches('iframe, frame, browser') &&
      this.canOpen();
  }

  canOpen() {
    const doc = this.document;
    return !doc.fullscreenElement && !doc.pointerLockElement &&
      !doc.querySelector('dialog[open], [aria-modal="true"]');
  }

  handleEvent(event) {
    if (!this.browsingContext.top.isContent || !event.isTrusted) return;
    const colon = event.key === ':' && !event.ctrlKey && !event.altKey && !event.metaKey;
    const internalShortcut = this.document.documentURI.startsWith('about:') &&
      event.code === 'Period' && event.ctrlKey && event.shiftKey &&
      !event.altKey && !event.metaKey;
    if ((!colon && !internalShortcut) || event.isComposing || event.keyCode === 229 ||
        !this.canOpen()) return;
    // Reserve the key before page listeners can redirect it into an editor.
    event.preventDefault();
    event.stopImmediatePropagation();
    if (!event.repeat) this.sendAsyncMessage('Open');
  }
}
