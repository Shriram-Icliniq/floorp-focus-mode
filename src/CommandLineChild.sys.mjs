/* Runs in each content frame; never reads or transmits page text. */
export class FocusCommandLineChild extends JSWindowActorChild {
  receiveMessage(message) {
    if (message.name !== 'CanOpen') return false;
    const doc = this.document;
    const path = [];
    let active = doc.activeElement;
    // A nested browser/frame owns its own focus checks and keyboard actor.
    if (active?.matches('iframe, frame, browser')) return false;
    while (active) {
      path.push(active);
      active = active.openOrClosedShadowRoot?.activeElement || active.parentElement;
    }
    return !this.isEditing(path) && !this.passThrough && !doc.fullscreenElement &&
      !doc.pointerLockElement && !doc.querySelector('dialog[open], [aria-modal="true"]');
  }
  isEditing(path) {
    return this.document.designMode === 'on' || path.some(node => node.nodeType === 1 && (
      node.isContentEditable || node.matches(
        'input, textarea, select, object, embed, [role="textbox"], [role="searchbox"], ' +
        '[role="combobox"], [role="spinbutton"], [role="slider"], [role="grid"], ' +
        '.monaco-editor, .cm-editor, .CodeMirror, [data-slate-editor], [data-lexical-editor]'
      )));
  }
  handleEvent(event) {
    if (!this.browsingContext.top.isContent) return;
    if (!event.isTrusted) return;
    if (event.key === "Escape") this.passThrough = false;
    const path = event.composedPath();
    const doc = this.document;
    // Closed shadow trees retarget composedPath at their host. Privileged
    // focus traversal still lets their inputs retain the keystroke.
    let active = doc.activeElement;
    while (active) {
      path.push(active);
      active = active.openOrClosedShadowRoot?.activeElement;
    }
    // composedPath sees focused nodes in shadow trees. A focused iframe is
    // handled by its own actor; uncertain/plugin contexts keep their keys.
    const editing = this.isEditing(path);
    // Vimium's explicit insert command consumes i even without an editable
    // element. Conservatively keep pass-through until Escape in that frame.
    if (!editing && event.defaultPrevented && event.key === "i" &&
        !event.ctrlKey && !event.altKey && !event.metaKey) this.passThrough = true;
    if (event.key !== ":" || event.defaultPrevented || event.isComposing ||
        event.keyCode === 229 || event.repeat || event.ctrlKey || event.altKey ||
        event.metaKey || editing || this.passThrough || doc.fullscreenElement ||
        doc.pointerLockElement || doc.querySelector('dialog[open], [aria-modal="true"]')) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    this.sendAsyncMessage("Open");
  }
}
