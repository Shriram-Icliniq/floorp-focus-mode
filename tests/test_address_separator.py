"""Inspect and verify address-bar separator ownership in an isolated Floorp."""
import os,sys,time,json,tempfile,pathlib,subprocess,base64
from marionette_client import Marionette
from browser_fixture import prepare
ROOT=pathlib.Path(__file__).parent
profile=pathlib.Path(tempfile.mkdtemp(prefix='floorp-separator-check-'))
(profile/'custom-focus-mode.enabled').touch()
(profile/'user.js').write_text('user_pref("marionette.port",2893);\nuser_pref("browser.aboutwelcome.enabled",false);\nuser_pref("floorp.browser.welcome.page.shown",true);\nuser_pref("browser.shell.checkDefaultBrowser",false);\nuser_pref("browser.startup.homepage_override.mstone","ignore");\n')
page=profile/'white.html';page.write_text('<!doctype html><style>html,body {margin:0;background:white;height:100%;}</style><title>Separator verification</title>')
log=(profile/'browser.log').open('w')
process=subprocess.Popen([prepare(profile),'--headless','--no-remote','--profile',str(profile),'--marionette',page.as_uri()],env={**os.environ,'MOZ_HEADLESS':'1','MOZ_REMOTE_ALLOW_SYSTEM_ACCESS':'1'},stdout=log,stderr=log)
checks=[]
try:
 for _ in range(100):
  try:m=Marionette(2893);break
  except ConnectionRefusedError:time.sleep(.15)
 else:raise RuntimeError('Browser did not start')
 def js(s):
  r=m.js(s);return r.get('value',r) if isinstance(r,dict) else r
 def check(name,ok):
  assert ok,name
  checks.append(name);print('PASS',name,flush=True)
 def screenshot(name):
  r=m.cmd('WebDriver:TakeScreenshot',{'id':None,'highlights':[],'full':False});(ROOT/name).write_bytes(base64.b64decode(r.get('value',r)))
 time.sleep(1)
 js('FocusMode.normal();Services.prefs.setBoolPref("sidebar.verticalTabs",false);FocusMode.setAddressPinned(false);FocusMode.setTabsVisible(false);FocusMode.enable();gURLBar.blur();gBrowser.selectedBrowser.focus();')
 time.sleep(2.4)
 stats=js('''return [document.getElementById('navigator-toolbox'),document.getElementById('nav-bar'),gBrowser.selectedBrowser.closest('.browserContainer')].map(e=>{const s=getComputedStyle(e),r=e.getBoundingClientRect();return {id:e.id,classes:e.className,top:r.top,bottom:r.bottom,height:r.height,borderTop:s.borderTop,borderBottom:s.borderBottom,outline:s.outline,shadow:s.boxShadow};});''')
 print('GEOMETRY',json.dumps(stats),flush=True)
 if '--inspect' in sys.argv:
  screenshot('address-separator-before.png');sys.exit(0)
 # Each visible line must be owned by the transformed/transparent navbar.
 for vertical in [False,True]:
  js('Services.prefs.setBoolPref("sidebar.verticalTabs",'+str(vertical).lower()+');');time.sleep(.3)
  for tabs in [False,True]:
   js('FocusMode.setTabsVisible('+str(tabs).lower()+');FocusMode.setAddressPinned(false);gURLBar.blur();gBrowser.selectedBrowser.focus();');time.sleep(2.3)
   prefix=('vertical' if vertical else 'horizontal')+(' pinned tabs' if tabs else ' hidden tabs')
   check(prefix+': no fixed toolbox separator',js('return parseFloat(getComputedStyle(document.getElementById("navigator-toolbox")).borderBottomWidth)===0;'))
   check(prefix+': no content top border or outline',js('const s=getComputedStyle(gBrowser.selectedBrowser.closest(".browserContainer"));return parseFloat(s.borderTopWidth)===0 && s.outlineStyle==="none" && s.boxShadow==="none";'))
   check(prefix+': navbar and separator hidden together',js('return !document.documentElement.hasAttribute("focus-address-visible") && getComputedStyle(document.getElementById("nav-bar")).opacity==="0" && getComputedStyle(document.getElementById("nav-bar"),"::after").content!=="none";'))
   if not vertical and not tabs:screenshot('address-separator-hidden.png')
   baseline=js('return gBrowser.selectedBrowser.getBoundingClientRect().top;')
   js('FocusMode.reveal("separator test");');time.sleep(.2)
   check(prefix+': temporary bar owns visible separator',js('const e=document.getElementById("nav-bar"),s=getComputedStyle(e,"::after");return getComputedStyle(e).opacity==="1" && s.position==="absolute" && parseFloat(s.height)>0;'))
   check(prefix+': temporary reveal preserves page position',js('return gBrowser.selectedBrowser.getBoundingClientRect().top;')==baseline)
   if not vertical and not tabs:screenshot('address-separator-visible.png')
   js('FocusMode.setAddressPinned(true);');time.sleep(.2)
   check(prefix+': pinned bar reserves space including its separator',js('return gBrowser.selectedBrowser.getBoundingClientRect().top>=document.getElementById("nav-bar").getBoundingClientRect().bottom-1;'))
   js('FocusMode.setAddressPinned(false);');time.sleep(.2)
   check(prefix+': hide command removes whole unit',js('return getComputedStyle(document.getElementById("nav-bar")).opacity==="0" && parseFloat(getComputedStyle(document.getElementById("navigator-toolbox")).borderBottomWidth)===0;'))
 js('Services.prefs.setBoolPref("sidebar.verticalTabs",false);FocusMode.normal();');time.sleep(.2)
 check('normal mode restores native separator styling',js('return getComputedStyle(document.getElementById("nav-bar"),"::after").content==="none" && parseFloat(getComputedStyle(document.getElementById("navigator-toolbox")).borderBottomWidth)>0;'))
 js('window.__floorpZenModeController.setEnabledFromUser(true);');time.sleep(.2)
 check('native Zen mode does not use custom separator',js('return !document.documentElement.hasAttribute("focus-mode") && getComputedStyle(document.getElementById("nav-bar"),"::after").content==="none";'))
 (ROOT/'address-separator-results.json').write_text(json.dumps({'passed':len(checks),'checks':checks,'geometry':stats},indent=2))
 print('Completed',len(checks),'separator checks.')
finally:
 process.terminate()
 try:process.wait(timeout=10)
 except subprocess.TimeoutExpired:process.kill()
