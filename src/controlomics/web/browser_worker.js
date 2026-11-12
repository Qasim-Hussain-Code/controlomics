// Dedicated worker that hosts Python for the static workspace. It downloads Pyodide,
// its packages, and the Controlomics wheel from this site, checks each against the
// SHA-256 in the build manifest, and answers one action at a time.
import { loadPyodide } from "./pyodide/pyodide.mjs";

const base = new URL("./", import.meta.url);
const index = new URL("pyodide/", base);
// Starting Pyodide from files already downloaded takes seconds; this bounds a hang.
const START_LIMIT_MS = 120000;
const UNEXPECTED = {status: 500, json: {error: "Local operation failed unexpectedly. Private details are omitted; retry manually."}};
let runtime = null;

async function sha256(buffer) {
  const digest = await crypto.subtle.digest("SHA-256", buffer);
  return [...new Uint8Array(digest)].map(byte => byte.toString(16).padStart(2, "0")).join("");
}

// Pyodide does not report an interrupted WebAssembly download; it waits indefinitely.
// Downloading and checking every file here first makes such a failure visible and
// retried, and leaves the files in the browser cache for Pyodide's own requests.
async function download(url, digest) {
  for (let attempt = 0; attempt < 3; attempt++) {
    try {
      const response = await fetch(url);
      if (response.ok) {
        const buffer = await response.arrayBuffer();
        if (await sha256(buffer) === digest) return buffer;
      }
    } catch {}
    await new Promise(resolve => setTimeout(resolve, 2000 * (attempt + 1)));
  }
  throw new Error("download failed");
}

function within(promise, limit) {
  return Promise.race([promise, new Promise((_, reject) => setTimeout(() => reject(new Error("start-up timed out")), limit))]);
}

try {
  // Controlomics never suspends WebAssembly, and Pyodide's JSPI path made start-up
  // more than twenty times slower in Chrome. Hiding JSPI in this worker only keeps
  // Pyodide on its ordinary path; the page and other workers are unaffected.
  delete WebAssembly.Suspending;
  delete WebAssembly.promising;
  const manifest = await (await fetch(new URL("browser_manifest.json", base), {cache: "no-cache"})).json();
  const files = [...Object.entries(manifest.core), ...Object.entries(manifest.package_files)];
  const downloaded = Object.fromEntries(await Promise.all(files.map(async ([name, digest]) => [name, await download(new URL(name, index), digest)])));
  const wheel = await download(new URL(manifest.wheel.file, base), manifest.wheel.sha256);
  const stdLibURL = URL.createObjectURL(new Blob([downloaded["python_stdlib.zip"]], {type: "application/zip"}));
  const python = await within(loadPyodide({indexURL: index.href, packageBaseUrl: index.href, stdLibURL, stdout: () => {}, stderr: () => {}}), START_LIMIT_MS);
  URL.revokeObjectURL(stdLibURL);
  await within(python.loadPackage(manifest.packages, {messageCallback: () => {}, errorCallback: () => {}}), START_LIMIT_MS);
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
