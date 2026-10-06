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
  const setViewport = async viewport => {
    await command('Emulation.setDeviceMetricsOverride', {width:viewport.width,height:viewport.height,deviceScaleFactor:1,mobile:false});
    // Let the responsive navigation transition finish before capture or hit tests.
    await pause(300);
  };
  const capture = async name => {
    await pause(200);
    const screenshot = await command('Page.captureScreenshot', {format:'png',captureBeyondViewport:false});
    fs.writeFileSync(path.join('docs','validation','ui_' + name + '.png'), Buffer.from(screenshot.data,'base64'));
  };
  const key = async (name, code, modifiers=0) => {
    await command('Input.dispatchKeyEvent',{type:'keyDown',key:name,code:name,windowsVirtualKeyCode:code,modifiers});
    await command('Input.dispatchKeyEvent',{type:'keyUp',key:name,code:name,windowsVirtualKeyCode:code,modifiers});
  };
  const countsMatch = "['claims','controls','evidence','results'].every((name,index)=>Number(document.getElementById('metric-'+name).textContent)===[state.project.claims.length,state.project.controls.length+state.project.candidates.length,state.project.evidence.length,state.project.results.filter(item=>item.execution_status==='COMPLETED').length][index] && document.getElementById('nav-'+name).textContent===document.getElementById('metric-'+name).textContent)";
  const observations = {browser: (await command('Browser.getVersion')).product, viewports: [], exceptions};
  await setViewport({width:1440,height:1000});
  await command('Page.navigate',{url:'http://127.0.0.1:8765/'});
  await until("typeof state !== 'undefined' && state.token !== null && !state.busy");
  observations.emptyWorkspace = await evaluate("({zeroCounts:[...document.querySelectorAll('.metric-value')].every(item=>item.textContent==='0'),savingDisabled:document.getElementById('export-bundle').disabled,searchDisabled:document.getElementById('control-search').disabled,view:state.view})");
  if (!observations.emptyWorkspace.zeroCounts || !observations.emptyWorkspace.savingDisabled || !observations.emptyWorkspace.searchDisabled || observations.emptyWorkspace.view!=='analysis') throw new Error('Empty workspace implied recorded results');
  await capture('workspace');
  for (const viewport of [{width:1440,height:1200,name:'controls'}, {width:430,height:1100,name:'mobile'}]) {
    await setViewport(viewport);
    await command('Page.navigate', {url:'about:blank'});
    await until("location.href === 'about:blank' && typeof state === 'undefined'");
    await command('Page.navigate', {url:'http://127.0.0.1:8765/#demo=transcriptomics'});
    await until("typeof state !== 'undefined' && state.project !== null && !state.busy");
    const layout = await evaluate("({viewport:innerWidth,document:document.documentElement.scrollWidth,cards:document.querySelectorAll('.control-card').length,status:document.getElementById('status').textContent})");
    if (layout.viewport !== viewport.width || layout.document > viewport.width || layout.cards < 3) throw new Error('Layout check failed: ' + JSON.stringify(layout));
    observations.viewports.push({...viewport,...layout});
    await capture(viewport.name);
  }
  await setViewport({width:1440,height:1200});
  observations.recordCounts = await evaluate(countsMatch);
  if (!observations.recordCounts) throw new Error('Workspace counts did not match project records');
  observations.controlSearch = await execute(`
    const snapshot=JSON.stringify(state.project), search=document.getElementById('control-search'), filter=document.getElementById('control-class-filter');
    search.value=state.project.controls[0].control_name; search.dispatchEvent(new Event('input'));
    const nameMatched=document.querySelectorAll('.control-card').length===1;
    search.value='no matching hypothetical specification'; search.dispatchEvent(new Event('input'));
    const noMatch=document.querySelectorAll('.control-card').length===0 && document.getElementById('control-list').textContent.includes('No controls match');
    search.value=''; filter.value='NEGATIVE'; filter.dispatchEvent(new Event('change'));
    const classMatched=[...document.querySelectorAll('.control-card')].every(card=>card.dataset.controlClass==='NEGATIVE') && document.querySelectorAll('.control-card').length===state.project.controls.filter(control=>control.control_class==='NEGATIVE').length;
    filter.value=''; filter.dispatchEvent(new Event('change'));
    return {nameMatched,noMatch,classMatched,restored:document.querySelectorAll('.control-card').length===state.project.controls.length,unchanged:JSON.stringify(state.project)===snapshot};
  `);
  if (!Object.values(observations.controlSearch).every(Boolean)) throw new Error('Control filtering changed records or selected the wrong collection');
  await execute("document.getElementById('tab-controls').focus()");
  await key('ArrowDown',40);
  const arrow = await evaluate("state.view==='evidence' && document.activeElement.id==='tab-evidence' && document.querySelectorAll('.tab[tabindex=\"0\"]').length===1");
  await key('End',35);
  const end = await evaluate("state.view==='evaluation' && document.activeElement.id==='tab-evaluation'");
  await key('Home',36);
  const home = await evaluate("state.view==='analysis' && document.activeElement.id==='tab-analysis'");
  observations.keyboardNavigation = {arrow,end,home};
  if (!arrow || !end || !home) throw new Error('Keyboard tab navigation failed');
  await execute('window.scrollTo(0,0)');
  await capture('analysis');
  observations.responsiveViews=[];
  for (const width of [375,768,1024,1440]) {
    await setViewport({width,height:900});
    for (const view of ['analysis','controls','evidence','execution','audit','evaluation']) {
      await execute(`switchView(${JSON.stringify(view)}); window.scrollTo(0,0);`);
      const layout=await evaluate("({width:innerWidth,document:document.documentElement.scrollWidth,view:state.view})");
      if (layout.document>width) throw new Error('Responsive view overflow: '+JSON.stringify(layout));
      observations.responsiveViews.push(layout);
    }
  }
  await setViewport({width:430,height:1100});
  await execute("switchView('controls'); document.getElementById('nav-toggle').click()");
  await until("document.getElementById('nav-toggle').getAttribute('aria-expanded')==='true'");
  const modal = await evaluate("document.getElementById('workspace-canvas').inert && !document.getElementById('workspace-nav').inert && document.getElementById('workspace-nav').getAttribute('aria-modal')==='true'");
  await key('Tab',9);
  const trapped = await evaluate("document.activeElement.classList.contains('brand')");
  await key('Tab',9,8);
  const reverseTrapped = await evaluate("document.activeElement.id==='tab-controls'");
  await capture('navigation_mobile');
  await key('Escape',27);
  const escaped = await evaluate("!document.body.classList.contains('nav-open') && !document.getElementById('workspace-canvas').inert && document.getElementById('workspace-nav').inert && document.activeElement.id==='nav-toggle'");
  await execute("document.getElementById('nav-toggle').click(); document.getElementById('tab-evidence').click()");
  const selected = await evaluate("state.view==='evidence' && !document.body.classList.contains('nav-open') && document.activeElement.id==='workspace-main'");
  await execute("document.querySelector('.metric-card[data-target=\"controls\"]').click()");
  const metricNavigation = await evaluate("state.view==='controls'");
  observations.mobileNavigation={modal,trapped,reverseTrapped,escaped,selected,metricNavigation};
  if (!Object.values(observations.mobileNavigation).every(Boolean)) throw new Error('Mobile navigation or focus boundary failed');
  await execute("document.querySelector('.workspace-menu summary').click()");
  await key('Escape',27);
  observations.fileMenus=await evaluate("!document.querySelector('.workspace-menu[open]') && document.activeElement.matches('.workspace-menu summary')");
  if (!observations.fileMenus) throw new Error('File menu Escape navigation failed');
  await command('Emulation.setEmulatedMedia',{features:[{name:'prefers-reduced-motion',value:'reduce'}]});
  observations.reducedMotion=await evaluate("matchMedia('(prefers-reduced-motion:reduce)').matches && getComputedStyle(document.getElementById('view-controls')).animationName==='none' && getComputedStyle(document.getElementById('workspace-nav')).transitionDuration==='0s'");
  if (!observations.reducedMotion) throw new Error('Reduced-motion preference was not respected');
  await command('Emulation.setEmulatedMedia',{features:[]});
  observations.textRendering=await execute("const original=state.project.analysis.scientific_question; const text='<img src=x onerror=window.untrustedMarkupExecuted=true> synthetic display fixture'; state.project.analysis.scientific_question=text; render(); const safe=document.getElementById('project-title').textContent===text && document.getElementById('project-title').children.length===0 && !window.untrustedMarkupExecuted; state.project.analysis.scientific_question=original; render(); return safe;");
  if (!observations.textRendering) throw new Error('Project title was interpreted as HTML');
  await setViewport({width:1440,height:1200});
  for (const positive of [true,false]) {
    const csv = fs.readFileSync(path.join('examples', positive ? 'positive_reference.csv' : 'negative_reference.csv'),'utf8');
    await execute(`switchView('execution'); document.getElementById('execution-expected').value='${positive?2:0}'; document.getElementById('execution-assumptions').value='Hand-constructed synthetic independent units. This checks only a technical mean-difference reference.'; const files${positive?1:2}=new DataTransfer(); files${positive?1:2}.items.add(new File([${JSON.stringify(csv)}], 'synthetic.csv', {type:'text/csv'})); document.getElementById('numeric-file').files=files${positive?1:2}.files; document.getElementById('execution-form').requestSubmit();`);
    await until(`state.project.results.length === ${positive?1:2} && !state.busy`);
  }
  observations.execution = await evaluate("({outcomes:state.project.results.map(x=>x.outcome),pathways:state.project.execution_plans.map(x=>x.pathway),audit:state.project.audits[0].assessment,externalRequests:state.audit.length})");
  observations.controlomicsVersion = await evaluate("state.project.provenance.at(-1).controlomics_version");
  const expectedVersion = /^version = "([^"]+)"/m.exec(fs.readFileSync('pyproject.toml','utf8'))[1];
  if (observations.controlomicsVersion !== expectedVersion) throw new Error('Running server differs from the package version');
  if (observations.execution.outcomes.join(',') !== 'PASS,PASS' || observations.execution.externalRequests !== 0) throw new Error('Execution check failed');
  observations.execution.unsupportedControlsExcluded = await evaluate("document.getElementById('execution-control').options.length===0 && state.project.controls.some(item=>item.scientific_level==='STATISTICAL')");
  if (!observations.execution.unsupportedControlsExcluded) throw new Error('An unsupported design control was selectable for numeric execution');
  await execute("switchView('execution'); document.querySelector('#paired-form').parentElement.open=true; document.getElementById('paired-rationale').value='Hypothetical complete pairs for a software UI check.'; document.getElementById('paired-assumptions').value='Synthetic independent pairs with sign invariance under the tested null.'; document.getElementById('paired-form').requestSubmit();");
  await until("document.getElementById('execution-adapter').value==='PAIRED_DIFFERENCE' && !state.busy");
  const pairedCSV = 'pair,condition,value\na,0,10\na,1,11\nb,0,20\nb,1,22\nc,0,30\nc,1,33\n';
  await execute(`document.getElementById('adapter-rationale').value='The fixture contains three complete independent pairs.'; const pairFiles=new DataTransfer(); pairFiles.items.add(new File([${JSON.stringify(pairedCSV)}],'paired.csv',{type:'text/csv'})); document.getElementById('numeric-file').files=pairFiles.files; document.getElementById('execution-form').requestSubmit();`);
  await until("state.project.results.length===3 && !state.busy");
  observations.pairedExecution = await evaluate("({outcome:state.project.results[2].outcome,p:state.project.results[2].p_value,input:state.project.results[2].input_hashes[0].input_id,remaining:document.getElementById('execution-control').options.length})");
  if (observations.pairedExecution.outcome!=='INDETERMINATE' || observations.pairedExecution.p!==0.25 || observations.pairedExecution.input!=='paired_units' || observations.pairedExecution.remaining!==0) throw new Error('Paired adapter workflow failed');
  observations.executedRecordCounts=await evaluate(countsMatch);
  if (!observations.executedRecordCounts) throw new Error('Counts did not update after execution');
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
    await setViewport(viewport);
    await execute('window.scrollTo(0,0)');
    if (await evaluate('document.documentElement.scrollWidth > innerWidth')) throw new Error('Evaluation layout overflow');
    await capture(viewport.name);
  }
  await execute("document.querySelector('.metric-panel').scrollIntoView({block:'start'})");
  observations.metricHeadingVisible=await evaluate("document.querySelector('.metric-panel').getBoundingClientRect().top>=document.querySelector('.topbar').getBoundingClientRect().bottom");
  if (!observations.metricHeadingVisible) throw new Error('Metric heading was obscured by the header');
  await capture('evaluation_metrics_mobile');
  await execute("document.getElementById('open-annotations').click()");
  await until("document.getElementById('annotation-panel').open && !state.busy");
  observations.annotations = await evaluate("({origin:document.getElementById('annotation-origin').value,reviewer:document.getElementById('annotation-reviewer').value,attested:document.getElementById('annotation-attestation').checked,unknown:[...document.querySelectorAll('#annotation-controls select')].every(item=>item.value===''),matchesDisabled:[...document.querySelectorAll('#annotation-controls input')].every(item=>item.disabled),savedOrigin:state.evaluationBundle.judgment_origin})");
  if (observations.annotations.origin || observations.annotations.reviewer || observations.annotations.attested || !observations.annotations.unknown || !observations.annotations.matchesDisabled || observations.annotations.savedOrigin!=='UNASSESSED') throw new Error('Annotation workbench inferred a human judgment');
  for (const viewport of [{width:1440,height:1200,name:'annotations'}, {width:430,height:1100,name:'annotations_mobile'}]) {
    await setViewport(viewport);
    await execute("document.getElementById('annotation-panel').scrollIntoView({block:'start'})");
    if (await evaluate('document.documentElement.scrollWidth>innerWidth')) throw new Error('Annotation layout overflow');
    if (await evaluate("document.getElementById('annotation-panel').getBoundingClientRect().top<document.querySelector('.topbar').getBoundingClientRect().bottom")) throw new Error('Judgment workbench heading was obscured');
    await capture(viewport.name);
  }
  observations.reviewBundle = await execute("const archive=await api('/api/review-bundle',{project:state.project,network_audit:state.audit,evaluation_bundle:state.evaluationBundle,annotation_revisions:state.revisions},true); const bytes=new Uint8Array(await archive.arrayBuffer()); let encoded=''; for(let start=0;start<bytes.length;start+=16384) encoded+=String.fromCharCode(...bytes.subarray(start,start+16384)); const restored=await api('/api/open-bundle',{archive_base64:btoa(encoded)}); return {bytes:bytes.length,sameProject:JSON.stringify(restored.project)===JSON.stringify(state.project),sameEvaluation:JSON.stringify(restored.evaluation_bundle)===JSON.stringify(state.evaluationBundle),networkEvents:restored.network_audit_restored.length,revisions:restored.annotation_revisions.length};");
  if (!observations.reviewBundle.sameProject || !observations.reviewBundle.sameEvaluation || observations.reviewBundle.networkEvents!==0) throw new Error('Review archive roundtrip failed');
  const identities = JSON.parse(fs.readFileSync('docs/validation/literature_identity_checks.json','utf8')).evidence;
  await execute(`state.project.evidence=${JSON.stringify(identities)}; render(); await openReview(${JSON.stringify(candidateId)});`);
  observations.reviewForm = await evaluate("({statements:document.querySelectorAll('#statement-reviews .statement-panel').length,attested:document.getElementById('human-attestation').checked,reviewer:document.getElementById('review-researcher').value})");
  if (observations.reviewForm.statements !== 2 || observations.reviewForm.attested || observations.reviewForm.reviewer || exceptions.length) throw new Error('Review form supplied an automatic attestation');
  observations.run_at = new Date().toISOString();
  observations.scope = 'Responsive workspace, actual record counts, search and class filters, keyboard tabs, mobile focus boundaries, file menus, reduced motion, text-only rendering, local synthetic reference and paired execution, description drafting, candidate editing, multi-claim, unassessed evaluation, blank judgment workbench, visible review headings, and review archive roundtrip. Recorded public identity metadata was used only to display the source-review form; no human source review or benchmark judgment was submitted, and no external request was made. This is browser integration coverage, not a screen-reader, full accessibility, or scientific validation.';
  fs.writeFileSync('docs/validation/ui_checks.json',JSON.stringify(observations,null,2)+'\n');
  console.log(JSON.stringify(observations,null,2));
  await command('Browser.close'); socket.close();
})().catch(error=>{console.error(error.message);process.exit(1);});
