// Optional QA lifecycle checks. Endpoint refusal and process exit are separate.
const fs = require('node:fs');
const path = require('node:path');
const {execFile} = require('node:child_process');

function writeObservation(outputDirectory, filename, observation) {
  fs.writeFileSync(path.join(outputDirectory,filename),JSON.stringify(observation,null,2)+'\n',{flag:'wx'});
}

async function processSnapshot(pid, timeout=5000) {
  if(!Number.isSafeInteger(pid) || pid<1) throw new Error('Supply a valid process identifier');
  if(process.platform!=='win32') {
    try { process.kill(pid,0); return {present:true,hasExited:false,identity:null}; }
    catch(error) {
      if(error.code==='ESRCH') return {present:false,hasExited:true,identity:null};
      throw new Error('Process observation unavailable');
    }
  }
  // Read only the supplied task-owned PID; do not list or terminate processes.
  // Dispose the handle so the observation itself cannot prolong PID retention.
  const script=`$qaProcess=$null; try { $qaProcess=[Diagnostics.Process]::GetProcessById(${pid}); $qaExited=$qaProcess.HasExited; $qaIdentity=$null; if(-not $qaExited) { $qaIdentity=$qaProcess.StartTime.ToUniversalTime().Ticks.ToString() }; [pscustomobject]@{present=$true;hasExited=$qaExited;identity=$qaIdentity} | ConvertTo-Json -Compress } catch [ArgumentException] { [pscustomobject]@{present=$false;hasExited=$true;identity=$null} | ConvertTo-Json -Compress } catch { [pscustomobject]@{error=$true} | ConvertTo-Json -Compress } finally { if($null -ne $qaProcess) { $qaProcess.Dispose() } }`;
  return new Promise((resolve,reject)=>execFile('powershell.exe',['-NoProfile','-NonInteractive','-Command',script],{encoding:'utf8',windowsHide:true,timeout},(error,stdout)=>{
    if(error) { reject(new Error('Process observation unavailable')); return; }
    try {
      const value=JSON.parse(stdout);
      if(value.error || typeof value.present!=='boolean' || typeof value.hasExited!=='boolean' || ![null,'string'].includes(value.identity===null?null:typeof value.identity)) throw new Error();
      resolve(value);
    } catch { reject(new Error('Process observation unavailable')); }
  }));
}

async function observeBrowserShutdown({requestClose,closeConnection,checkEndpoint,checkProcess=null,onCheckpoint=()=>{},now=()=>performance.now(),pause=ms=>new Promise(resolve=>setTimeout(resolve,ms)),processTimeoutMs=40000,endpointAttempts=20,pollMs=250,processProbeTimeoutMs=5000}) {
  const result={status:'NOT_STARTED',debuggingEndpointClosed:false,processExitObserved:false,
    processExitRequested:checkProcess!==null,processIdentityCaptured:false,closeRequestAccepted:false,
    processTimeoutMs,endpointAttemptsMax:endpointAttempts,pollIntervalMs:pollMs};
  onCheckpoint({...result});
  let initial=null, processObservationError=false;
  if(checkProcess) {
    try {
      initial=await checkProcess(processProbeTimeoutMs);
      if(initial.hasExited || !initial.present) processObservationError=true;
      else result.processIdentityCaptured=initial.identity!==null;
    } catch { processObservationError=true; }
  }
  result.status='CLOSING';
  try { await requestClose(); result.closeRequestAccepted=true; }
  catch {
    result.status='ERROR'; result.failureStage='CLOSE_REQUEST';
    result.processObservation='Shutdown request failed; process exit was not established.';
    try { closeConnection(); } catch { result.connectionCleanupError=true; }
    return result;
  }
  try { closeConnection(); }
  catch {
    result.status='ERROR'; result.failureStage='LOCAL_CONNECTION_CLOSE';
    result.processObservation='Local debugging connection cleanup failed; process exit was not established.';
    return result;
  }
  const endpointStart=now();
  for(let attempt=0;attempt<endpointAttempts;attempt++) {
    result.endpointAttempts=attempt+1;
    try {
      const observed=await checkEndpoint();
      result.lastEndpointObservation=observed.closed?'CONNECTION_REFUSED':observed.status;
      if(observed.closed) { result.debuggingEndpointClosed=true; break; }
    } catch { result.lastEndpointObservation='OBSERVATION_ERROR'; }
    await pause(pollMs);
  }
  result.endpointObservationMs=Math.round(now()-endpointStart);
  if(!result.debuggingEndpointClosed) {
    result.status='TIMED_OUT'; result.failureStage='DEBUGGING_ENDPOINT';
    result.processObservation='Debugging endpoint closure was not established; process exit was not inferred.';
    return result;
  }
  if(!checkProcess) {
    result.status='ENDPOINT_CLOSED_PROCESS_NOT_MEASURED';
    result.processObservation='Browser PID was not supplied; only debugging-endpoint closure was measured.';
    return result;
  }
  if(processObservationError) {
    result.status='ERROR'; result.failureStage='PROCESS_IDENTITY';
    result.processObservation='The supplied process could not be identified as running before shutdown; exit was not inferred.';
    return result;
  }
  const processStart=now();
  result.status='WAITING_FOR_PROCESS';
  while(now()-processStart<processTimeoutMs) {
    const remaining=processTimeoutMs-(now()-processStart);
    try {
      const observed=await checkProcess(Math.max(1,Math.min(processProbeTimeoutMs,remaining)));
      const changed=initial.identity!==null && observed.identity!==null && initial.identity!==observed.identity;
      if(observed.hasExited || !observed.present || changed) {
        result.processExitObserved=true;
        result.processIdentityChanged=changed;
        result.processObservation=changed?'The original process identity no longer owns the supplied PID.':observed.present?'An exited process state was observed; the PID can remain listed.':'The task-owned browser PID no longer exists.';
        break;
      }
    } catch {
      const expired=now()-processStart>=processTimeoutMs;
      result.status=expired?'TIMED_OUT':'ERROR'; result.failureStage=expired?'PROCESS_EXIT':'PROCESS_OBSERVATION';
      result.processObservation=expired?'Process exit was not observed within the recorded bound; exit was not inferred.':'Process observation was unavailable; exit was not inferred.';
      result.processObservationMs=Math.round(now()-processStart);
      return result;
    }
    await pause(Math.min(pollMs,Math.max(0,processTimeoutMs-(now()-processStart))));
  }
  result.processObservationMs=Math.round(now()-processStart);
  if(!result.processExitObserved) {
    result.status='TIMED_OUT'; result.failureStage='PROCESS_EXIT';
    result.processObservation='Process exit was not observed within the recorded bound; endpoint closure alone does not establish exit.';
  } else result.status='PASS';
  return result;
}

async function retainShutdownObservations({observations,outputDirectory,...options}) {
  const shutdown=await observeBrowserShutdown({...options,onCheckpoint:status=>{
    const checkpoint={...observations,completion:'FUNCTIONAL_CHECKS_COMPLETE_SHUTDOWN_NOT_STARTED',browserShutdown:status};
    writeObservation(outputDirectory,'ui_checks_before_shutdown.json',checkpoint);
    options.onCheckpoint?.(status);
  }});
  const final={...observations,completion:shutdown.status==='PASS'?'COMPLETE':shutdown.status==='ENDPOINT_CLOSED_PROCESS_NOT_MEASURED'?'COMPLETE_WITH_LIMITED_SHUTDOWN_OBSERVATION':'FUNCTIONAL_CHECKS_COMPLETE_SHUTDOWN_UNCONFIRMED',browserShutdown:shutdown};
  writeObservation(outputDirectory,'ui_checks.json',final);
  return final;
}

module.exports={processSnapshot,observeBrowserShutdown,retainShutdownObservations};
