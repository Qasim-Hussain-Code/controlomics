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
    if (result.exceptionDetails) throw new Error(result.exceptionDetails.exception?.description || result.exceptionDetails.text);
    return result.result.value;
  };
  const until = async expression => {
    for (let attempt=0; attempt<80; attempt++) { if (await evaluate(expression)) return; await pause(100); }
    throw new Error('UI condition not reached: ' + expression);
  };
  const execute = script => evaluate('(async()=>{' + script + '})()');
  const observations = {browser: (await command('Browser.getVersion')).product, viewports: [], exceptions};
  for (const viewport of [{width:1440,height:1200,name:'controls'}, {width:430,height:1100,name:'mobile'}]) {
    await command('Emulation.setDeviceMetricsOverride', {...viewport, deviceScaleFactor:1, mobile:false});
    await command('Page.navigate', {url:'about:blank'});
    await until("location.href === 'about:blank' && typeof state === 'undefined'");
    await command('Page.navigate', {url:'http://127.0.0.1:8765/#demo=transcriptomics'});
    await until("typeof state !== 'undefined' && state.project !== null && !state.busy");
    const layout = await evaluate("({viewport:innerWidth,document:document.documentElement.scrollWidth,cards:document.querySelectorAll('.control-card').length,status:document.getElementById('status').textContent})");
    if (layout.viewport !== viewport.width || layout.document > viewport.width || layout.cards < 3) throw new Error('Layout check failed: ' + JSON.stringify(layout));
    observations.viewports.push({...viewport,...layout});
    await pause(150);
    const screenshot = await command('Page.captureScreenshot', {format:'png',captureBeyondViewport:false});
    fs.writeFileSync(path.join('docs','validation','ui_' + viewport.name + '.png'), Buffer.from(screenshot.data,'base64'));
  }
  await command('Emulation.setDeviceMetricsOverride', {width:1440,height:1200,deviceScaleFactor:1,mobile:false});
  for (const positive of [true,false]) {
    const csv = fs.readFileSync(path.join('examples', positive ? 'positive_reference.csv' : 'negative_reference.csv'),'utf8');
    await execute(`switchView('execution'); document.getElementById('execution-expected').value='${positive?2:0}'; document.getElementById('execution-assumptions').value='Hand-constructed synthetic independent units. This checks only a technical mean-difference reference.'; const files${positive?1:2}=new DataTransfer(); files${positive?1:2}.items.add(new File([${JSON.stringify(csv)}], 'synthetic.csv', {type:'text/csv'})); document.getElementById('numeric-file').files=files${positive?1:2}.files; document.getElementById('execution-form').requestSubmit();`);
    await until(`state.project.results.length === ${positive?1:2} && !state.busy`);
  }
  observations.execution = await evaluate("({outcomes:state.project.results.map(x=>x.outcome),pathways:state.project.execution_plans.map(x=>x.pathway),audit:state.project.audits[0].assessment,externalRequests:state.audit.length})");
  if (observations.execution.outcomes.join(',') !== 'PASS,PASS' || observations.execution.externalRequests !== 0) throw new Error('Execution check failed');
  observations.execution.unsupportedControlsExcluded = await evaluate("document.getElementById('execution-control').options.length===0 && state.project.controls.some(item=>item.scientific_level==='STATISTICAL')");
  if (!observations.execution.unsupportedControlsExcluded) throw new Error('An unsupported design control was selectable for numeric execution');
  observations.report = await evaluate("api('/api/report',{project:state.project,network_audit:state.audit},true).then(blob=>blob.text()).then(text=>({html:text.startsWith('<!doctype html>'),hasInputHashes:text.includes('Input hashes'),hasWarnings:text.includes('Warnings'),hasConservativeAssessment:text.includes('INSUFFICIENT_EVIDENCE')}))");
  if (!Object.values(observations.report).every(Boolean) || exceptions.length) throw new Error('Report or browser exception check failed');
  await execute("switchView('analysis'); document.getElementById('narrative-form').parentElement.open=true; document.getElementById('narrative-description').value='Question: A hypothetical question\\nAnalysis: A feature prediction analysis\\nMethods: Classification\\nResult: A hypothetical result\\nClaim: Features predict labels'; document.getElementById('narrative-form').requestSubmit();");
  await until("state.narrative !== null && !state.busy");
  await execute("document.getElementById('use-narrative').click()");
  observations.narrative = await evaluate("({claim:document.getElementById('analysis-form').elements.namedItem('claim').value,category:document.getElementById('analysis-form').elements.namedItem('claim_category').value,support:document.getElementById('analysis-form').elements.namedItem('computational_support').value})");
  if (observations.narrative.category || observations.narrative.support) throw new Error('Narrative categories were inferred without confirmation');
  await execute("document.getElementById('additional-claims').open=true; const claimForm=document.getElementById('claim-form'); claimForm.elements.namedItem('statement').value='A second hypothetical prediction claim'; claimForm.elements.namedItem('category').value='PREDICTIVE'; claimForm.elements.namedItem('computational_support').value='PREDICTIVE'; claimForm.requestSubmit();");
  await until("state.project.claims.length === 2 && !state.busy");
  observations.claims = await evaluate("({claims:state.project.claims.length,profiles:state.profiles.length,controlsByClaim:state.project.claims.map(claim=>state.project.controls.filter(control=>control.claim_tested===claim.claim_id).length)})");
  if (observations.claims.profiles !== 2 || observations.claims.controlsByClaim.some(count=>count<2)) throw new Error('Additional claim binding failed');
  await execute("document.getElementById('add-control').click(); const candidateForm=document.getElementById('candidate-form'); for(const name of ['name','rationale','expected_behavior','failure_interpretation','priority_rationale','limitations']) candidateForm.elements.namedItem(name).value='Hypothetical researcher specification for local UI testing'; candidateForm.requestSubmit();");
  await until("state.project.candidates.length === 1 && !state.busy");
  const candidateId = await evaluate("state.project.candidates[0].control_id");
  await execute("editCandidate(state.project.candidates[0]); document.getElementById('candidate-form').elements.namedItem('expected_behavior').value='Revised hypothetical expected behavior'; document.getElementById('candidate-form').requestSubmit();");
  await until("state.project.candidates[0].expected_behavior.startsWith('Revised') && !state.busy");
  observations.candidate = await evaluate("({status:state.project.candidates[0].evidence_status,id:state.project.candidates[0].control_id,revisionRecorded:state.project.provenance.some(item=>item.warnings.some(warning=>warning.startsWith('Superseded candidate snapshot')))})");
  if (observations.candidate.status !== 'UNVERIFIED' || observations.candidate.id !== candidateId || !observations.candidate.revisionRecorded) throw new Error('Candidate edit promoted or replaced the specification');
  await execute("const duplicateFile=new DataTransfer(); duplicateFile.items.add(new File(['{\"claim\":\"first\",\"claim\":\"second\"}'],'duplicate.json',{type:'application/json'})); document.getElementById('project-file').files=duplicateFile.files; document.getElementById('project-file').dispatchEvent(new Event('change'));");
  await until("document.getElementById('status').classList.contains('error') && !state.busy");
  observations.duplicateImportRejected = await evaluate("state.project.claims.length===2 && state.project.candidates.length===1");
  const evaluationBundle = fs.readFileSync('examples/benchmark.design.unassessed.json','utf8');
  await execute(`switchView('evaluation'); const evaluationFile=new DataTransfer(); evaluationFile.items.add(new File([${JSON.stringify(evaluationBundle)}],'development.unassessed.json',{type:'application/json'})); document.getElementById('evaluation-file').files=evaluationFile.files; document.getElementById('evaluation-form').requestSubmit();`);
  await until("state.evaluation !== null && !state.busy");
  observations.evaluation = await evaluate("({origin:state.evaluation.judgment_origin,precision:state.evaluation.metrics.recommendation_precision.value,unavailableDisplayed:document.getElementById('evaluation-result').textContent.includes('Unavailable'),cases:state.evaluation.coverage.cases})");
  if (observations.evaluation.precision !== null || observations.evaluation.origin !== 'UNASSESSED' || !observations.evaluation.unavailableDisplayed) throw new Error('Unassessed evaluation appeared measured');
  for (const viewport of [{width:1440,height:1200,name:'evaluation'}, {width:430,height:1100,name:'evaluation_mobile'}]) {
    await command('Emulation.setDeviceMetricsOverride', {...viewport,deviceScaleFactor:1,mobile:false});
    await execute('window.scrollTo(0,0)');
    if (await evaluate('document.documentElement.scrollWidth > innerWidth')) throw new Error('Evaluation layout overflow');
    const screenshot=await command('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});
    fs.writeFileSync(path.join('docs','validation','ui_' + viewport.name + '.png'),Buffer.from(screenshot.data,'base64'));
  }
  await execute("document.querySelector('.metric-panel').scrollIntoView({block:'start'})");
  await pause(150);
  const metricScreenshot=await command('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});
  fs.writeFileSync('docs/validation/ui_evaluation_metrics_mobile.png',Buffer.from(metricScreenshot.data,'base64'));
  const identities = JSON.parse(fs.readFileSync('docs/validation/literature_identity_checks.json','utf8')).evidence;
  await execute(`state.project.evidence=${JSON.stringify(identities)}; render(); await openReview(${JSON.stringify(candidateId)});`);
  observations.reviewForm = await evaluate("({statements:document.querySelectorAll('.statement-panel').length,attested:document.getElementById('human-attestation').checked,reviewer:document.getElementById('review-researcher').value})");
  if (observations.reviewForm.statements !== 2 || observations.reviewForm.attested || observations.reviewForm.reviewer || exceptions.length) throw new Error('Review form supplied an automatic attestation');
  observations.run_at = new Date().toISOString();
  observations.scope = 'Local synthetic workflow, description drafting, candidate editing, multi-claim and unassessed evaluation checks. Recorded public identity metadata was used only to display the review form; no human review was submitted, and no external request was made.';
  fs.writeFileSync('docs/validation/ui_checks.json',JSON.stringify(observations,null,2)+'\n');
  console.log(JSON.stringify(observations,null,2));
  await command('Browser.close'); socket.close();
})().catch(error=>{console.error(error.message);process.exit(1);});
