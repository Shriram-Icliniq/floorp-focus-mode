"""Real-browser site/tab reveals: full documents, SPA, redirects, history and restore."""
import http.server,json,os,subprocess,tempfile,threading,time
from pathlib import Path
from browser_fixture import prepare
from marionette_client import Marionette
ROOT=Path(__file__).parent
class Page(http.server.BaseHTTPRequestHandler):
 reload_seen=False
 def do_GET(self):
  path=self.path.split('?')[0]
  if path.startswith('/reload-flip'):
   if Page.reload_seen:
    self.send_response(302);self.send_header('Location','http://alpha.example.com:'+str(self.server.server_port)+'/reload-destination');self.end_headers();return
   Page.reload_seen=True
  if path.startswith('/redirect/'):
   time.sleep(.25);step=int(path.rsplit('/',1)[1]);self.send_response(302)
   host,path=('beta.example.org','/redirect/1') if step==0 else ('gamma.example.net','/slow-final')
   self.send_header('Location','http://'+host+':'+str(self.server.server_port)+path);self.end_headers();return
  if path.startswith('/internal-redirect'):
   self.send_response(302);self.send_header('Location','/page-final');self.end_headers();return
  if path.startswith('/slow'):time.sleep(.9)
  self.send_response(200);self.send_header('Content-Type','text/html');self.send_header('Cache-Control','no-store');self.end_headers()
  try:self.wfile.write(b'<!doctype html><title>Navigation fixture</title><p>Local document</p>')
  except (BrokenPipeError,ConnectionResetError):pass
 def log_message(self,*args):pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Page)
threading.Thread(target=server.serve_forever,daemon=True).start()
def url(host='alpha.example.com',path='/page'):return 'http://'+host+':'+str(server.server_port)+path
profile=Path(tempfile.mkdtemp(prefix='floorp-navigation-check-'))
(profile/'user.js').write_text('''user_pref("marionette.port",2894);
user_pref("browser.aboutwelcome.enabled",false);
user_pref("floorp.browser.welcome.page.shown",true);
user_pref("browser.shell.checkDefaultBrowser",false);
user_pref("browser.startup.homepage_override.mstone","ignore");
user_pref("network.proxy.type",0);
user_pref("network.dns.localDomains","alpha.example.com,account.example.com,beta.example.org,gamma.example.net");
''')
log=(profile/'browser.log').open('w')
process=subprocess.Popen([prepare(profile),'--headless','--no-remote','--profile',str(profile),'--marionette',url()],env={**os.environ,'MOZ_HEADLESS':'1','MOZ_REMOTE_ALLOW_SYSTEM_ACCESS':'1'},stdout=log,stderr=log)
checks=[]
try:
 for _ in range(100):
  try:m=Marionette(2894);break
  except ConnectionRefusedError:time.sleep(.15)
 else:raise RuntimeError('Browser did not start')
 def js(script):
  result=m.js(script);return result.get('value',result) if isinstance(result,dict) else result
 def context(name):m.cmd('Marionette:SetContext',{'value':name})
 def check(name,value):
  if not value:
   context('chrome');print('DIAGNOSTIC',js('return {url:gBrowser.selectedBrowser.currentURI.spec,events:window.__reveals,hold:FocusMode.state.hold};'),flush=True)
  assert value,name
  checks.append(name);print('PASS',name,flush=True)
 def hidden():
  context('chrome');return js('return !document.documentElement.hasAttribute("focus-address-visible") && !document.documentElement.hasAttribute("focus-tabs-visible");')
 def quiet(label):
  context('chrome');check(label+' reveals neither bar',hidden() and js('return __reveals.length===0;'))
 def address_only(label):
  context('chrome');check(label+' reveals only address bar',js('return document.documentElement.hasAttribute("focus-address-visible") && !document.documentElement.hasAttribute("focus-tabs-visible") && __reveals.filter(e=>e.bar==="address").length===1 && !__reveals.some(e=>e.bar==="tabs");'))
 def tabs_only(label):
  context('chrome');check(label+' reveals only tabs',js('return document.documentElement.hasAttribute("focus-tabs-visible") && !document.documentElement.hasAttribute("focus-address-visible") && __reveals.some(e=>e.bar==="tabs") && !__reveals.some(e=>e.bar==="address");'))
 def navigate(destination):
  context('chrome');js('gBrowser.selectedBrowser.loadURI(Services.io.newURI('+json.dumps(destination)+'),{triggeringPrincipal:Services.scriptSecurityManager.getSystemPrincipal()});')
 def settled():
  context('chrome');time.sleep(.1)
  for _ in range(140):
   if not js('return gBrowser.selectedBrowser.webProgress.isLoadingDocument;'):time.sleep(.1);return
   time.sleep(.05)
  raise AssertionError('Navigation did not finish')
 def hide():
  context('chrome');js('gURLBar.blur();gBrowser.selectedBrowser.focus();');time.sleep(.15)
  js('FocusMode.setAddressPinned(false);FocusMode.setTabsVisible(false);window.__reveals=[];')
 time.sleep(1);settled()
 m.cmd('WebDriver:PerformActions',{'actions':[{'type':'pointer','id':'mouse','parameters':{'pointerType':'mouse'},'actions':[{'type':'pointerMove','origin':'viewport','x':900,'y':400,'duration':0}]}]})
 js('Services.prefs.setBoolPref("sidebar.verticalTabs",'+str(os.environ.get('FLOORP_TEST_VERTICAL')=='1').lower()+');');time.sleep(.3)
 js('Services.prefs.setIntPref("user.focusMode.revealMs",500);FocusMode.normal();FocusMode.setTabsVisible(false);FocusMode.setAddressPinned(false);FocusMode.enable();')
 # Count even brief reveals, not just visibility when the assertion runs.
 js('window.__reveals=[];for(const [key,bar] of [["lastActivity","address"],["lastTabActivity","tabs"]]){let value=FocusMode.state[key];Object.defineProperty(FocusMode.state,key,{get:()=>value,set:v=>{value=v;__reveals.push({bar,reason:v});},configurable:true});}')
 hide();check('starts with both bars hidden',hidden())
 check('fixture uses intended site',js('return gBrowser.selectedBrowser.currentURI.host==="alpha.example.com";'))
 for label,script in [('hash navigation','location.hash="section";'),('SPA pushState','history.pushState({},"","?filter=one#section");'),('SPA replaceState','history.replaceState({},"","/route?filter=two");'),('same-document Back','history.back();'),('same-document Forward','history.forward();')]:
  hide();context('content');js(script);time.sleep(.2);quiet(label)
 hide();context('content');js('void fetch("/slow-api");');time.sleep(.2);quiet('fetch start');time.sleep(1);quiet('fetch completion')
 hide();navigate(url(path='/slow'));time.sleep(.2);quiet('same-site document start');settled();quiet('same-site document completion')
 hide();js('gBrowser.selectedBrowser.reload();');time.sleep(.2);quiet('reload start');settled();quiet('reload completion')
 hide();navigate(url(path='/internal-redirect'));settled();quiet('same-site redirects')
 hide();navigate(url('account.example.com'));settled();quiet('cross-origin subdomain navigation within one website')
 hide();navigate(url('beta.example.org','/slow'));time.sleep(.2);quiet('uncommitted cross-site request');settled();address_only('committed cross-site navigation')
 time.sleep(.65);check('site peek expires',hidden())
 hide();js('gBrowser.goBack();');settled();quiet('cross-site Back')
 check('Back reaches prior site',js('return gBrowser.selectedBrowser.currentURI.host==="account.example.com";'))
 hide();js('gBrowser.goForward();');settled();quiet('cross-site Forward')
 hide();navigate(url('account.example.com'));settled();address_only('normal cross-site visit after history')
 hide();navigate(url('alpha.example.com','/redirect/0'));time.sleep(.7);quiet('cross-site redirect hops before commit');settled();address_only('final redirect site')
 check('redirect reaches final website',js('return gBrowser.selectedBrowser.currentURI.host==="gamma.example.net";'))
 time.sleep(.65);check('redirect peek expires',hidden());check('redirect chain reveals address exactly once',js('return __reveals.length===1;'))
 hide();js('gBrowser.selectedBrowser.reload();');settled();quiet('reload after redirects')
 hide();navigate(url('gamma.example.net','/reload-flip'));settled();quiet('reload fixture same-site entry')
 hide();js('gBrowser.selectedBrowser.reload();');settled();quiet('reload redirecting to another website')
 check('reload redirect reaches other website',js('return gBrowser.selectedBrowser.currentURI.host==="alpha.example.com";'))
 hide();js('window.__originalPeekTab=gBrowser.selectedTab;window.__backgroundPeekTab=gBrowser.addTrustedTab("about:blank",{skipAnimation:true});');time.sleep(.15);tabs_only('opening a tab')
 hide();js('window.__backgroundPeekTab.linkedBrowser.loadURI(Services.io.newURI('+json.dumps(url('beta.example.org','/slow-background'))+'),{triggeringPrincipal:Services.scriptSecurityManager.getSystemPrincipal()});');time.sleep(.2);quiet('background document start');time.sleep(1);quiet('background document completion')
 hide();js('gBrowser.selectedTab=window.__backgroundPeekTab;');time.sleep(.15);tabs_only('switching tabs')
 hide();navigate(url('beta.example.org','/page-two'));settled();quiet('internal navigation after background tab switch')
 hide();js('gBrowser.selectedTab=window.__originalPeekTab;');time.sleep(.15);tabs_only('returning to original tab')
 hide();js('gBrowser.removeTab(window.__backgroundPeekTab,{animate:false});');time.sleep(.2);tabs_only('closing a tab')
 # Native session-store operations, not synthetic restore events.
 hide();js('Services.prefs.setIntPref("user.focusMode.revealMs",2000);window.__duplicatePeekTab=SessionStore.duplicateTab(window,gBrowser.selectedTab,0,false);');time.sleep(1);tabs_only('duplicating a tab')
 check('duplicate tab exists',js('return !!window.__duplicatePeekTab?.isConnected;'))
 js('gBrowser.removeTab(window.__duplicatePeekTab,{animate:false});');time.sleep(.4);hide()
 js('SessionStore.undoCloseTab(window,0);');time.sleep(1);tabs_only('restoring a closed tab');js('Services.prefs.setIntPref("user.focusMode.revealMs",500);')
 hide();context('content');js('const frame=document.createElement("iframe");frame.src='+json.dumps(url('alpha.example.com','/slow-frame'))+';document.body.appendChild(frame);');time.sleep(.2);quiet('cross-site subframe start');time.sleep(1);quiet('cross-site subframe completion')
 context('chrome')
 m.cmd('WebDriver:PerformActions',{'actions':[{'type':'key','id':'url-keys','actions':[{'type':'keyDown','value':'\ue009'},{'type':'keyDown','value':'l'},{'type':'keyUp','value':'l'},{'type':'keyUp','value':'\ue009'}]}]})
 time.sleep(.7)
 check('Ctrl+L reveals address and holds beyond timeout',js('return document.documentElement.hasAttribute("focus-address-visible") && document.activeElement===gURLBar.inputField;'))
 check('Ctrl+L keeps tabs hidden',js('return !document.documentElement.hasAttribute("focus-tabs-visible");'))
 js('gURLBar.blur();gBrowser.selectedBrowser.focus();');time.sleep(.15);check('address focus grace period',js('return document.documentElement.hasAttribute("focus-address-visible");'))
 time.sleep(.5);check('address focus grace expires',hidden())
 report='navigation-peek-vertical-results.json' if os.environ.get('FLOORP_TEST_VERTICAL')=='1' else 'navigation-peek-results.json'
 (ROOT/report).write_text(json.dumps({'passed':len(checks),'checks':checks},indent=2));print('Completed',len(checks),'navigation peek checks.')
finally:
 process.terminate()
 try:process.wait(timeout=10)
 except subprocess.TimeoutExpired:process.kill()
 server.shutdown()
