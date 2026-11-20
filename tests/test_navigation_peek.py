"""Verify document-load address peeks with real navigation and local redirects."""
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
        js('FocusMode.setAddressPinned(false);')
    time.sleep(1)
    settled()
    js('Services.prefs.setIntPref("user.focusMode.revealMs",500);FocusMode.normal();FocusMode.setTabsVisible(false);FocusMode.setAddressPinned(false);FocusMode.enable();gURLBar.blur();gBrowser.selectedBrowser.focus();')
    time.sleep(.7)
    check('starts with address bar hidden', not visible())
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
        check(operation + ' does not peek', not visible())
    context('content')
    js('void fetch("/slow-api");')
    time.sleep(.2)
    check('same-page fetch start does not peek', not visible())
    time.sleep(1)
    check('same-page fetch completion does not peek', not visible())
    hide()
    navigate('/slow')
    time.sleep(.15)
    check('new document peeks at load start', visible())
    time.sleep(.65)
    check('slow document does not extend the peek until completion', not visible())
    check('slow document is still loading after the peek expires', js('return gBrowser.selectedBrowser.webProgress.isLoadingDocument;'))
    settled()
    time.sleep(.15)
    check('load completion does not peek again', not visible())
    hide()
    js('gBrowser.selectedBrowser.reload();')
    time.sleep(.15)
    check('reload peeks once at load start', visible())
    time.sleep(.65)
    check('reload peek expires while request is still running', not visible())
    settled()
    time.sleep(.15)
    check('reload completion does not peek again', not visible())
    hide()
    navigate('/redirect/0')
    time.sleep(.15)
    check('redirect chain peeks at initial load start', visible())
    time.sleep(.65)
    check('intermediate redirects do not restart address timer', not visible())
    check('redirect chain remains in flight when original peek expires', js('return gBrowser.selectedBrowser.webProgress.isLoadingDocument;'))
    settled()
    time.sleep(.15)
    check('final redirect destination does not trigger a second peek', not visible())
    check('redirect chain reaches its final document', js('return gBrowser.selectedBrowser.currentURI.spec.endsWith("/slow-final");'))
    # A completed document followed by another navigation gets its own peek.
    navigate('/page-two')
    time.sleep(.15)
    check('a subsequent document gets a new peek', visible())
    settled()
    time.sleep(.6)
    check('subsequent document peek expires normally', not visible())
    js('gBrowser.goBack();')
    time.sleep(.15)
    check('Back to a different document peeks', visible())
    settled()
    time.sleep(.6)
    hide()
    # Tab creation itself is still a tab-activity trigger. Clear that separate
    # reveal before testing a document loading in an already-background tab.
    js('window.__backgroundPeekTab=gBrowser.addTrustedTab("about:blank",{skipAnimation:true});')
    time.sleep(.3)
    hide()
    js('window.__backgroundPeekTab.linkedBrowser.loadURI(Services.io.newURI(' + json.dumps(base + '/slow-background') + '),{triggeringPrincipal:Services.scriptSecurityManager.getSystemPrincipal()});')
    time.sleep(.2)
    check('background document start does not peek over current page', not visible())
    time.sleep(1)
    check('background document completion does not peek over current page', not visible())
    # A real subframe document is not a top-level navigation.
    context('content')
    js('const frame=document.createElement("iframe");frame.src=' + json.dumps(base + '/slow-frame') + ';document.body.appendChild(frame);')
    time.sleep(.2)
    check('subframe document start does not peek', not visible())
    time.sleep(1)
    check('subframe document completion does not peek', not visible())
    # Explicit address focus still holds the bar beyond the automatic delay.
    js('gURLBar.focus();')
    time.sleep(.7)
    check('explicit URL field focus holds address bar open', visible())
    js('gURLBar.blur();gBrowser.selectedBrowser.focus();')
    time.sleep(.15)
    check('leaving URL field retains its grace period', visible())
    time.sleep(.5)
    check('address focus grace period expires normally', not visible())
    (ROOT / 'navigation-peek-results.json').write_text(json.dumps({'passed':len(checks),'checks':checks}, indent=2))
    print('Completed',len(checks),'navigation peek checks.')
finally:
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
    server.shutdown()
