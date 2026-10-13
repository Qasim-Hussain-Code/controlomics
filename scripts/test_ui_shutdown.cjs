// Controlled lifecycle tests only. No browser, network or scientific claims.
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {randomUUID} = require('node:crypto');
const {observeBrowserShutdown,retainShutdownObservations,processSnapshot} = require('./check_ui_shutdown.cjs');

const evidenceRoot=path.resolve(process.env.CONTROLOMICS_SHUTDOWN_TEST_DIR || 'local_projects/ui_shutdown_tests/'+randomUUID());
fs.mkdirSync(evidenceRoot,{recursive:true});
const live={present:true,hasExited:false,identity:'original'};
function scenario(overrides={}) {
  let time=0, closeCalls=0, connectionCloses=0;
  return {
    options:{requestClose:async()=>{closeCalls++;},closeConnection:()=>{connectionCloses++;},
      checkEndpoint:async()=>({closed:true}),checkProcess:async()=>time===0?live:{present:false,hasExited:true,identity:null},
      now:()=>time,pause:async ms=>{time+=ms;},...overrides},
    advance:ms=>{time+=ms;},time:()=>time,closeCalls:()=>closeCalls,connectionCloses:()=>connectionCloses,
  };
}
function folder(name) { const destination=path.join(evidenceRoot,name); fs.mkdirSync(destination); return destination; }
const functional={fixture:true,scope:'Synthetic shutdown lifecycle only.',functional_checks:{complete:true},source_hashes:{fixture:'retained'},screenshot_hashes:{synthetic_capture:'retained'}};

test('checkpoint exists before close; successful final record retains functional evidence',async()=>{
  const destination=folder('success'), setup=scenario();
  let processCalls=0;
  setup.options.checkProcess=async()=>++processCalls===1?live:{present:false,hasExited:true,identity:null};
  setup.options.requestClose=async()=>{
    const saved=JSON.parse(fs.readFileSync(path.join(destination,'ui_checks_before_shutdown.json'),'utf8'));
    assert.deepEqual(saved.source_hashes,functional.source_hashes);
    assert.equal(saved.browserShutdown.status,'NOT_STARTED');
    assert.equal(saved.browserShutdown.processExitObserved,false);
  };
  const record=await retainShutdownObservations({observations:functional,outputDirectory:destination,...setup.options});
  assert.equal(record.completion,'COMPLETE');
  assert.equal(record.browserShutdown.status,'PASS');
  assert.equal(record.browserShutdown.processExitObserved,true);
  assert.deepEqual(JSON.parse(fs.readFileSync(path.join(destination,'ui_checks.json'),'utf8')),record);
});

test('exit after 70 seconds fails the unchanged 40-second bound and retains completed observations',async()=>{
  const destination=folder('slow_exit'), setup=scenario();
  setup.options.checkProcess=async()=>setup.time()<70000?live:{present:false,hasExited:true,identity:null};
  const result=await retainShutdownObservations({observations:functional,outputDirectory:destination,...setup.options});
  assert.equal(setup.time(),40000);
  assert.equal(result.browserShutdown.processTimeoutMs,40000);
  assert.equal(result.browserShutdown.status,'TIMED_OUT');
  assert.equal(result.browserShutdown.failureStage,'PROCESS_EXIT');
  assert.equal(result.browserShutdown.debuggingEndpointClosed,true);
  assert.equal(result.browserShutdown.processExitObserved,false);
  assert.equal(result.completion,'FUNCTIONAL_CHECKS_COMPLETE_SHUTDOWN_UNCONFIRMED');
  assert.deepEqual(JSON.parse(fs.readFileSync(path.join(destination,'ui_checks.json'),'utf8')).functional_checks,functional.functional_checks);
  assert.ok(fs.existsSync(path.join(destination,'ui_checks_before_shutdown.json')));
});

test('an exited Windows process can remain listed without being mistaken for running',async()=>{
  const setup=scenario(); let calls=0;
  setup.options.checkProcess=async()=>++calls===1?live:{present:true,hasExited:true,identity:'original'};
  const result=await observeBrowserShutdown(setup.options);
  assert.equal(result.status,'PASS'); assert.equal(result.processExitObserved,true);
  assert.match(result.processObservation,/exited process state/);
});

test('PID reuse establishes departure of the original identity and does not stop another process',async()=>{
  const setup=scenario(); let calls=0;
  setup.options.checkProcess=async()=>++calls===1?live:{present:true,hasExited:false,identity:'replacement'};
  const result=await observeBrowserShutdown(setup.options);
  assert.equal(result.processIdentityChanged,true); assert.equal(result.processExitObserved,true);
  assert.equal(result.status,'PASS'); assert.equal(setup.connectionCloses(),1);
});

test('endpoint timeout is unconfirmed and never substitutes for process exit',async()=>{
  const destination=folder('endpoint_timeout'), setup=scenario({checkEndpoint:async()=>({closed:false,status:'NO_REFUSAL_OBSERVED'})});
  const result=await retainShutdownObservations({observations:functional,outputDirectory:destination,...setup.options});
  assert.equal(result.browserShutdown.endpointAttempts,20);
  assert.equal(result.browserShutdown.status,'TIMED_OUT');
  assert.equal(result.browserShutdown.failureStage,'DEBUGGING_ENDPOINT');
  assert.equal(result.browserShutdown.processExitObserved,false);
  assert.equal(result.browserShutdown.debuggingEndpointClosed,false);
});

test('close-request failure retains a final ERROR record and the earlier checkpoint',async()=>{
  const destination=folder('close_error'), setup=scenario({requestClose:async()=>{throw new Error('synthetic failure');}});
  const result=await retainShutdownObservations({observations:functional,outputDirectory:destination,...setup.options});
  assert.equal(result.browserShutdown.status,'ERROR'); assert.equal(result.browserShutdown.failureStage,'CLOSE_REQUEST');
  assert.equal(result.browserShutdown.processExitObserved,false);
  assert.equal(setup.connectionCloses(),1);
  assert.ok(fs.existsSync(path.join(destination,'ui_checks.json')));
});

test('process-observation errors retain evidence without claiming exit',async()=>{
  const destination=folder('process_error'), setup=scenario(); let calls=0;
  setup.options.checkProcess=async()=>{if(++calls===1)return live;throw new Error('synthetic permissions failure');};
  const result=await retainShutdownObservations({observations:functional,outputDirectory:destination,...setup.options});
  assert.equal(result.browserShutdown.status,'ERROR'); assert.equal(result.browserShutdown.failureStage,'PROCESS_OBSERVATION');
  assert.equal(result.browserShutdown.processExitObserved,false);
});

test('missing initial process identity still closes the verified debug connection and remains ERROR',async()=>{
  const setup=scenario({checkProcess:async()=>{throw new Error('synthetic failure');}});
  const result=await observeBrowserShutdown(setup.options);
  assert.equal(setup.closeCalls(),1); assert.equal(setup.connectionCloses(),1);
  assert.equal(result.status,'ERROR'); assert.equal(result.failureStage,'PROCESS_IDENTITY');
  assert.equal(result.processExitObserved,false);
});

test('without a PID the result explicitly records process exit as unmeasured',async()=>{
  const setup=scenario({checkProcess:null}), result=await observeBrowserShutdown(setup.options);
  assert.equal(result.status,'ENDPOINT_CLOSED_PROCESS_NOT_MEASURED');
  assert.equal(result.processExitRequested,false); assert.equal(result.processExitObserved,false);
});

test('expired process probe is a timeout, not a successful exit or an unrelated error',async()=>{
  const setup=scenario(); let calls=0;
  setup.options.checkProcess=async()=>{if(++calls===1)return live;setup.advance(40000);throw new Error('synthetic probe timeout');};
  const result=await observeBrowserShutdown(setup.options);
  assert.equal(result.status,'TIMED_OUT'); assert.equal(result.failureStage,'PROCESS_EXIT');
  assert.equal(result.processExitObserved,false);
});

test('previous observation bytes are not replaced and no close request is submitted on checkpoint conflict',async()=>{
  const destination=folder('retained_prior'), setup=scenario();
  fs.writeFileSync(path.join(destination,'ui_checks_before_shutdown.json'),'retained prior bytes');
  await assert.rejects(()=>retainShutdownObservations({observations:functional,outputDirectory:destination,...setup.options}),{code:'EEXIST'});
  assert.equal(setup.closeCalls(),0);
  assert.equal(fs.readFileSync(path.join(destination,'ui_checks_before_shutdown.json'),'utf8'),'retained prior bytes');
});

test('current-process snapshot reports live identity without terminating or listing processes',async()=>{
  const result=await processSnapshot(process.pid,5000);
  assert.equal(result.present,true); assert.equal(result.hasExited,false);
  if(process.platform==='win32') assert.equal(typeof result.identity,'string');
});

test('invalid or textual PID values are rejected before OS command construction',async()=>{
  for(const pid of [0,-1,1.5,'1; synthetic_statement',Number.MAX_SAFE_INTEGER+1]) {
    await assert.rejects(()=>processSnapshot(pid),/valid process identifier/);
  }
});
