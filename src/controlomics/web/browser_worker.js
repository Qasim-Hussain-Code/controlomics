// Dedicated worker that hosts Python for the static workspace. It loads Pyodide and
// its packages from this site, installs the Controlomics wheel after checking its
// SHA-256 against the build manifest, and answers one action at a time.
import { loadPyodide } from "./pyodide/pyodide.mjs";

const base = new URL("./", import.meta.url);
const UNEXPECTED = {status: 500, json: {error: "Local operation failed unexpectedly. Private details are omitted; retry manually."}};
let runtime = null;

async function sha256(buffer) {
  const digest = await crypto.subtle.digest("SHA-256", buffer);
  return [...new Uint8Array(digest)].map(byte => byte.toString(16).padStart(2, "0")).join("");
}

try {
  // Controlomics never suspends WebAssembly, and Pyodide's JSPI path made start-up
  // more than twenty times slower in Chrome. Hiding JSPI in this worker only keeps
  // Pyodide on its ordinary path; the page and other workers are unaffected.
  delete WebAssembly.Suspending;
  delete WebAssembly.promising;
  const manifest = await (await fetch(new URL("browser_manifest.json", base), {cache: "no-cache"})).json();
  const python = await loadPyodide({indexURL: new URL("pyodide/", base).href, stdout: () => {}, stderr: () => {}});
  await python.loadPackage(manifest.packages, {messageCallback: () => {}, errorCallback: () => {}});
  const wheel = await (await fetch(new URL(manifest.wheel.file, base), {cache: "no-cache"})).arrayBuffer();
  if (await sha256(wheel) !== manifest.wheel.sha256) throw new Error("wheel digest mismatch");
  python.unpackArchive(wheel, "wheel");
  runtime = python.pyimport("controlomics.browser");
  runtime.install();
  postMessage({type: "ready"});
} catch {
  postMessage({type: "failed"});
}

onmessage = ({data}) => {
  let reply;
  try { reply = runtime.dispatch(data.path, data.body, data.outcomes || "{}"); }
  catch { reply = JSON.stringify(UNEXPECTED); }
  postMessage({id: data.id, reply});
};
