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

  canOpen() {
    // Ctrl+; is an explicit browser command, including inside editors and
    // hidden editor iframes. Punctuation no longer needs focus heuristics.
    const doc = this.document;
    return !doc.fullscreenElement && !doc.pointerLockElement && !this.hasVisibleModal();
  }

  handleEvent(event) {
    if (!this.browsingContext.top.isContent || !event.isTrusted) return;
    const commandShortcut = event.key === ';' && event.ctrlKey &&
      !event.shiftKey && !event.altKey && !event.metaKey;
    const internalShortcut = this.document.documentURI.startsWith('about:') &&
      event.code === 'Period' && event.ctrlKey && event.shiftKey &&
      !event.altKey && !event.metaKey;
    if ((!commandShortcut && !internalShortcut) || event.isComposing || event.keyCode === 229 ||
        !this.canOpen()) return;
    // Reserve the key before page listeners can redirect it into an editor.
    event.preventDefault();
    event.stopImmediatePropagation();
    if (!event.repeat) this.sendAsyncMessage('Open');
  }
}
