"""Verify document-load address and tab peeks with real navigation and local redirects."""
import http.server
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
from browser_fixture import prepare
from marionette_client import Marionette

ROOT = Path(__file__).parent

class Page(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split('?')[0]
        if path.startswith('/redirect/'):
            step = int(path.rsplit('/', 1)[1])
            time.sleep(.35)
            self.send_response(302)
            self.send_header('Location', '/redirect/' + str(step + 1) if step < 2 else '/slow-final')
            self.end_headers()
            return
        if path.startswith('/slow'):
            time.sleep(.95)
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        try:
            self.wfile.write(b'<!doctype html><title>Navigation peek fixture</title><p>Local document</p>')
        except (BrokenPipeError, ConnectionResetError):
            pass
    def log_message(self, *args):
        pass

server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Page)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = 'http://127.0.0.1:' + str(server.server_port)
profile = Path(tempfile.mkdtemp(prefix='floorp-navigation-check-'))
(profile / 'user.js').write_text('user_pref("marionette.port",2894);\nuser_pref("browser.aboutwelcome.enabled",false);\nuser_pref("floorp.browser.welcome.page.shown",true);\nuser_pref("browser.shell.checkDefaultBrowser",false);\nuser_pref("browser.startup.homepage_override.mstone","ignore");\n')
log = (profile / 'browser.log').open('w')
process = subprocess.Popen([prepare(profile), '--headless', '--no-remote', '--profile', str(profile), '--marionette', base + '/page'], env={**os.environ, 'MOZ_HEADLESS':'1', 'MOZ_REMOTE_ALLOW_SYSTEM_ACCESS':'1'}, stdout=log, stderr=log)
checks = []
try:
    for _ in range(100):
        try:
            m = Marionette(2894)
            break
        except ConnectionRefusedError:
            time.sleep(.15)
    else:
        raise RuntimeError('Browser did not start')
    def js(script):
        result = m.js(script)
        return result.get('value', result) if isinstance(result, dict) else result
    def context(name):
        m.cmd('Marionette:SetContext', {'value':name})
    def check(name, value):
        assert value, name
        checks.append(name)
        print('PASS', name, flush=True)
    def visible():
        context('chrome')
        return js('return document.documentElement.hasAttribute("focus-address-visible");')
    def both_hidden():
        context('chrome')
        return js('return !document.documentElement.hasAttribute("focus-address-visible") && !document.documentElement.hasAttribute("focus-tabs-visible");')
    def both_visible():
        context('chrome')
        return js('return document.documentElement.hasAttribute("focus-address-visible") && document.documentElement.hasAttribute("focus-tabs-overlay");')
    def navigate(path):
        context('chrome')
        js('gBrowser.selectedBrowser.loadURI(Services.io.newURI(' + json.dumps(base + path) + '),{triggeringPrincipal:Services.scriptSecurityManager.getSystemPrincipal()});')
    def settled():
        context('chrome')
        for _ in range(100):
            if not js('return gBrowser.selectedBrowser.webProgress.isLoadingDocument;'):
                return
            time.sleep(.05)
        raise AssertionError('Navigation did not finish')
    def hide():
        context('chrome')
        js('gURLBar.blur();gBrowser.selectedBrowser.focus();FocusMode.setAddressPinned(false);')
        time.sleep(.15)
        js('FocusMode.setAddressPinned(false);FocusMode.setTabsVisible(false);')
    time.sleep(1)
    m.cmd('WebDriver:PerformActions',{'actions':[{'type':'pointer','id':'mouse','parameters':{'pointerType':'mouse'},'actions':[{'type':'pointerMove','origin':'viewport','x':900,'y':400,'duration':0}]}]})
    settled()
    js('Services.prefs.setBoolPref("sidebar.verticalTabs",'+str(os.environ.get('FLOORP_TEST_VERTICAL') == '1').lower()+');')
    time.sleep(.3)
    js('Services.prefs.setIntPref("user.focusMode.revealMs",500);FocusMode.normal();FocusMode.setTabsVisible(false);FocusMode.setAddressPinned(false);FocusMode.enable();gURLBar.blur();gBrowser.selectedBrowser.focus();')
    time.sleep(.7)
    check('starts with address bar and tabs hidden', both_hidden())
    for operation, script in [
        ('fragment', 'location.hash="section";'),
        ('pushState query', 'history.pushState({},"","?filter=one#section");'),
        ('replaceState path and query', 'history.replaceState({},"","/route?filter=two");'),
        ('same-document Back', 'history.back();'),
    ]:
        hide()
        context('content')
        js(script)
        time.sleep(.2)
        check(operation + ' does not peek', both_hidden())
    context('content')
    js('void fetch("/slow-api");')
    time.sleep(.2)
    check('same-page fetch start does not peek', both_hidden())
    time.sleep(1)
    check('same-page fetch completion does not peek', both_hidden())
    hide()
    navigate('/slow')
    time.sleep(.15)
    check('new document peeks at load start (address and tabs)', both_visible())
    time.sleep(.65)
    check('slow document does not extend the peek until completion', both_hidden())
    check('slow document is still loading after the peek expires', js('return gBrowser.selectedBrowser.webProgress.isLoadingDocument;'))
    settled()
    time.sleep(.15)
    check('load completion does not peek again', both_hidden())
    hide()
    js('gBrowser.selectedBrowser.reload();')
    time.sleep(.15)
    check('reload peeks once at load start (address and tabs)', both_visible())
    time.sleep(.65)
    check('reload peek expires while request is still running', both_hidden())
    settled()
    time.sleep(.15)
    check('reload completion does not peek again', both_hidden())
    hide()
    navigate('/redirect/0')
    time.sleep(.15)
    check('redirect chain peeks at initial load start (address and tabs)', both_visible())
    time.sleep(.65)
    check('intermediate redirects do not restart address timer', both_hidden())
    check('redirect chain remains in flight when original peek expires', js('return gBrowser.selectedBrowser.webProgress.isLoadingDocument;'))
    settled()
    time.sleep(.15)
    check('final redirect destination does not trigger a second peek', both_hidden())
    check('redirect chain reaches its final document', js('return gBrowser.selectedBrowser.currentURI.spec.endsWith("/slow-final");'))
    # A completed document followed by another navigation gets its own peek.
    navigate('/page-two')
    time.sleep(.15)
    check('a subsequent document gets a new peek (address and tabs)', both_visible())
    settled()
    time.sleep(.6)
    check('subsequent document peek expires normally', both_hidden())
    js('gBrowser.goBack();')
    time.sleep(.15)
    check('Back to a different document peeks (address and tabs)', both_visible())
    settled()
    time.sleep(.6)
    hide()
    # Tab creation itself is still a tab-activity trigger. Clear that separate
    # reveal before testing a document loading in an already-background tab.
    js('window.__backgroundPeekTab=gBrowser.addTrustedTab("about:blank",{skipAnimation:true});')
    time.sleep(.3)
    check('opening a tab still reveals both bars', both_visible())
    hide()
    js('window.__backgroundPeekTab.linkedBrowser.loadURI(Services.io.newURI(' + json.dumps(base + '/slow-background') + '),{triggeringPrincipal:Services.scriptSecurityManager.getSystemPrincipal()});')
    time.sleep(.2)
    check('background document start does not peek over current page', both_hidden())
    time.sleep(1)
    check('background document completion does not peek over current page', both_hidden())
    hide()
    js('window.__originalPeekTab=gBrowser.selectedTab;gBrowser.selectedTab=window.__backgroundPeekTab;')
    time.sleep(.1)
    check('switching tabs still reveals both bars', both_visible())
    hide()
    js('gBrowser.selectedTab=window.__originalPeekTab;')
    time.sleep(.1)
    check('returning to original tab still reveals both bars', both_visible())
    hide()
    js('gBrowser.removeTab(window.__backgroundPeekTab,{animate:false});')
    time.sleep(.1)
    check('closing a tab still reveals both bars', both_visible())
    hide()
    # A real subframe document is not a top-level navigation.
    context('content')
    js('const frame=document.createElement("iframe");frame.src=' + json.dumps(base + '/slow-frame') + ';document.body.appendChild(frame);')
    time.sleep(.2)
    check('subframe document start does not peek', both_hidden())
    time.sleep(1)
    check('subframe document completion does not peek', both_hidden())
    # Explicit address focus still holds the bar beyond the automatic delay.
    js('gURLBar.focus();')
    time.sleep(.7)
    check('explicit URL field focus holds address bar open', visible())
    js('gURLBar.blur();gBrowser.selectedBrowser.focus();')
    time.sleep(.15)
    check('leaving URL field retains its grace period', visible())
    time.sleep(.5)
    check('address focus grace period expires normally', both_hidden())
    report = 'navigation-peek-vertical-results.json' if os.environ.get('FLOORP_TEST_VERTICAL') == '1' else 'navigation-peek-results.json'
    (ROOT / report).write_text(json.dumps({'passed':len(checks),'checks':checks}, indent=2))
    print('Completed',len(checks),'navigation peek checks.')
finally:
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
    server.shutdown()
