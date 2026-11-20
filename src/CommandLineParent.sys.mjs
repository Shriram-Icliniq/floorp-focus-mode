export class FocusCommandLineParent extends JSWindowActorParent {
  receiveMessage(message) {
    if (message.name !== "Open") return;
    const win = this.browsingContext.topChromeWindow;
    const browser = win?.gBrowser?.selectedBrowser;
    if (!browser || !win.document.hasFocus() ||
        win.document.activeElement !== browser) return;
    // Internal tabs such as Add-ons nest a <browser> with its own top-level
    // browsing context. Follow its DOM owners back to the actual selected tab.
    let context = this.browsingContext.top;
    const visited = new Set();
    while (context && context !== browser.browsingContext) {
      if (visited.has(context)) return;
      visited.add(context);
      context = context.embedderElement?.ownerDocument?.defaultView?.browsingContext?.top;
    }
    if (context !== browser.browsingContext) return;
    win.FocusCommandLine?.open();
  }
}
