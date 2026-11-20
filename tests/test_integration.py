"""Real Floorp browser-chrome integration checks against an isolated test profile."""
import sys,time,json,pathlib,base64
from marionette_client import Marionette
import http.server,threading
class Page(http.server.BaseHTTPRequestHandler):
 def do_GET(self):
  self.send_response(200);self.send_header('Content-Type','text/html');self.end_headers();self.wfile.write(b'<!doctype html><title>Focus Mode verification</title><h1>Custom Focus Mode</h1><p>Local navigation and reload test.</p>')
 def log_message(self,*args):pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Page)
threading.Thread(target=server.serve_forever,daemon=True).start()
url='http://127.0.0.1:'+str(server.server_port)+'/'
m=Marionette(int(sys.argv[1]) if len(sys.argv)>1 else 2878)
results=[]
def js(s):
 r=m.js(s)
 return r.get('value',r) if isinstance(r,dict) else r
def check(name,condition):
 assert condition,name
 results.append(name);print('PASS',name,flush=True)
def wait(seconds=.16):time.sleep(seconds)
js("window.dispatchEvent(new Event('floorp-command-palette-toggle'));")
wait()
# Always start with palette closed.
if js("return !!document.getElementById('command-palette-overlay');"):
 js("window.dispatchEvent(new Event('floorp-command-palette-toggle'));")
wait()
# Check the actual native palette's displayed catalogue and dispatch an item.
js("window.dispatchEvent(new Event('floorp-command-palette-toggle'));")
wait()
js("const i=document.getElementById('command-palette-search');i.value='Focus Mode';i.dispatchEvent(new Event('input',{bubbles:true}));")
wait(.25)
labels=js("return Array.from(document.querySelectorAll('.command-palette-item')).map(e=>e.textContent.trim());")
expected=['Focus Mode - Toggle Custom Mode','Focus Mode - Toggle Address Bar','Focus Mode - Toggle Tabs Bar','Focus Mode - Show Address Bar Temporarily','Focus Mode - Restore Normal Browser']
check('all five native palette commands are searchable',all(x in labels for x in expected))
js("Array.from(document.querySelectorAll('.command-palette-item')).find(e=>e.textContent.trim()==='Focus Mode - Restore Normal Browser').click();")
check('native palette command executes normal mode',js("return !FocusMode.state.enabled && !document.documentElement.hasAttribute('focus-mode');"))
js("FocusMode.state.addressPinned=false;FocusMode.state.tabsVisible=false;FocusMode.enable();gURLBar.blur();gBrowser.selectedBrowser.focus();")
wait(2.25)
check('custom mode starts with both bars hidden',js("return getComputedStyle(document.getElementById('TabsToolbar')).display==='none' && getComputedStyle(document.getElementById('nav-bar')).opacity==='0';"))
# Hover cannot reveal either bar.
js("document.getElementById('navigator-toolbox').dispatchEvent(new MouseEvent('mouseover',{bubbles:true,clientY:1}));window.dispatchEvent(new MouseEvent('mousemove',{clientY:1}));")
wait()
check('top-edge mouse activity does not reveal address bar',js("return !document.documentElement.hasAttribute('focus-address-visible');"))
js("gURLBar.focus();")
wait()
check('address-bar focus reveals it',js("return document.documentElement.hasAttribute('focus-address-visible');"))
wait(2.15)
check('typing focus holds it open beyond two seconds',js("return document.documentElement.hasAttribute('focus-address-visible');"))
js("gURLBar.blur();gBrowser.selectedBrowser.focus();")
wait(.45)
check('bar remains visible during grace period',js("return document.documentElement.hasAttribute('focus-address-visible');"))
wait(1.85)
check('bar hides after two-second grace period',js("return !document.documentElement.hasAttribute('focus-address-visible');"))
js("FocusMode.toggleAddress();")
wait(2.25)
check('explicitly pinned address bar stays visible',js("return FocusMode.state.addressPinned && document.documentElement.hasAttribute('focus-address-visible');"))
check('pinned horizontal bar reserves content space',js("return gBrowser.selectedBrowser.getBoundingClientRect().top>=document.getElementById('nav-bar').getBoundingClientRect().bottom-1;"))
js("FocusMode.toggleTabs();")
check('tabs toggle does not change pinned address bar',js("return FocusMode.state.addressPinned && getComputedStyle(document.getElementById('TabsToolbar')).display!=='none';"))
js("FocusMode.toggleAddress();")
wait(.2)
check('address toggle does not hide horizontal tabs',js("return !FocusMode.state.addressPinned && FocusMode.state.tabsVisible && getComputedStyle(document.getElementById('nav-bar')).opacity==='0';"))
js("FocusMode.toggleTabs();window.__focusTestTab=gBrowser.addTrustedTab('about:blank',{skipAnimation:true});")
wait(.15)
check('opening a tab reveals address bar',js("return FocusMode.state.lastActivity==='TabOpen' && document.documentElement.hasAttribute('focus-address-visible');"))
wait(2.3)
js("gBrowser.selectedTab=window.__focusTestTab;")
wait(.15)
check('switching tabs reveals address bar',js("return document.documentElement.hasAttribute('focus-address-visible');"))
js("gBrowser.removeTab(window.__focusTestTab,{animate:false});")
wait(.15)
check('closing a tab reveals address bar',js("return document.documentElement.hasAttribute('focus-address-visible');"))
# Real navigation and reload against a local HTTP server.
js("FocusMode.state.lastActivity=null;gBrowser.selectedBrowser.loadURI(Services.io.newURI('"+url+"'),{triggeringPrincipal:Services.scriptSecurityManager.getSystemPrincipal()});")
wait(.6)
check('navigation/page load reveals address bar',js("return ['navigation','page load/reload'].includes(FocusMode.state.lastActivity) && document.documentElement.hasAttribute('focus-address-visible');"))
js("FocusMode.state.lastActivity=null;gBrowser.selectedBrowser.reload();")
wait(.5)
check('actual reload reveals address bar',js("return FocusMode.state.lastActivity==='page load/reload' && document.documentElement.hasAttribute('focus-address-visible');"))
check('actual reload also reveals temporary tabs',js("return FocusMode.state.lastTabActivity==='page load/reload' && document.documentElement.hasAttribute('focus-tabs-overlay');"))
js("Services.prefs.setBoolPref('sidebar.verticalTabs',true);")
wait(2.4)
check('native vertical layout is detected',js("return gBrowser.tabContainer.verticalMode && document.documentElement.hasAttribute('focus-vertical');"))
check('vertical tab rail is hidden in custom mode',js("const e=document.querySelector('sidebar-main');return e && e.getBoundingClientRect().width===0;"))
js("FocusMode.toggleTabs();")
wait(.3)
check('same tabs command shows vertical tab rail',js("const e=document.querySelector('sidebar-main');return e && e.getBoundingClientRect().width>0;"))
js("FocusMode.toggleAddress();")
wait(.2)
check('pinned vertical-layout bar reserves content space',js("return gBrowser.selectedBrowser.getBoundingClientRect().top>=document.getElementById('nav-bar').getBoundingClientRect().bottom-1;"))
js("FocusMode.toggleAddress();")
js("FocusMode.toggleTabs();")
wait(.15)
check('same tabs command hides vertical tab rail',js("return document.querySelector('sidebar-main').getBoundingClientRect().width===0;"))
js("FocusMode.normal();")
wait(.15)
check('normal mode restores vertical tabs and native navbar',js("return document.querySelector('sidebar-main').getBoundingClientRect().width>0 && getComputedStyle(document.getElementById('nav-bar')).position!=='absolute';"))
js("Services.prefs.setBoolPref('sidebar.verticalTabs',false);FocusMode.enable();")
wait(.5)
js("window.__floorpZenModeController.setEnabledFromUser(true);")
wait(.15)
check('native Zen Mode takes over without custom-mode CSS',js("return document.documentElement.hasAttribute('zenmode') && !document.documentElement.hasAttribute('focus-mode');"))
js("window.__floorpZenModeController.setEnabledFromUser(false);FocusMode.enable();")
# Trusted native keyboard command: no synthetic page-key bridge.
m.cmd('WebDriver:PerformActions',{'actions':[{'type':'key','id':'keys','actions':[{'type':'keyDown','value':'\ue009'},{'type':'keyDown','value':'\ue008'},{'type':'keyDown','value':'p'},{'type':'keyUp','value':'p'},{'type':'keyUp','value':'\ue008'},{'type':'keyUp','value':'\ue009'}]}]})
wait(.3)
check('Ctrl+Shift+P opens native palette',js("return !!document.getElementById('command-palette-overlay');"))
check('shortcut did not create a private window',js("return Array.from(Services.wm.getEnumerator('navigator:browser')).length===1;"))
# Screenshot of actual custom commands for visual QA.
js("const i=document.getElementById('command-palette-search');i.value='Focus Mode';i.dispatchEvent(new Event('input',{bubbles:true}));")
wait(.2)
r=m.cmd('WebDriver:TakeScreenshot',{'id':None,'highlights':[],'full':False});data=r.get('value',r) if isinstance(r,dict) else r
folder=pathlib.Path(__file__).parent
(folder/'palette-preview.png').write_bytes(base64.b64decode(data))
(folder/'test-results.json').write_text(json.dumps({'passed':len(results),'checks':results},indent=2))
server.shutdown()
print('Completed',len(results),'integration checks.')
