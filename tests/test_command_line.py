"""Disposable real-browser command-line and input-guard regression checks."""
import os,sys,time,json,tempfile,pathlib,subprocess,shutil,base64,http.server,threading,functools
from marionette_client import Marionette
from browser_fixture import prepare
ROOT=pathlib.Path(__file__).parent
profile=pathlib.Path(tempfile.mkdtemp(prefix='floorp-command-check-'))
(profile/'custom-focus-mode.enabled').touch()
(profile/'user.js').write_text('user_pref("marionette.port",2892);\nuser_pref("browser.aboutwelcome.enabled",false);\nuser_pref("browser.shell.checkDefaultBrowser",false);\nuser_pref("browser.startup.homepage_override.mstone","ignore");\nuser_pref("extensions.autoDisableScopes",0);\nuser_pref("floorp.browser.welcome.page.shown",true);\n')
vimium_xpi=os.environ.get('FLOORP_VIMIUM_XPI')
if vimium_xpi:
 (profile/'extensions').mkdir()
 shutil.copy2(vimium_xpi,profile/'extensions/vimium-c@gdh1995.cn.xpi')
page=profile/'fixture.html'
page.write_text('''<!doctype html><title>Command line verification</title><h1>Command mode</h1><button id="button">Ordinary button</button><input id="text"><input id="password" type="password"><textarea id="area"></textarea><div id="editable" contenteditable="true">Editable</div><div id="role" role="textbox" tabindex="0">Rich editor</div><select id="select"><option>A</option></select><div id="chat-composer" class="ProseMirror" contenteditable="true" role="textbox" data-testid="chat-composer"><p><br></p></div><div id="shadow"></div><iframe srcdoc="<input id='nested'><button id='plain'>Frame button</button>"></iframe><script>const host=document.getElementById('shadow'); const root=host.attachShadow({mode:'closed'});root.innerHTML='<input id="deep">';host.onclick=()=>root.querySelector('input').focus();</script>''')
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(profile)))
threading.Thread(target=server.serve_forever,daemon=True).start()
url='http://127.0.0.1:'+str(server.server_port)+'/fixture.html'
log=(profile/'browser.log').open('w')
process=subprocess.Popen([prepare(profile),'--headless','--no-remote','--profile',str(profile),'--marionette',url],env={**os.environ,'MOZ_HEADLESS':'1','MOZ_REMOTE_ALLOW_SYSTEM_ACCESS':'1'},stdout=log,stderr=log)
checks=[]
def check(name,value):
 if not value:
  context('chrome');print('DIAGNOSTIC',js('return {focused:document.hasFocus(),active:document.activeElement?.localName,popups:[...document.querySelectorAll(\'#mainPopupSet panel[panelopen="true"], #mainPopupSet menupopup[open="true"]\')].map(e=>e.id),lastKey:window.__tabLastKey};'),flush=True)
  r=m.cmd('WebDriver:TakeScreenshot',{'id':None,'highlights':[],'full':False});(ROOT/'command-line-failure.png').write_bytes(base64.b64decode(r.get('value',r)))
 assert value,name
 checks.append(name);print('PASS',name,flush=True)
try:
 for _ in range(100):
  try:m=Marionette(2892);break
  except ConnectionRefusedError:time.sleep(.15)
 else:raise RuntimeError('Browser did not start: '+(profile/'browser.log').read_text())
 def context(c):m.cmd('Marionette:SetContext',{'value':c})
 def js(s):
  r=m.js(s);return r.get('value',r) if isinstance(r,dict) else r
 def keys(text):
  m.cmd('WebDriver:PerformActions',{'actions':[{'type':'key','id':'command-keys','actions':[a for c in text for a in [{'type':'keyDown','value':c},{'type':'keyUp','value':c}]]}]})
  time.sleep(.12)
 def opened():
  context('chrome');return js("return !!window.FocusCommandLine && !document.getElementById('focus-command-line').hidden;")
 def pagefocus(selector='body'):
  context('content');js("document.querySelector("+json.dumps(selector)+").focus();")
 def openline():
  context('chrome');js('gBrowser.selectedBrowser.focus();')
  context('content');js('document.activeElement.blur();');keys(':')
  check('colon opens from browsing context',opened())
 def command(text):
  context('chrome');js('FocusCommandLine.open(); const i=document.getElementById("focus-command-input");i.value='+json.dumps(text)+';i.dispatchEvent(new Event("input"));');keys('\ue007')
 if '--tabs-only' not in sys.argv:
  time.sleep(2)
  context('chrome');check('custom command UI loaded',js('return !!FocusCommandLine && FocusMode.state.ready;'))
  # Wait for fixture navigation and extension startup.
  context('content');m.cmd('WebDriver:Navigate',{'url':url});time.sleep(1)
  openline()
  context('chrome');check('all eleven commands offered',js("return document.querySelectorAll('.focus-command-option').length===11;"))
  check('command UI overlays without resizing content',js("return getComputedStyle(document.getElementById('focus-command-line')).position==='fixed';"))
  keys('focus');keys('\ue015');keys('\ue007');check('Enter executes highlighted suggestion for incomplete input',not opened() and js('return !FocusMode.state.enabled;'))
  openline();context('chrome');check('most recent command is the default suggestion',js('return document.querySelector(\'.focus-command-option[aria-selected="true"] strong\').textContent==="focus off";'))
  keys('focus');keys('\ue004');context('chrome');check('Tab completes highlighted suggestion',js('return document.getElementById("focus-command-input").value==="focus off";'))
  keys('\ue004');context('chrome');check('Tab cycles original matching suggestions',js('return document.getElementById("focus-command-input").value==="focus on";'))
  keys('\ue00c');check('Escape closes command line',not opened())
  context('chrome');check('Escape restores page focus',js('return document.activeElement===gBrowser.selectedBrowser;'))
  for text,assertion in [
   ('focus off','!FocusMode.state.enabled'),('tabs hide','FocusMode.state.enabled && !FocusMode.state.tabsVisible && FocusMode.state.addressPinned'),
   ('tabs show','FocusMode.state.tabsVisible'),('address hide','!FocusMode.state.addressPinned && FocusMode.state.tabsVisible'),
   ('address show','FocusMode.state.addressPinned'),('address toggle','!FocusMode.state.addressPinned'),
   ('tabs toggle','!FocusMode.state.tabsVisible'),('address peek','FocusMode.state.temporary && !FocusMode.state.addressPinned'),
   ('tabs peek','FocusMode.state.tabsTemporary && !FocusMode.state.tabsVisible'),
   ('focus toggle','!FocusMode.state.enabled'),('focus on','FocusMode.state.enabled')]:
   command(text);check(text+' executes',js('return '+assertion+';'));check(text+' dismisses command line',not opened())
  for prefix,assertion in [('focus of','!FocusMode.state.enabled'),('focus t','FocusMode.state.enabled'),('address s','FocusMode.state.addressPinned'),('tabs h','!FocusMode.state.tabsVisible')]:
   command(prefix);check('unique prefix '+prefix+' executes on Enter',not opened() and js('return '+assertion+';'))
  command('address');check('Enter runs default selection for multiple matches',not opened())
  command('');check('Enter repeats the most recent command on empty input',not opened())
  command('unknown');check('unknown command stays open',opened());context('chrome');keys('\ue00c')
  command('address peek');command('address hide');context('chrome');check('address hide immediately clears temporary reveal',js('return !FocusMode.state.temporary && !document.documentElement.hasAttribute("focus-address-visible");'))
  command('tabs peek');command('tabs hide');context('chrome');check('tabs hide immediately clears temporary reveal',js('return !FocusMode.state.tabsTemporary && !document.documentElement.hasAttribute("focus-tabs-visible");'))
  for selector in ['#text','#password','#area','#editable','#role','#select','#chat-composer']:
   context('chrome');js('gBrowser.selectedBrowser.focus();');pagefocus(selector);keys(';:')
   check('punctuation does not open command line in '+selector,not opened())
   if selector in ['#text','#password','#area','#editable','#chat-composer']:
    context('content');check('semicolon and colon reach '+selector,js('const node=document.querySelector('+json.dumps(selector)+'); return (node.value ?? node.textContent).includes(";:");'))
  context('content');js('document.querySelector("#shadow").click();');keys(':')
  check('closed shadow input retains colon',not opened())
  context('content');m.cmd('WebDriver:SwitchToFrame',{'id':0});js('document.getElementById("nested").focus();');keys(':')
  check('frame input retains colon',not opened())
  context('content');js('document.getElementById("plain").focus();');keys(':');check('frame ordinary button opens command line',opened())
  keys('\ue00c');context('content');m.cmd('WebDriver:SwitchToFrame',{'id':None})
  # Cookie managers may retain aria-modal on hidden full-screen dialogs.
  modal_cases=[
   ('hidden consent dialog', '<div id="modal-test" role="dialog" aria-modal="true" style="position:fixed;inset:0;visibility:hidden;opacity:0"></div>', True),
   ('display-none modal', '<div id="modal-test" aria-modal="true" style="display:none"></div>', True),
   ('modal inside hidden ancestor', '<div id="modal-test" hidden><div aria-modal="true" style="position:fixed;inset:0"></div></div>', True),
   ('transparent modal ancestor', '<div id="modal-test" style="opacity:0"><div aria-modal="true" style="position:fixed;inset:0"></div></div>', True),
   ('offscreen modal', '<div id="modal-test" aria-modal="true" style="position:fixed;left:-200vw;top:0;width:100vw;height:100vh"></div>', True),
   ('zero-sized modal placeholder', '<div id="modal-test" aria-modal="true" style="width:0;height:0"></div>', True),
   ('visible ARIA modal', '<div id="modal-test" role="dialog" aria-modal="true" style="position:fixed;inset:0;background:white"></div>', False),
  ]
  for label,markup,allowed in modal_cases:
   context('content');js('document.body.insertAdjacentHTML("beforeend",'+json.dumps(markup)+');document.querySelector("#button").focus();');keys(':')
   check(label+(' allows browsing shortcut' if allowed else ' retains keyboard ownership'),opened()==allowed)
   if allowed:keys('\ue00c')
   context('content');js('document.getElementById("modal-test").remove();')
  context('content');js('const modal=document.createElement("dialog");modal.id="modal-test";modal.innerHTML="<button>Dialog action</button>";document.body.appendChild(modal);modal.showModal();');keys(':')
  check('visible native modal retains keyboard ownership',not opened())
  context('content');js('document.getElementById("modal-test").close();document.getElementById("modal-test").remove();document.querySelector("#button").focus();');keys(':')
  check('closing native modal restores browsing shortcut',opened());keys('\ue00c')
  context('content');js('const modal=document.createElement("dialog");modal.id="modal-test";modal.textContent="Modeless panel";document.body.appendChild(modal);modal.show();document.querySelector("#button").focus();');keys(':')
  check('modeless native dialog does not disable browsing shortcut',opened());keys('\ue00c')
  context('content');js('document.getElementById("modal-test").close();document.getElementById("modal-test").remove();')
  js("""document.querySelector('#text').value='';document.querySelector('#button').focus();
    window.addEventListener('keydown', event => {
      if (event.key !== ':' || document.activeElement?.isContentEditable || document.activeElement?.matches('input,textarea')) return;
      const input = document.querySelector('#text');
      input.focus();
      input.value += event.key;
      event.preventDefault();
    }, {capture: true});""")
  keys(':');check('colon opens before the page redirects it into an input',opened());keys('\ue00c')
  context('content');check('page shortcut handler never received colon',js('return document.querySelector("#text").value==="";'))
  context('content');js('document.querySelector("#chat-composer").focus();');keys(';:');check('focused rich composer retains punctuation with site auto-focus handler installed',not opened());context('content');check('rich composer receives punctuation after browsing shortcut',js('return document.querySelector("#chat-composer").textContent.includes(";:;:");'))
  context('chrome');js('gURLBar.focus();');keys(':');check('address-bar typing does not open command line',not opened())
  openline();context('chrome');js('document.getElementById("focus-command-input").value="tabs";document.getElementById("focus-command-input").dispatchEvent(new Event("input"));')
  keys('\ue015');context('chrome');chosen=js('return document.querySelector(\'.focus-command-option[aria-selected="true"] strong\').textContent;');keys('\ue004');context('chrome');check('Down selects and Tab completes',js('return document.getElementById("focus-command-input").value;')==chosen)
  r=m.cmd('WebDriver:TakeScreenshot',{'id':None,'highlights':[],'full':False});r=r.get('value',r)
  (ROOT/'command-line-preview.png').write_bytes(base64.b64decode(r))
  keys('\ue00c')
  # Fuzzy ranking, recency, navigation and input editing.
  def query(text):
   context('chrome');js('FocusCommandLine.open(); const i=document.getElementById("focus-command-input");i.value='+json.dumps(text)+';i.dispatchEvent(new Event("input"));')
  def value():return js('return document.getElementById("focus-command-input").value;')
  def chosen():return js('return document.querySelector(\'.focus-command-option[aria-selected="true"] strong\')?.textContent;')
  def chord(letter):
   m.cmd('WebDriver:PerformActions',{'actions':[{'type':'key','id':'command-keys','actions':[{'type':'keyDown','value':'\ue009'},{'type':'keyDown','value':letter},{'type':'keyUp','value':letter},{'type':'keyUp','value':'\ue009'}]}]});time.sleep(.12)
  for text,expected in [('adr sh','address show'),('tbpk','tabs peek'),('FOCUS OF','focus off')]:
   query(text);check('fuzzy query '+text+' ranks expected command first',chosen()==expected);keys('\ue00c')
  command('address hide');query('adr sh');check('fuzzy match quality outranks recency',chosen()=='address show');keys('\ue00c')
  command('tabs peek');query('');check('successful execution moves command to top',chosen()=='tabs peek');keys('\ue007');check('Enter with empty query repeats default selection',not opened())
  context('chrome');saved=js('return Services.prefs.getStringPref("user.focusMode.commandLine.recentCommands");');check('recency stores command names only',all(isinstance(n,str) and n in ['focus on','focus off','focus toggle']+[a+' '+b for a in ['address','tabs'] for b in ['show','hide','toggle','peek']] for n in json.loads(saved)))
  js('FocusCommandLine.destroy();Services.scriptloader.loadSubScript("resource://custom-focus-mode/command-line.js",window,"UTF-8");');query('');check('recency survives reloading command UI',chosen()=='tabs peek');keys('\ue00c')
  query('tabs');before=value();chord('n');check('Ctrl+N moves selection without changing input',chosen()!='tabs peek' and value()==before);chord('p');check('Ctrl+P returns to previous selection',chosen()=='tabs peek' and value()==before);keys('\ue00c')
  query('');keys('address show');count=js('return gBrowser.tabs.length;');chord('w');check('Ctrl+W deletes previous whitespace-separated word',value()=='address ');check('Ctrl+W does not close a tab',js('return gBrowser.tabs.length;')==count)
  chord('z');check('Ctrl+Z undoes word deletion',value()=='address show');js('const i=document.getElementById("focus-command-input");i.setSelectionRange(i.value.length,i.value.length);');chord('u');check('Ctrl+U deletes to beginning',value()=='');check('Ctrl+U does not open source tab',js('return gBrowser.tabs.length;')==count)
  keys('tabs peek');chord('h');check('Ctrl+H deletes previous character',value()=='tabs pee');check('Ctrl+H keeps command line focused',js('return document.activeElement.id==="focus-command-input";'))
  query('address show');js('document.getElementById("focus-command-input").setSelectionRange(8,8);');chord('w');check('word deletion in middle preserves following text',value()=='show')
  query('address show');js('document.getElementById("focus-command-input").setSelectionRange(8,12);');chord('w');check('word deletion respects selected text',value()=='address ')
  query('address show');js('document.getElementById("focus-command-input").setSelectionRange(8,8);');chord('u');check('Ctrl+U preserves text after cursor',value()=='show')
  query('address show   ');chord('w');check('Ctrl+W consumes trailing whitespace with previous word',value()=='address ')
  query('   ');chord('w');check('Ctrl+W handles whitespace-only input',value()=='')
  query('tabs peek');keys('\ue011');chord('h');check('Ctrl+H at beginning preserves input',value()=='tabs peek');keys('\ue010');chord('h');check('End positions deletion at end of input',value()=='tabs pee')
  chord('c');check('Ctrl+C cancels command mode',not opened())
  # Browser shortcuts resume outside command mode in a disposable tab.
  context('content');old=m.cmd('WebDriver:GetWindowHandle',{});old=old.get('value',old);new=m.cmd('WebDriver:NewWindow',{'type':'tab'});new=new.get('value',new);m.cmd('WebDriver:SwitchToWindow',{'handle':new['handle']});context('chrome');js('gBrowser.selectedBrowser.focus();');chord('w');time.sleep(.2);m.cmd('WebDriver:SwitchToWindow',{'handle':old});context('chrome');check('Ctrl+W outside command mode closes its tab',js('return gBrowser.tabs.length;')==count)
  if vimium_xpi:
   context('chrome');check('Vimium installed in disposable profile',js('return Services.prefs.getStringPref("extensions.webextensions.uuids", "").includes("vimium-c@gdh1995.cn");'))
   context('chrome');js('gBrowser.selectedBrowser.focus();');context('content');js('document.activeElement.blur();');keys('f');keys(':')
   check('colon opens while Vimium hints are active',opened());keys('\ue00c');keys('\ue00c')
   keys('i');keys(':');check('colon opens in Vimium insert mode',opened());keys('\ue00c');keys('\ue00c')
  openline();context('chrome');js('gURLBar.focus();');time.sleep(.1);check('moving focus to browser UI dismisses command line',not opened())
 # A small blank PDF exercises the built-in viewer's resource document.
 objects=[b'<< /Type /Catalog /Pages 2 0 R >>',b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 400 400] /Resources << >> >>']
 pdf=b'%PDF-1.4\n';offsets=[0]
 for i,obj in enumerate(objects,1):
  offsets.append(len(pdf));pdf+=str(i).encode()+b' 0 obj\n'+obj+b'\nendobj\n'
 start=len(pdf);pdf+=b'xref\n0 4\n0000000000 65535 f \n'+b''.join(f'{n:010} 00000 n \n'.encode() for n in offsets[1:])+f'trailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n{start}\n%%EOF'.encode()
 (profile/'fixture.pdf').write_bytes(pdf)
 context('chrome');extension_id=json.loads(js('return Services.prefs.getStringPref("extensions.webextensions.uuids");')).get('vimium-c@gdh1995.cn')
 context('chrome');js("window.addEventListener('keydown',e=>{window.__tabLastKey={key:e.key,target:e.target.localName,uri:e.target.ownerDocument.documentURI};},true);")
 # The same shortcut must work across tab protocols and browser process types.
 context('content');m.cmd('WebDriver:Navigate',{'url':'about:preferences'});time.sleep(.5)
 js('document.querySelector("#searchInput").focus();');keys(':')
 check('focused Settings search retains colon',not opened())
 context('content')
 m.cmd('WebDriver:PerformActions',{'actions':[{'type':'key','id':'command-keys','actions':[
  {'type':'keyDown','value':'\ue009'},{'type':'keyDown','value':'\ue008'},
  {'type':'keyDown','value':'.'},{'type':'keyUp','value':'.'},
  {'type':'keyUp','value':'\ue008'},{'type':'keyUp','value':'\ue009'},
 ]}]});time.sleep(.12)
 check('Ctrl+Shift+Period opens from Settings search',opened())
 keys('\ue00c')
 destinations=['about:about','about:hub','about:keyboard','about:blank','about:newtab','about:preferences','about:addons','about:config','about:support', 'data:text/html,<title>Data tab</title><p>Data tab</p>',page.as_uri(), 'chrome://global/content/aboutAbout.html', 'view-source:'+url,url.replace('fixture.html','fixture.pdf')]
 if extension_id:destinations.append('moz-extension://'+extension_id+'/pages/options.html')
 for destination in destinations:
  context('content');m.cmd('WebDriver:Navigate',{'url':destination});time.sleep(.5)
  context('chrome');js('gBrowser.selectedBrowser.focus();')
  context('content');js('const body=document.body || document.documentElement;body.setAttribute("tabindex","-1");body.focus();');keys(':')
  check('colon opens in '+destination,opened())
  context('chrome');keys('\ue00c')
 # A fresh tab and an already-existing tab keep the shortcut after a switch.
 context('content');original=m.cmd('WebDriver:GetWindowHandle',{});original=original.get('value',original)
 created=m.cmd('WebDriver:NewWindow',{'type':'tab'});created=created.get('value',created)
 m.cmd('WebDriver:SwitchToWindow',{'handle':created['handle']});time.sleep(.4)
 context('chrome');js('gBrowser.selectedBrowser.focus();');context('content');js('document.body?.focus();');keys(':');check('newly opened tab supports command mode',opened())
 context('chrome');keys('\ue00c');context('content');m.cmd('WebDriver:CloseWindow',{});m.cmd('WebDriver:SwitchToWindow',{'handle':original});time.sleep(.2)
 context('chrome');js('gBrowser.selectedBrowser.focus();');context('content');js('document.body?.focus();');keys(':');check('existing tab still supports command mode after switching',opened())
 context('chrome');keys('\ue00c')
 context('content');m.cmd('WebDriver:Navigate',{'url':url});time.sleep(.3)
 # Existing Focus Mode regression suites run on this same disposable session.
 context('chrome');js('gURLBar.blur();gBrowser.selectedBrowser.focus();');m.cmd('WebDriver:DeleteSession',{});m.sock.close()
 for suite in ([] if '--commands-only' in sys.argv else ['test_integration.py','test_tabs_overlay.py']):
  subprocess.run([sys.executable,str(ROOT/suite),'2892'],check=True)
 (ROOT/'command-line-results.json').write_text(json.dumps({'passed':len(checks),'checks':checks,'profile':str(profile)},indent=2))
 print('Completed',len(checks),'checks; profile:',profile)

finally:
 process.terminate()
 try:process.wait(timeout=10)
 except subprocess.TimeoutExpired:process.kill()
