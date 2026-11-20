// Loaded early in the browser window's module realm, before the native palette catalogue.
import { g as registry } from "chrome://noraneko/content/assets/js/gestures.js";

const commands = [
  ["Focus Mode - Toggle Custom Mode", "toggle"],
  ["Focus Mode - Toggle Address Bar", "toggleAddress"],
  ["Focus Mode - Toggle Tabs Bar", "toggleTabs"],
  ["Focus Mode - Show Address Bar Temporarily", "reveal"],
  ["Focus Mode - Restore Normal Browser", "normal"],
];
if (!registry?.registerAction || !registry?.getAllActions) {
  throw new Error("Custom Focus Mode: Floorp's palette registry API changed; mode not activated.");
}
for (const [name, method] of commands) {
  registry.registerAction({ name, fn: win => win.FocusMode?.[method]() });
}
window.__focusModePaletteRegistered = commands.map(([name]) => name);
window.dispatchEvent(new Event("custom-focus-palette-ready"));
