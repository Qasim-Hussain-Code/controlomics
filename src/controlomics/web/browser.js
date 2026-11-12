"use strict";
// In-browser runtime for the static Controlomics workspace. Interface requests to
// /api/ run in a dedicated worker that hosts Python with Pyodide. Nothing is sent
// to a first-party server; the page and its Python both run in this browser.
// An approved literature or model request is checked in Python first, then sent
// by this page exactly as approved, and its outcome is returned to Python.
(() => {
  // The local server bounds the fixed runner at 35 seconds; two more cover package preparation.
  const EXECUTION_LIMIT_MS = 37000;
  const TRANSPORT_TIMEOUT_MS = 20000;
  const SLOW_START_MS = 45000;
  const START_RETRIES = 2;
  const MAX_RESPONSE_BYTES = 2 * 1024 * 1024;
  const TIMEOUT_REPLY = {status: 400, json: {error: "Local execution exceeded its time limit. Reduce the workload or use a dispatched execution package. No result was imported.", code: "LOCAL_EXECUTION_TIMEOUT"}};
  const UNEXPECTED_REPLY = {status: 500, json: {error: "Local operation failed unexpectedly. Private details are omitted; retry manually."}};
  const nativeFetch = globalThis.fetch.bind(globalThis);
  const pending = new Map();
  let worker, ready, nextId = 1, note = null, noteState = "loading", noteText = "Preparing the in-browser Python runtime. The first visit downloads about 15 MB.";

  function showStatus(text, state) {
    noteText = text;
    noteState = state;
    if (!note) return;
    note.textContent = text;
    note.dataset.state = state;
  }

  // One start-up cycle; `ready` settles once for the cycle, after retries if a download fails.
  function start() {
    let settle;
    ready = new Promise((resolve, reject) => { settle = {resolve, reject}; });
    ready.catch(() => {});
    launch(settle, 0);
  }

  function launch(settle, attempt) {
    showStatus(attempt ? "Retrying the in-browser Python runtime after an interrupted download. No research input has been sent." : "Preparing the in-browser Python runtime. The first visit downloads about 15 MB.", "loading");
    worker = new Worker(new URL("browser_worker.js", document.baseURI), {type: "module", name: "controlomics-python"});
    const current = worker;
    let started = false;
    setTimeout(() => {
      if (worker === current && noteState === "loading") showStatus("Still preparing the in-browser Python runtime. On a slow connection the first visit can take several minutes. No research input has been sent.", "loading");
    }, SLOW_START_MS);
    const failed = () => {
      if (worker !== current) return;
      if (attempt < START_RETRIES) { current.terminate(); setTimeout(() => launch(settle, attempt + 1), 2000 * (attempt + 1)); return; }
      showStatus("The in-browser Python runtime could not start. No research input was sent. Reload the page to retry.", "failed");
      settle.reject(new Error("runtime unavailable"));
    };
    worker.onmessage = ({data}) => {
      if (data.type === "ready") { started = true; showStatus("Running in this browser. Research records are not uploaded.", "ready"); settle.resolve(); return; }
      if (data.type === "failed") { failed(); return; }
      const job = pending.get(data.id);
      if (!job) return;
      pending.delete(data.id);
      clearTimeout(job.timer);
      job.resolve(data.reply);
    };
    worker.onerror = () => {
      if (!started) { failed(); return; }
      showStatus("The in-browser Python runtime stopped. No further research input was processed. Reload the page to retry.", "failed");
      for (const job of pending.values()) { clearTimeout(job.timer); job.reject(new TypeError("runtime stopped")); }
      pending.clear();
    };
  }

  function restart() {
    worker.terminate();
    for (const job of pending.values()) { clearTimeout(job.timer); job.reject(new TypeError("runtime restarted")); }
    pending.clear();
    start();
  }

  // One request to the Python worker; resolves with its JSON envelope.
  async function ask(path, body, outcomes, signal) {
    await ready;
    const text = await new Promise((resolve, reject) => {
      const id = nextId++;
      const job = {resolve, reject, timer: null};
      if (path === "/api/execute") {
        job.timer = setTimeout(() => {
          if (!pending.delete(id)) return;
          restart();
          resolve(JSON.stringify(TIMEOUT_REPLY));
        }, EXECUTION_LIMIT_MS);
      }
      signal?.addEventListener("abort", () => {
        if (!pending.delete(id)) return;
        clearTimeout(job.timer);
        restart();
        reject(signal.reason ?? new DOMException("The operation was aborted.", "AbortError"));
      }, {once: true});
      pending.set(id, job);
      worker.postMessage({id, path, body, outcomes});
    });
    return JSON.parse(text);
  }

  function base64(bytes) {
    let text = "";
    for (let offset = 0; offset < bytes.length; offset += 0x8000) text += String.fromCharCode(...bytes.subarray(offset, offset + 0x8000));
    return btoa(text);
  }

  // Sends one approved request exactly as Python prepared it and reports how far it got.
  async function transmit(request, body, signal) {
    if (typeof request.url !== "string" || !request.url.startsWith("https://")) return {phase: "NOT_STARTED", ok: false};
    const headers = {"Accept": "application/json"};
    if (request.body !== null) headers["Content-Type"] = "application/json";
    if (request.credential) {
      let key = null;
      try { key = JSON.parse(body).api_key; } catch {}
      if (typeof key !== "string" || !key || /[\r\n]/.test(key)) return {phase: "NOT_STARTED", ok: false};
      headers["Authorization"] = "Bearer " + key;
    }
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), TRANSPORT_TIMEOUT_MS);
    const forward = () => controller.abort();
    signal?.addEventListener("abort", forward, {once: true});
    let phase = "ATTEMPTED";
    try {
      const response = await nativeFetch(request.url, {method: request.method, headers, body: request.body ?? undefined,
        redirect: "error", credentials: "omit", referrerPolicy: "no-referrer", cache: "no-store", mode: "cors", signal: controller.signal});
      phase = "COMPLETED";
      if (!response.ok || !response.body) { response.body?.cancel(); return {phase, ok: false}; }
      const reader = response.body.getReader(), chunks = [];
      let size = 0;
      for (;;) {
        const {done, value} = await reader.read();
        if (done) break;
        size += value.byteLength;
        if (size > MAX_RESPONSE_BYTES) { reader.cancel(); return {phase, ok: false}; }
        chunks.push(value);
      }
      const bytes = new Uint8Array(size);
      let offset = 0;
      for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength; }
      return {phase, ok: true, body_base64: base64(bytes)};
    } catch {
      return {phase, ok: false};
    } finally {
      clearTimeout(timer);
      signal?.removeEventListener("abort", forward);
    }
  }

  async function run(path, body, signal) {
    let reply = await ask(path, body, "{}", signal);
    if (!reply.fetch) return reply;
    const request = reply.fetch;
    const outcome = await transmit(request, body, signal);
    if (signal?.aborted) throw signal.reason ?? new DOMException("The operation was aborted.", "AbortError");
    reply = await ask(path, body, JSON.stringify({[request.request_sha256]: outcome}), signal);
    return reply.fetch ? UNEXPECTED_REPLY : reply;
  }

  function token() {
    const bytes = crypto.getRandomValues(new Uint8Array(32));
    return base64(bytes).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  }

  function respond(reply) {
    const headers = {"Cache-Control": "no-store"};
    if (typeof reply.body_base64 === "string") {
      const bytes = Uint8Array.from(atob(reply.body_base64), character => character.charCodeAt(0));
      return new Response(bytes, {status: reply.status, headers: {...headers, "Content-Type": reply.content_type, "Content-Disposition": "attachment; filename=\"" + reply.filename + "\""}});
    }
    return new Response(JSON.stringify(reply.json), {status: reply.status, headers: {...headers, "Content-Type": "application/json"}});
  }

  globalThis.fetch = async (input, init = {}) => {
    if (typeof input !== "string" || !input.startsWith("/api/")) return nativeFetch(input, init);
    if (init.signal?.aborted) throw init.signal.reason;
    if (input === "/api/session") {
      return new Response(JSON.stringify({token: token(), deployment: {mode: "BROWSER"}}), {status: 200, headers: {"Content-Type": "application/json", "Cache-Control": "no-store"}});
    }
    if (String(init.method || "GET").toUpperCase() !== "POST" || typeof init.body !== "string") {
      return new Response(JSON.stringify({error: "Resource not found."}), {status: 404, headers: {"Content-Type": "application/json"}});
    }
    return respond(await run(input, init.body, init.signal));
  };
  globalThis.ControlomicsBrowser = Object.freeze({active: true});

  document.addEventListener("DOMContentLoaded", () => {
    note = document.createElement("p");
    note.id = "browser-runtime";
    note.className = "browser-runtime";
    note.setAttribute("role", "status");
    note.setAttribute("aria-live", "polite");
    note.textContent = noteText;
    note.dataset.state = noteState;
    const status = document.getElementById("status");
    if (status) status.before(note); else document.body.prepend(note);
  });
  start();
})();
