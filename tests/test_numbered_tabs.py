"""Trusted Ctrl+number tab selection in a fresh isolated browser."""
import json,os,subprocess,tempfile,time
from pathlib import Path
from browser_fixture import prepare
from marionette_client import Marionette
ROOT=Path(__file__).parent
profile=Path(tempfile.mkdtemp(prefix='floorp-numbered-tabs-'))
(profile/'user.js').write_text('user_pref("marionette.port",2896);\nuser_pref("browser.aboutwelcome.enabled",false);\nuser_pref("floorp.browser.welcome.page.shown",true);\nuser_pref("browser.shell.checkDefaultBrowser",false);\n')
log=(profile/'browser.log').open('w')
process=subprocess.Popen([prepare(profile),'--headless','--no-remote','--profile',str(profile),'--marionette','about:blank'],env={**os.environ,'MOZ_HEADLESS':'1','MOZ_REMOTE_ALLOW_SYSTEM_ACCESS':'1'},stdout=log,stderr=log)
checks=[]
try:
 for _ in range(100):
  try:m=Marionette(2896);break
  except ConnectionRefusedError:time.sleep(.15)
 else:raise RuntimeError('Browser did not start')
 def js(s):
  r=m.js(s);return r.get('value',r) if isinstance(r,dict) else r
 def check(name,value):
  if not value:print('DIAGNOSTIC',js('return {index:[...gBrowser.tabs].indexOf(gBrowser.selectedTab),key:document.getElementById("key_selectTab1").getAttribute("modifiers"),focus:document.activeElement?.localName};'),flush=True)
  assert value,name
  checks.append(name);print('PASS',name,flush=True)
 def chord(number,modifier='\ue009'):
  m.cmd('WebDriver:PerformActions',{'actions':[{'type':'key','id':'numbered-tabs','actions':[{'type':'keyDown','value':modifier},{'type':'keyDown','value':str(number)},{'type':'keyUp','value':str(number)},{'type':'keyUp','value':modifier}]}]});time.sleep(.15)
 time.sleep(1)
 check('customization initialized',js('return FocusMode.state.ready;'))
 js('window.__testTabs=Array.from({length:11},()=>gBrowser.addTrustedTab("about:blank",{skipAnimation:true}));')
 time.sleep(.5)
 for mode in ['focus','normal']:
  js('Services.prefs.setBoolPref("sidebar.verticalTabs",false);FocusMode.'+('enable' if mode=='focus' else 'normal')+'();')
  for number in range(1,10):
   js('gBrowser.selectedTab=gBrowser.tabs[9];gBrowser.selectedBrowser.focus();')
   chord(number)
   expected=number-1 if number<9 else js('return gBrowser.tabs.length-1;')
   check(mode+': Ctrl+'+str(number)+' selects '+('last tab' if number==9 else 'position '+str(number)),js('return gBrowser.selectedTab===gBrowser.tabs['+str(expected)+'];'))
 # Horizontal/vertical modes share the same native commands.
 js('Services.prefs.setBoolPref("sidebar.verticalTabs",true);FocusMode.enable();gBrowser.selectedTab=gBrowser.tabs[9];gBrowser.selectedBrowser.focus();');time.sleep(.4)
 chord(2);check('vertical tabs support Ctrl+2',js('return gBrowser.selectedTab===gBrowser.tabs[1];'))
 # Browser-field focus must retain the native accelerator too.
 js('gURLBar.focus();');chord(3);check('Ctrl+3 works from address field',js('return gBrowser.selectedTab===gBrowser.tabs[2];'))
 js('gBrowser.selectedBrowser.focus();');chord(1,'\ue00a')
 check('old Alt+1 binding is replaced',js('return gBrowser.selectedTab===gBrowser.tabs[2];'))
 js('FocusMode.setAddressPinned(false);FocusMode.setTabsVisible(false);gURLBar.blur();gBrowser.selectedBrowser.focus();');time.sleep(.2);js('FocusMode.setAddressPinned(false);');chord(4)
 check('numbered tab selection reveals only tab context',js('return document.documentElement.hasAttribute("focus-tabs-visible") && !document.documentElement.hasAttribute("focus-address-visible");'))
 js('FocusMode.destroy();')
 check('destroy restores native Linux Alt modifier',js('return [...Array.from({length:8},(_,i)=>document.getElementById("key_selectTab"+(i+1))),document.getElementById("key_selectLastTab")].every(key=>key.getAttribute("modifiers")==="alt");'))
 (ROOT/'numbered-tabs-results.json').write_text(json.dumps({'passed':len(checks),'checks':checks},indent=2))
 print('Completed',len(checks),'numbered-tab shortcut checks.')
finally:
 process.terminate()
 try:process.wait(timeout=10)
 except subprocess.TimeoutExpired:process.kill()
