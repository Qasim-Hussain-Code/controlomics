// Optional development check; Node and Chrome are not runtime dependencies.
// Start the local Controlomics server on port 8765 first. In a fresh task-owned
// profile, launch installed Chrome headless with --enable-automation,
// --disable-background-networking, --disable-sync, --disable-extensions,
// --disable-component-update, --no-first-run, --no-default-browser-check,
// --remote-debugging-address=127.0.0.1, --remote-debugging-port=9227,
// --user-data-dir=<a new local QA directory>, and about:blank.
// Run node scripts/check_ui.cjs --profile <that exact QA directory> from the repository root. This performs only
// hypothetical local actions, saves validation artifacts, and closes that QA
// browser. Never attach it to a normal user profile or private project session.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const {parseArgs} = require('node:util');
const {values} = parseArgs({options: {
  server: {type:'string',default:'http://127.0.0.1:8765'},
  'debug-port': {type:'string',default:'9227'},
  profile: {type:'string'}, output: {type:'string',default:'docs/validation'},
  downloads: {type:'string',default:'local_projects/ui-check/downloads'}
}});
const serverURL = new URL(values.server);
if (serverURL.protocol !== 'http:' || serverURL.hostname !== '127.0.0.1' || serverURL.username || serverURL.password || serverURL.pathname !== '/' || serverURL.search || serverURL.hash) throw new Error('UI checks require a loopback server origin');
const serverOrigin = serverURL.origin;
const debugPort = Number(values['debug-port']);
if (!Number.isInteger(debugPort) || debugPort < 1 || debugPort > 65535 || !values.profile) throw new Error('Supply a valid debug port and the exact task-owned --profile directory');
const expectedProfile = path.resolve(values.profile), outputDirectory = path.resolve(values.output);
fs.mkdirSync(outputDirectory,{recursive:true});
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));

(async () => {
  const tabs = await (await fetch('http://127.0.0.1:'+debugPort+'/json/list')).json();
  const target = tabs.find(tab => tab.type === 'page');
  const socket = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => { socket.onopen = resolve; socket.onerror = reject; });
  let sequence = 0;
  const pending = new Map(), exceptions = [], externalRequests = [];
  const command = (method, params = {}, sessionId) => new Promise((resolve, reject) => {
    const id = ++sequence;
    const timer = setTimeout(() => { pending.delete(id); reject(new Error(method + ' timed out')); }, 15000);
    pending.set(id, {resolve, reject, timer});
    socket.send(JSON.stringify({id, method, params, ...(sessionId ? {sessionId} : {})}));
  });
  socket.onmessage = event => {
    const data = JSON.parse(event.data);
    if (data.id && pending.has(data.id)) {
      const item = pending.get(data.id); pending.delete(data.id); clearTimeout(item.timer);
      if (data.error) item.reject(new Error(JSON.stringify(data.error))); else item.resolve(data.result);
    }
    if (data.method === 'Runtime.exceptionThrown') exceptions.push(data.params.exceptionDetails.text);
    if (data.method === 'Network.requestWillBeSent' && /^https?:/.test(data.params.request.url) && new URL(data.params.request.url).origin !== serverOrigin) externalRequests.push('Nonlocal request observed');
    if (data.method === 'Page.javascriptDialogOpening') command('Page.handleJavaScriptDialog', {accept:true}).catch(() => {});
  };
  const browserArguments = (await command('Browser.getBrowserCommandLine')).arguments;
  const profileArgument = browserArguments.find(argument=>argument.startsWith('--user-data-dir='));
  if (!browserArguments.includes('--headless=new') || !profileArgument || path.resolve(profileArgument.slice('--user-data-dir='.length)) !== expectedProfile) throw new Error('Refusing to use or close a browser outside the explicitly selected headless QA profile');
  await command('Page.enable'); await command('Runtime.enable'); await command('Network.enable');
  await command('Browser.setDownloadBehavior',{behavior:'allow',downloadPath:path.resolve(values.downloads)});
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
    fs.writeFileSync(path.join(outputDirectory,'ui_' + name + '.png'), Buffer.from(screenshot.data,'base64'));
  };
  const key = async (name, code, modifiers=0) => {
    await command('Input.dispatchKeyEvent',{type:'keyDown',key:name,code:name,windowsVirtualKeyCode:code,modifiers});
    await command('Input.dispatchKeyEvent',{type:'keyUp',key:name,code:name,windowsVirtualKeyCode:code,modifiers});
  };
  const countsMatch = "['claims','controls','evidence','results'].every((name,index)=>Number(document.getElementById('metric-'+name).textContent)===[state.project.claims.length,state.project.controls.length+state.project.candidates.length,state.project.evidence.length,state.project.results.filter(item=>item.execution_status==='COMPLETED').length][index] && document.getElementById('nav-'+name).textContent===document.getElementById('metric-'+name).textContent)";
  const observations = {browser: (await command('Browser.getVersion')).product, viewports: [], exceptions, externalRequests};
  const privateAttributionSourceCheck = fs.readFileSync('src/controlomics/web/index.html','utf8').includes('<footer><span>Controlomics</span>');
  if (!privateAttributionSourceCheck) throw new Error('Workspace footer has unexpected attribution');
  await setViewport({width:1440,height:1000});
  await command('Page.navigate',{url:serverOrigin+'/'});
  await until("typeof state !== 'undefined' && state.token !== null && !state.busy");
  observations.emptyWorkspace = await evaluate("({zeroCounts:[...document.querySelectorAll('.metric-value')].every(item=>item.textContent==='0'),savingDisabled:document.getElementById('export-bundle').disabled,searchDisabled:document.getElementById('control-search').disabled,view:state.view})");
  if (!observations.emptyWorkspace.zeroCounts || !observations.emptyWorkspace.savingDisabled || !observations.emptyWorkspace.searchDisabled || observations.emptyWorkspace.view!=='analysis') throw new Error('Empty workspace implied recorded results');
  await capture('workspace');
  observations.emptyDraftProtection=await execute("const field=document.getElementById('analysis-form').elements.namedItem('question'); field.value='Synthetic unrecorded input'; field.dispatchEvent(new Event('input',{bubbles:true})); const tracked=hasUnsavedWork() && document.getElementById('save-state').textContent==='Unrecorded inputs'; const previousConfirm=window.confirm; window.confirm=()=>false; document.getElementById('new-workspace').click(); const retained=field.value==='Synthetic unrecorded input'; window.confirm=()=>true; document.getElementById('new-workspace').click(); window.confirm=previousConfirm; return {tracked,retained,cleared:field.value==='' && !hasUnsavedWork()};");
  if (!Object.values(observations.emptyDraftProtection).every(Boolean)) throw new Error('Empty-workspace input protection failed');
  observations.programmaticDraftProtection=await execute("const form=document.getElementById('analysis-form'); example('rna'); const tracked=state.drafts.has('analysis-form'); const question=form.elements.namedItem('question').value, prior=window.confirm; window.confirm=()=>false; example('ml'); const retained=form.elements.namedItem('question').value===question; window.confirm=()=>true; document.getElementById('new-workspace').click(); window.confirm=prior; return {tracked,retained,cleared:!hasUnsavedWork()};");
  if (!Object.values(observations.programmaticDraftProtection).every(Boolean)) throw new Error('Programmatically filled analysis fields were unprotected');
  for (const viewport of [{width:1440,height:1200,name:'controls'}, {width:430,height:1100,name:'mobile'}]) {
    await setViewport(viewport);
    await command('Page.navigate', {url:'about:blank'});
    await until("location.href === 'about:blank' && typeof state === 'undefined'");
    await command('Page.navigate', {url:serverOrigin+'/#demo=transcriptomics'});
    await until("typeof state !== 'undefined' && state.project !== null && !state.busy");
    const layout = await evaluate("({viewport:innerWidth,document:document.documentElement.scrollWidth,cards:document.querySelectorAll('.control-card').length,status:document.getElementById('status').textContent})");
    if (layout.viewport !== viewport.width || layout.document > viewport.width || layout.cards < 3) throw new Error('Layout check failed: ' + JSON.stringify(layout));
    observations.viewports.push({...viewport,...layout});
    await capture(viewport.name);
  }
  await setViewport({width:1440,height:1200});
  observations.recordCounts = await evaluate(countsMatch);
  if (!observations.recordCounts) throw new Error('Workspace counts did not match project records');
  await execute("document.getElementById('export-bundle').click()");
  await until("state.preparedRevision===state.revision && !state.busy");
  observations.preparedDownload=await evaluate("!hasUnsavedWork() && document.getElementById('save-state').textContent==='Bundle prepared'");
  if (!observations.preparedDownload) throw new Error('Prepared bundle status did not match its recorded revision');
  observations.draftReversion=await execute("const field=document.getElementById('analysis-form').elements.namedItem('question'), original=field.value; field.value='Synthetic temporary edit'; field.dispatchEvent(new Event('input',{bubbles:true})); const changed=hasUnsavedWork(); field.value=original; field.dispatchEvent(new Event('input',{bubbles:true})); return {changed,reverted:!hasUnsavedWork()};");
  if (!Object.values(observations.draftReversion).every(Boolean)) throw new Error('Draft reversion did not restore save status');
  observations.executionFields=await execute("const kind=document.getElementById('execution-kind'); kind.value='REFERENCE'; syncExecutionFields(); const reference=!document.getElementById('execution-reference-fields').hidden && document.getElementById('execution-resampling-fields').hidden; kind.value='BOOTSTRAP'; syncExecutionFields(); const bootstrap=document.getElementById('execution-reference-fields').hidden && !document.getElementById('execution-coverage-label').hidden && !document.getElementById('execution-coverage').disabled; kind.value='PERMUTATION'; syncExecutionFields(); const permutation=document.getElementById('execution-coverage-label').hidden && document.getElementById('execution-expected').disabled; kind.value='REFERENCE'; syncExecutionFields(); return {reference,bootstrap,permutation};");
  if (!Object.values(observations.executionFields).every(Boolean)) throw new Error('Procedure-specific inputs were misleading');
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
  await execute("document.getElementById('nav-toggle').click(); document.getElementById('nav-close').click()");
  const closeButton=await evaluate("!document.body.classList.contains('nav-open') && document.activeElement.id==='nav-toggle' && !document.getElementById('workspace-canvas').inert");
  observations.mobileNavigation={modal,trapped,reverseTrapped,escaped,selected,metricNavigation,closeButton};
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
  const bomCSV='\ufeffunit,label,value\na,0,0\nb,0,1\nc,1,2\nd,1,3\n';
  await execute(`switchView('execution'); const csvFile=new DataTransfer(); csvFile.items.add(new File([${JSON.stringify(bomCSV)}],'synthetic-bom.csv',{type:'text/csv'})); document.getElementById('numeric-file').files=csvFile.files; document.getElementById('numeric-file').dispatchEvent(new Event('change',{bubbles:true})); document.getElementById('inspect-input').click();`);
  await until("state.inputSummary!==null && !state.busy");
  observations.inputInspection=await evaluate("({rows:state.inputSummary.rows,zero:state.inputSummary.group_zero_units,one:state.inputSummary.group_one_units,bom:state.inputSummary.utf8_bom,sha256:state.inputSummary.input_sha256,results:state.project.results.length,externalRequests:state.audit.length})");
  if (observations.inputInspection.rows!==4 || observations.inputInspection.zero!==2 || observations.inputInspection.one!==2 || !observations.inputInspection.bom || observations.inputInspection.sha256!==crypto.createHash('sha256').update(bomCSV,'utf8').digest('hex') || observations.inputInspection.results!==0 || observations.inputInspection.externalRequests!==0) throw new Error('Input inspection changed bytes, executed a control, or sent externally');
  await execute("document.getElementById('input-summary').scrollIntoView({block:'start'})");
  await capture('input_inspection');
  await execute("const invalidCSV=new DataTransfer(); invalidCSV.items.add(new File([new Uint8Array([255,10,65])],'invalid.csv',{type:'text/csv'})); document.getElementById('numeric-file').files=invalidCSV.files; document.getElementById('numeric-file').dispatchEvent(new Event('change',{bubbles:true})); document.getElementById('inspect-input').click();");
  await until("document.getElementById('status').classList.contains('error') && !state.busy");
  observations.invalidUTF8=await evaluate("state.inputSummary===null && state.project.results.length===0 && document.getElementById('status').textContent.includes('UTF-8')");
  if (!observations.invalidUTF8) throw new Error('Invalid UTF-8 was silently replaced');
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
  await execute("switchView('execution'); document.querySelector('#paired-form').parentElement.open=true; document.getElementById('paired-rationale').value='Synthetic complete pairs to check bootstrap parameter recording.'; document.getElementById('paired-assumptions').value='Synthetic independent complete pairs; whole-pair resampling only.'; document.getElementById('paired-form').requestSubmit();");
  await until("document.getElementById('execution-control').options.length===1 && !state.busy");
  await execute(`document.getElementById('execution-kind').value='BOOTSTRAP'; document.getElementById('execution-kind').dispatchEvent(new Event('change',{bubbles:true})); document.getElementById('execution-coverage').value='0.9'; document.getElementById('execution-draws').value='199'; document.getElementById('execution-seed').value='17'; document.getElementById('adapter-rationale').value='Synthetic complete pairs match this software fixture.'; document.getElementById('execution-assumptions').value='Hypothetical independent pairs and whole-pair resampling. Coverage has not been evaluated.'; const bootstrapFiles=new DataTransfer(); bootstrapFiles.items.add(new File([${JSON.stringify(pairedCSV)}],'bootstrap-paired.csv',{type:'text/csv'})); document.getElementById('numeric-file').files=bootstrapFiles.files; document.getElementById('execution-form').requestSubmit();`);
  await until("state.project.results.length===4 && !state.busy");
  observations.pairedBootstrap=await evaluate("({outcome:state.project.results[3].outcome,coverage:state.project.results[3].confidence_interval.coverage,seed:state.project.results[3].random_seed,method:state.project.results[3].confidence_interval.method})");
  if (observations.pairedBootstrap.outcome!=='INDETERMINATE' || observations.pairedBootstrap.coverage!==0.9 || observations.pairedBootstrap.seed!==17 || !observations.pairedBootstrap.method.includes('Complete-pair')) throw new Error('Bootstrap configuration was not reflected in its actual result');
  observations.report = await evaluate("api('/api/report',{project:state.project,network_audit:state.audit},true).then(blob=>blob.text()).then(text=>({html:text.startsWith('<!doctype html>'),hasInputHashes:text.includes('Input hashes'),hasWarnings:text.includes('Warnings'),hasConservativeAssessment:text.includes('INSUFFICIENT_EVIDENCE')}))");
  if (!Object.values(observations.report).every(Boolean) || exceptions.length) throw new Error('Report or browser exception check failed');
  const reportHTML=await evaluate("api('/api/report',{project:state.project,network_audit:state.audit},true).then(blob=>blob.text())");
  const reportTarget=await command('Target.createTarget',{url:'about:blank'});
  const reportSession=(await command('Target.attachToTarget',{targetId:reportTarget.targetId,flatten:true})).sessionId;
  await command('Page.enable',{},reportSession);
  const reportFrame=(await command('Page.getFrameTree',{},reportSession)).frameTree.frame.id;
  await command('Page.setDocumentContent',{frameId:reportFrame,html:reportHTML},reportSession);
  observations.reportLayout=[];
  for (const viewport of [{width:1440,height:1200,name:'report'}, {width:430,height:1100,name:'report_mobile'}]) {
    await command('Emulation.setDeviceMetricsOverride',{width:viewport.width,height:viewport.height,deviceScaleFactor:1,mobile:false},reportSession);
    await pause(200);
    const measured=await command('Runtime.evaluate',{expression:"({width:innerWidth,document:document.documentElement.scrollWidth,links:[...document.querySelectorAll('a[href^=\"#\"]')].every(link=>document.getElementById(link.getAttribute('href').slice(1))!==null),noScripts:document.scripts.length===0})",returnByValue:true},reportSession);
    const layout=measured.result.value;
    if (layout.document>viewport.width || !layout.links || !layout.noScripts) throw new Error('Report layout or internal references failed');
    observations.reportLayout.push(layout);
    const screenshot=await command('Page.captureScreenshot',{format:'png',captureBeyondViewport:false},reportSession);
    fs.writeFileSync(path.join(outputDirectory,'ui_'+viewport.name+'.png'),Buffer.from(screenshot.data,'base64'));
  }
  await command('Emulation.setEmulatedMedia',{media:'print'},reportSession);
  const printState=await command('Runtime.evaluate',{expression:"getComputedStyle(document.querySelector('.report-nav')).display==='none' && getComputedStyle(document.body).backgroundColor==='rgb(255, 255, 255)'",returnByValue:true},reportSession);
  observations.reportPrintStyles=printState.result.value;
  if (!observations.reportPrintStyles) throw new Error('Report print styles failed');
  await command('Target.closeTarget',{targetId:reportTarget.targetId});
  await execute("switchView('analysis'); document.getElementById('narrative-form').parentElement.open=true; document.getElementById('narrative-description').value='Question: A hypothetical question\\nAnalysis: A feature prediction analysis\\nMethods: Classification\\nResult: A hypothetical result\\nClaim: Features predict labels'; document.getElementById('narrative-form').requestSubmit();");
  await until("state.narrative !== null && !state.busy");
  await execute("document.getElementById('use-narrative').click()");
  observations.narrative = await evaluate("({claim:document.getElementById('analysis-form').elements.namedItem('claim').value,category:document.getElementById('analysis-form').elements.namedItem('claim_category').value,support:document.getElementById('analysis-form').elements.namedItem('computational_support').value})");
  if (observations.narrative.category || observations.narrative.support) throw new Error('Narrative categories were inferred without confirmation');
  await execute("document.getElementById('additional-claims').open=true; const claimForm=document.getElementById('claim-form'); claimForm.elements.namedItem('statement').value='A second hypothetical prediction claim'; claimForm.elements.namedItem('category').value='PREDICTIVE'; claimForm.elements.namedItem('computational_support').value='PREDICTIVE'; claimForm.requestSubmit();");
  await until("state.project.claims.length === 2 && !state.busy");
  observations.claims = await evaluate("({claims:state.project.claims.length,profiles:state.profiles.length,controlsByClaim:state.project.claims.map(claim=>state.project.controls.filter(control=>control.claim_tested===claim.claim_id).length)})");
  if (observations.claims.profiles !== 2 || observations.claims.controlsByClaim.some(count=>count<2)) throw new Error('Additional claim binding failed');
  observations.claimFilter=await execute(`
    const before=JSON.stringify(state.project), filter=document.getElementById('control-claim-filter'), claim=state.project.claims[1];
    filter.value=claim.claim_id; filter.dispatchEvent(new Event('change')); switchView('controls');
    const cards=[...document.querySelectorAll('.control-card')], expected=state.project.controls.filter(control=>control.claim_tested===claim.claim_id);
    const selected=cards.length===expected.length && cards.every(card=>card.textContent.includes(claim.statement));
    const classFilter=document.getElementById('control-class-filter'); classFilter.value='NEGATIVE'; classFilter.dispatchEvent(new Event('change'));
    const combined=document.querySelectorAll('.control-card').length===expected.filter(control=>control.control_class==='NEGATIVE').length;
    classFilter.value=''; classFilter.dispatchEvent(new Event('change'));
    return {selected,combined,unchanged:before===JSON.stringify(state.project),visible:!document.getElementById('claim-filter-label').hidden};
  `);
  if (!Object.values(observations.claimFilter).every(Boolean)) throw new Error('Claim and class filtering broke scientific bindings');
  observations.multiClaimLayout=[];
  for (const width of [375,430,768,1024,1440]) {
    await setViewport({width,height:1100});
    const layout=await evaluate("({width:innerWidth,document:document.documentElement.scrollWidth})");
    if (layout.document>width) throw new Error('Multi-claim toolbar overflow');
    observations.multiClaimLayout.push(layout);
  }
  await capture('claims');
  await execute("document.getElementById('control-claim-filter').value=''; renderControlCards()");
  observations.recordBindings=await execute(`
    const controls=state.project.controls;
    const results=[...document.querySelectorAll('.result-panel')].every(panel=>{const control=controls.find(item=>item.control_id===panel.dataset.controlId); return panel.querySelector('h3').textContent===control.control_name && panel.textContent.includes(state.project.claims.find(claim=>claim.claim_id===control.claim_tested).statement) && panel.textContent.includes('Execution specification');});
    const audits=[...document.querySelectorAll('.audit-panel')].every(panel=>panel.textContent.includes(state.project.claims.find(claim=>claim.claim_id===panel.dataset.claimId).statement));
    return {results,audits,resultCount:document.querySelectorAll('.result-panel').length===state.project.results.length,auditCount:document.querySelectorAll('.audit-panel').length===state.project.audits.length};
  `);
  if (!Object.values(observations.recordBindings).every(Boolean)) throw new Error('Result or audit view hid its scientific target');
  await execute("document.getElementById('add-control').click(); const candidateForm=document.getElementById('candidate-form'); for(const name of ['name','rationale','expected_behavior','failure_interpretation','priority_rationale','limitations']) candidateForm.elements.namedItem(name).value='Hypothetical researcher specification for local UI testing'; candidateForm.requestSubmit();");
  await until("state.project.candidates.length === 1 && !state.busy");
  const candidateId = await evaluate("state.project.candidates[0].control_id");
  await execute("editCandidate(state.project.candidates[0]); document.getElementById('candidate-form').elements.namedItem('expected_behavior').value='Revised hypothetical expected behavior'; document.getElementById('candidate-form').requestSubmit();");
  await until("state.project.candidates[0].expected_behavior.startsWith('Revised') && !state.busy");
  observations.candidate = await evaluate("({status:state.project.candidates[0].evidence_status,id:state.project.candidates[0].control_id,revisionRecorded:state.project.provenance.some(item=>item.warnings.some(warning=>warning.startsWith('Superseded candidate snapshot')))})");
  if (observations.candidate.status !== 'UNVERIFIED' || observations.candidate.id !== candidateId || !observations.candidate.revisionRecorded) throw new Error('Candidate edit promoted or replaced the specification');
  observations.candidateDraftProtection=await execute("const field=document.getElementById('candidate-form').elements.namedItem('expected_behavior'), original=field.value, prior=window.confirm; field.value='Synthetic unrecorded candidate edit'; field.dispatchEvent(new Event('input',{bubbles:true})); window.confirm=()=>false; editCandidate(); const retained=field.value==='Synthetic unrecorded candidate edit' && document.getElementById('candidate-form').elements.namedItem('control_id').value===state.project.candidates[0].control_id; window.confirm=prior; field.value=original; field.dispatchEvent(new Event('input',{bubbles:true})); return {retained,reverted:!state.drafts.has('candidate-form')};");
  if (!Object.values(observations.candidateDraftProtection).every(Boolean)) throw new Error('Candidate switching discarded a draft');
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
  observations.evaluationSnapshotProtection = await execute(`
    const original=structuredClone(state.evaluationBundle), oldHash=state.evaluation.bundle_sha256;
    const hashVisible=document.getElementById('evaluation-result').textContent.includes(oldHash);
    const changed=structuredClone(original); changed.dataset.dataset_id='changed.synthetic.fixture';
    await loadAnnotationBundle(changed);
    const replacementCleared=state.evaluation===null && document.getElementById('export-evaluation').disabled && !document.querySelector('.metric-panel');
    document.getElementById('evaluation-form').requestSubmit();
    return {hashVisible,replacementCleared,oldHash};
  `);
  await until("state.evaluation !== null && !state.busy");
  observations.evaluationSnapshotProtection.newHash=await evaluate("state.evaluation.bundle_sha256!=="+JSON.stringify(observations.evaluationSnapshotProtection.oldHash)+" && state.evaluation.bundle_sha256===state.annotationHash && state.evaluation.dataset_id==='changed.synthetic.fixture'");
  delete observations.evaluationSnapshotProtection.oldHash;
  observations.evaluationSnapshotProtection.partitionCleared=await execute("const selector=document.getElementById('evaluation-partition'); selector.value='DEVELOPMENT'; selector.dispatchEvent(new Event('change',{bubbles:true})); return state.evaluation===null && document.getElementById('export-evaluation').disabled && !document.querySelector('.metric-panel');");
  if (!Object.values(observations.evaluationSnapshotProtection).every(Boolean)) throw new Error('Evaluation metrics remained available for a different bundle or partition');
  await execute("document.getElementById('evaluation-partition').value=''; await loadAnnotationBundle("+evaluationBundle+"); document.getElementById('evaluation-form').requestSubmit();");
  await until("state.evaluation !== null && !state.busy");
  await execute("document.getElementById('open-annotations').click()");
  await until("document.getElementById('annotation-panel').open && !state.busy");
  observations.annotations = await evaluate("({origin:document.getElementById('annotation-origin').value,reviewer:document.getElementById('annotation-reviewer').value,attested:document.getElementById('annotation-attestation').checked,unknown:[...document.querySelectorAll('#annotation-controls select')].every(item=>item.value===''),matchesDisabled:[...document.querySelectorAll('#annotation-controls input')].every(item=>item.disabled),savedOrigin:state.evaluationBundle.judgment_origin})");
  if (observations.annotations.origin || observations.annotations.reviewer || observations.annotations.attested || !observations.annotations.unknown || !observations.annotations.matchesDisabled || observations.annotations.savedOrigin!=='UNASSESSED') throw new Error('Annotation workbench inferred a human judgment');
  observations.annotationDraftProtection=await execute("const select=document.getElementById('ann-appropriate-0'); select.value='true'; select.dispatchEvent(new Event('change',{bubbles:true})); const prior=window.confirm; window.confirm=()=>false; const accepted=await loadAnnotationBundle(state.evaluationBundle); window.confirm=prior; const retained=accepted===false && select.value==='true' && state.revisions.length===0 && state.evaluationBundle.judgment_origin==='UNASSESSED'; select.value=''; select.dispatchEvent(new Event('change',{bubbles:true})); return retained;");
  if (!observations.annotationDraftProtection) throw new Error('Unrecorded judgment inputs were replaced');
  observations.judgmentCaseProtection=await execute(`
    const selector=document.getElementById('annotation-case'), first=selector.value, second=selector.options[1].value;
    selector.value=second; selector.dispatchEvent(new Event('change',{bubbles:true}));
    const navigationOnly=!state.drafts.has('annotation-form');
    document.getElementById('ann-appropriate-0').value='true'; document.getElementById('ann-appropriate-0').dispatchEvent(new Event('change',{bubbles:true}));
    selector.value=first; selector.dispatchEvent(new Event('change',{bubbles:true}));
    const active=document.getElementById('ann-appropriate-0'); active.value='true'; active.dispatchEvent(new Event('change',{bubbles:true})); active.value=''; active.dispatchEvent(new Event('change',{bubbles:true}));
    const hiddenCaseProtected=state.drafts.has('annotation-form') && state.annotationDraft.judgments.some(item=>item.case_id===second && item.appropriate===true);
    selector.value=second; selector.dispatchEvent(new Event('change',{bubbles:true}));
    document.getElementById('ann-appropriate-0').value=''; document.getElementById('ann-appropriate-0').dispatchEvent(new Event('change',{bubbles:true}));
    selector.value=first; selector.dispatchEvent(new Event('change',{bubbles:true}));
    return {navigationOnly,hiddenCaseProtected,reverted:!state.drafts.has('annotation-form'),unrecorded:state.evaluationBundle.judgment_origin==='UNASSESSED' && state.revisions.length===0};
  `);
  if (!Object.values(observations.judgmentCaseProtection).every(Boolean)) throw new Error('Judgment edit protection ignored a hidden case or counted case navigation as an edit');
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
  observations.sourceReviewDraftProtection=await execute("const field=document.getElementById('statement-0-source'); field.value='Synthetic unrecorded source text'; field.dispatchEvent(new Event('input',{bubbles:true})); const control=state.reviewTemplate.control_id, prior=window.confirm; window.confirm=()=>false; await openReview(state.project.controls[0].control_id); window.confirm=prior; return field.value==='Synthetic unrecorded source text' && state.reviewTemplate.control_id===control && document.getElementById('review-control').value===control;");
  if (!observations.sourceReviewDraftProtection) throw new Error('Unrecorded source-review inputs were replaced');
  const replacementProject=fs.readFileSync('examples/microscopy_ml.project.json','utf8');
  await execute(`window.qaOriginalProject=JSON.stringify(state.project); window.qaOriginalConfirm=window.confirm; window.confirm=()=>false; const importFile=new DataTransfer(); importFile.items.add(new File([${JSON.stringify(replacementProject)}],'hypothetical.json',{type:'application/json'})); document.getElementById('project-file').files=importFile.files; document.getElementById('project-file').dispatchEvent(new Event('change'));`);
  await until("document.getElementById('status').textContent==='Kept the current workspace.' && !state.busy");
  observations.replacementCancelled=await evaluate("JSON.stringify(state.project)===window.qaOriginalProject && state.evaluationBundle!==null && document.getElementById('statement-0-source').value==='Synthetic unrecorded source text'");
  if (!observations.replacementCancelled) throw new Error('Cancelled import lost recorded or draft work');
  await execute(`window.confirm=()=>true; const importFile2=new DataTransfer(); importFile2.items.add(new File([${JSON.stringify(replacementProject)}],'hypothetical.json',{type:'application/json'})); document.getElementById('project-file').files=importFile2.files; document.getElementById('project-file').dispatchEvent(new Event('change'));`);
  await until("state.project.manifest.project_id==="+JSON.stringify(JSON.parse(replacementProject).manifest.project_id)+" && !state.busy");
  observations.replacementCoherence=await evaluate("({formMatches:document.getElementById('analysis-form').elements.namedItem('question').value===state.project.analysis.scientific_question,oldEvaluationCleared:state.evaluationBundle===null && state.evaluation===null,oldReviewCleared:state.reviewTemplate===null && document.getElementById('statement-reviews').children.length===0,oldLedgerCleared:state.audit.length===0,oldInputCleared:state.inputSummary===null && document.getElementById('numeric-file').files.length===0,draftsCleared:state.drafts.size===0})");
  await execute('window.confirm=window.qaOriginalConfirm; delete window.qaOriginalConfirm; delete window.qaOriginalProject;');
  if (!Object.values(observations.replacementCoherence).every(Boolean)) throw new Error('Imported workspace retained stale project state');
  await execute("switchView('analysis'); const input=document.getElementById('analysis-form').elements.namedItem('question'); window.qaInputBefore=input.value; input.focus(); void action(()=>new Promise(resolve=>{window.qaReleaseOperation=resolve;}));");
  const pendingLocked=await evaluate("state.busy && hasUnsavedWork() && [...document.querySelectorAll('form, .file-label')].every(element=>element.inert)");
  await command('Input.insertText',{text:'Synthetic concurrent input must not replace the pending form'});
  const inputRetained=await evaluate("document.getElementById('analysis-form').elements.namedItem('question').value===window.qaInputBefore");
  await execute("window.qaReleaseOperation(); delete window.qaReleaseOperation; delete window.qaInputBefore;");
  await until('!state.busy');
  const completedUnlocked=await evaluate("[...document.querySelectorAll('form, .file-label')].every(element=>!element.inert)");
  const failedUnlocked=await execute("await action(async()=>{throw new Error('Synthetic operation failure');}); return !state.busy && [...document.querySelectorAll('form, .file-label')].every(element=>!element.inert);");
  observations.pendingInputProtection={pendingLocked,inputRetained,completedUnlocked,failedUnlocked};
  if (!Object.values(observations.pendingInputProtection).every(Boolean)) throw new Error('Pending or failed operations left editable snapshots or locked inputs');
  observations.sessionRecovery=await execute(`
    const snapshot=JSON.stringify(state.project), actualFetch=window.fetch; let posts=0, rejected=false;
    state.token='stale.synthetic.token'; window.fetch=(url,options)=>{if(options?.method==='POST')posts++;return actualFetch(url,options);};
    try { await api('/api/parse-json',{content:'{"fixture":1}'}); } catch(error) { rejected=error.message.includes('session was renewed'); } finally { window.fetch=actualFetch; }
    const recovered=(await api('/api/parse-json',{content:'{"fixture":1}'})).value.fixture===1;
    return {rejected,noAutomaticRetry:posts===1,recovered,projectRetained:JSON.stringify(state.project)===snapshot};
  `);
  if (!Object.values(observations.sessionRecovery).every(Boolean)) throw new Error('Session recovery lost workspace data or automatically repeated an operation');
  observations.interruptedRequest=await execute(`
    const snapshot=JSON.stringify(state.project), actualFetch=window.fetch; let calls=0, redacted=false, uncertainty=false;
    window.fetch=async()=>{calls++;throw new DOMException('private_sentinel','AbortError');};
    try { await api('/api/model/run',{}); } catch(error) { redacted=!error.message.includes('private_sentinel'); uncertainty=error.message.includes('may already have been transmitted'); } finally { window.fetch=actualFetch; }
    return {redacted,uncertainty,noAutomaticRetry:calls===1,projectRetained:JSON.stringify(state.project)===snapshot};
  `);
  if (!Object.values(observations.interruptedRequest).every(Boolean)) throw new Error('Interrupted request was repeated or misrepresented');
  observations.emptyReplacementClears=await execute("const prior=window.confirm; window.confirm=()=>true; document.getElementById('request-preview').textContent='Synthetic previous request preview'; document.getElementById('model-key').value='Synthetic previous credential'; document.getElementById('new-workspace').click(); window.confirm=prior; return {project:state.project===null,ledger:document.getElementById('ledger').textContent==='',preview:document.getElementById('request-preview').textContent==='',credential:document.getElementById('model-key').value==='',zeroCounts:[...document.querySelectorAll('.metric-value')].every(item=>item.textContent==='0'),unrecorded:!hasUnsavedWork()};");
  if (!Object.values(observations.emptyReplacementClears).every(Boolean)) throw new Error('Empty workspace retained prior project details');
  observations.run_at = new Date().toISOString();
  observations.personalProjectAttributionOmitted = privateAttributionSourceCheck;
  observations.scope = 'Local reliability-phase checks with an explicitly selected headless QA profile. Responsive workspace, actual record counts, search and combined claim/class filters, scientific result and audit bindings, keyboard tabs, mobile focus boundaries, file menus, reduced motion, text-only rendering, unsaved input protection and reversion, prepared downloads, cancelled and coherent project replacement, complete workspace reset, candidate, source and multi-case annotation draft protection, programmatic field tracking, procedure-specific fields, exact-byte UTF-8/BOM input inspection, reference and paired execution, explicit bootstrap coverage/seed recording, linked responsive reports and print styles, description drafting, candidate editing, multi-claim, unassessed evaluation, blank judgment workbench, visible review headings, and review archive roundtrip. Added actual evaluation snapshot hashes and bundle/partition invalidation, pending-input locking and failure recovery, stale-session renewal without automatic replay, and a mocked interrupted hosted-request response. All computations and edited inputs were hypothetical software fixtures. Recorded public identity metadata was used only to display the source-review form; no human source review or benchmark judgment was submitted, and no external page request was observed. This is browser integration coverage, not a screen-reader, full accessibility, print-pagination, or scientific validation.';
  if (externalRequests.length) throw new Error('UI checks observed an unexpected nonlocal page request');
  fs.writeFileSync(path.join(outputDirectory,'ui_checks.json'),JSON.stringify(observations,null,2)+'\n');
  console.log(JSON.stringify(observations,null,2));
  await command('Browser.close'); socket.close();
})().catch(error=>{console.error(error.message);process.exit(1);});
