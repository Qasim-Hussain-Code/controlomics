// Optional development check; Node and Chrome are not runtime dependencies.
// Start the local Controlomics server on port 8765 first. In a fresh task-owned
// profile, launch installed Chrome headless with --enable-automation,
// --disable-background-networking, --disable-sync, --disable-extensions,
// --disable-component-update, --no-first-run, --no-default-browser-check,
// --remote-debugging-address=127.0.0.1, --remote-debugging-port=9227,
// --user-data-dir=<a new local QA directory>, and about:blank.
// Run node scripts/check_ui.cjs from the repository root. This performs only
// hypothetical local actions, saves validation artifacts, and closes that QA
// browser. Never attach it to a normal user profile or private project session.
const fs = require('node:fs');
const path = require('node:path');
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));

(async () => {
  const tabs = await (await fetch('http://127.0.0.1:9227/json/list')).json();
  const target = tabs.find(tab => tab.type === 'page');
  const socket = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => { socket.onopen = resolve; socket.onerror = reject; });
  let sequence = 0;
  const pending = new Map(), exceptions = [];
  const command = (method, params = {}) => new Promise((resolve, reject) => {
    const id = ++sequence;
    const timer = setTimeout(() => { pending.delete(id); reject(new Error(method + ' timed out')); }, 15000);
    pending.set(id, {resolve, reject, timer});
    socket.send(JSON.stringify({id, method, params}));
  });
  socket.onmessage = event => {
    const data = JSON.parse(event.data);
    if (data.id && pending.has(data.id)) {
      const item = pending.get(data.id); pending.delete(data.id); clearTimeout(item.timer);
      if (data.error) item.reject(new Error(JSON.stringify(data.error))); else item.resolve(data.result);
    }
    if (data.method === 'Runtime.exceptionThrown') exceptions.push(data.params.exceptionDetails.text);
    if (data.method === 'Page.javascriptDialogOpening') command('Page.handleJavaScriptDialog', {accept:true}).catch(() => {});
  };
  await command('Page.enable'); await command('Runtime.enable');
  const evaluate = async expression => {
    const result = await command('Runtime.evaluate', {expression, awaitPromise:true, returnByValue:true});
    if (result.exceptionDetails) throw new Error(result.exceptionDetails.text);
    return result.result.value;
  };
  const until = async expression => {
    for (let attempt=0; attempt<80; attempt++) { if (await evaluate(expression)) return; await pause(100); }
    throw new Error('UI condition not reached: ' + expression);
  };
  const observations = {browser: (await command('Browser.getVersion')).product, viewports: [], exceptions};
  for (const viewport of [{width:1440,height:1200,name:'controls'}, {width:430,height:1100,name:'mobile'}]) {
    await command('Emulation.setDeviceMetricsOverride', {...viewport, deviceScaleFactor:1, mobile:false});
    await command('Page.navigate', {url:'http://127.0.0.1:8765/#demo=transcriptomics'});
    await until("typeof state !== 'undefined' && state.project !== null && !state.busy");
    const layout = await evaluate("({viewport:innerWidth,document:document.documentElement.scrollWidth,cards:document.querySelectorAll('.control-card').length,status:document.getElementById('status').textContent})");
    if (layout.viewport !== viewport.width || layout.document > viewport.width || layout.cards !== 2) throw new Error('Layout check failed: ' + JSON.stringify(layout));
    observations.viewports.push({...viewport,...layout});
    await pause(150);
    const screenshot = await command('Page.captureScreenshot', {format:'png',captureBeyondViewport:false});
    fs.writeFileSync(path.join('docs','validation','ui_' + viewport.name + '.png'), Buffer.from(screenshot.data,'base64'));
  }
  await command('Emulation.setDeviceMetricsOverride', {width:1440,height:1200,deviceScaleFactor:1,mobile:false});
  for (const positive of [true,false]) {
    const csv = fs.readFileSync(path.join('examples', positive ? 'positive_reference.csv' : 'negative_reference.csv'),'utf8');
    await evaluate(`switchView('execution'); document.getElementById('execution-expected').value='${positive?2:0}'; document.getElementById('execution-assumptions').value='Hand-constructed synthetic independent units. This checks only a technical mean-difference reference.'; const files${positive?1:2}=new DataTransfer(); files${positive?1:2}.items.add(new File([${JSON.stringify(csv)}], 'synthetic.csv', {type:'text/csv'})); document.getElementById('numeric-file').files=files${positive?1:2}.files; document.getElementById('execution-form').requestSubmit();`);
    await until(`state.project.results.length === ${positive?1:2} && !state.busy`);
  }
  observations.execution = await evaluate("({outcomes:state.project.results.map(x=>x.outcome),pathways:state.project.execution_plans.map(x=>x.pathway),audit:state.project.audits[0].assessment,externalRequests:state.audit.length})");
  if (observations.execution.outcomes.join(',') !== 'PASS,PASS' || observations.execution.externalRequests !== 0) throw new Error('Execution check failed');
  observations.report = await evaluate("api('/api/report',{project:state.project,network_audit:state.audit},true).then(blob=>blob.text()).then(text=>({html:text.startsWith('<!doctype html>'),hasInputHashes:text.includes('Input hashes'),hasWarnings:text.includes('Warnings'),hasConservativeAssessment:text.includes('INSUFFICIENT_EVIDENCE')}))");
  if (!Object.values(observations.report).every(Boolean) || exceptions.length) throw new Error('Report or browser exception check failed');
  observations.run_at = new Date().toISOString();
  observations.scope = 'Local synthetic browser demonstration only; no biological data or external requests.';
  fs.writeFileSync('docs/validation/ui_checks.json',JSON.stringify(observations,null,2)+'\n');
  console.log(JSON.stringify(observations,null,2));
  await command('Browser.close'); socket.close();
})().catch(error=>{console.error(error.message);process.exit(1);});
