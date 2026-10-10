// parallel-batch.mjs — run files with N concurrent workers, append ndjson.
import { spawn } from "node:child_process";
import { readFileSync, mkdirSync, appendFileSync, existsSync } from "node:fs";
import path from "node:path";
const BASE = path.dirname(new URL(import.meta.url).pathname);
const SRC = path.resolve(BASE, "../letta-src");
const NODE = process.execPath;
const LOADER = path.join(BASE, "loader.mjs");
const ENTRY = path.join(BASE, "child-entry.mjs");
const HOME_ROOT = path.join(BASE, "homes");
const CONC = Number(process.env.CONC || "6");
const OUT = process.env.OUT || path.join(BASE, "run-results.ndjson");
const files = readFileSync(process.env.LIST, "utf8").split("\n").map(s=>s.trim()).filter(Boolean);
const ISO_MANIFEST = path.join(SRC, "scripts/isolated-unit-tests.json");
let isoEnvByPath = new Map();
try { const m = JSON.parse(readFileSync(ISO_MANIFEST, "utf8")); for (const e of m.tests) isoEnvByPath.set(path.join(SRC, e.path), e.env || {}); } catch {}
const done = new Set();
if (existsSync(OUT)) for (const l of readFileSync(OUT,"utf8").split("\n")) { try { done.add(JSON.parse(l).file); } catch{} }
const todo = files.filter(f=>!done.has(f));
console.log(`[parallel] ${todo.length} to run, concurrency ${CONC}`);
let next = 0, active = 0, finished = 0;
const started = Date.now();
function runOne(file){
  const index = next++;
  const home = path.join(HOME_ROOT, "par-" + index);
  mkdirSync(home, { recursive: true });
  const env = { ...process.env };
  delete env.LD_LIBRARY_PATH;
  env.LETTA_CODE_TELEM = "0";
  env.BUNNODE_TIMEOUT_MS = "90000";
  env.BUNNODE_TSCACHE_DIR = path.join(BASE, "tscache");
  const isoEnv = isoEnvByPath.get(file);
  if (isoEnv) Object.assign(env, isoEnv);
  env.HOME = home; env.TMPDIR = home;
  env.PATH = path.join(BASE, "bin") + path.delimiter + (env.PATH || "");
  env.GIT_CONFIG_COUNT = "1"; env.GIT_CONFIG_KEY_0 = "safe.directory"; env.GIT_CONFIG_VALUE_0 = "*";
  env.GIT_CEILING_DIRECTORIES = BASE;
  return new Promise((resolve)=>{
    const child = spawn(NODE, ["--jitless","--no-experimental-strip-types","--import",LOADER,"--no-warnings",ENTRY,file], { cwd: SRC, env, stdio: ["ignore","pipe","pipe"] });
    let stdout="", stderr="";
    child.stdout.on("data", d=>stdout+=d);
    child.stderr.on("data", d=>stderr+=d);
    const timer = setTimeout(()=>{ try{child.kill("SIGKILL");}catch{} }, 300000);
    const appendLine = (o)=>{ try{ appendFileSync(OUT, JSON.stringify(o)+"\n"); }catch{} };
    child.on("error", err=>{ clearTimeout(timer); appendLine({file, crash:true, reason:"spawn error: "+err.message}); resolve(); });
    child.on("close", (code)=>{
      clearTimeout(timer);
      const line = stdout.split("\n").find(l=>l.startsWith("BUNNODE_RESULT "));
      if (line){
        try {
          const r = JSON.parse(line.slice("BUNNODE_RESULT ".length));
          appendLine({ file, total: r.total, passed: r.passed, failed: r.failed, crash: false, exitCode: code });
        } catch(e){ appendLine({ file, crash: true, reason: "bad result json: "+e.message, exitCode: code }); }
      } else {
        appendLine({ file, crash: true, reason: "no BUNNODE_RESULT", exitCode: code, stderrTail: stderr.slice(-300) });
      }
      finished++;
      resolve();
    });
  });
}
(async()=>{
  const workers = [];
  for (let w=0; w<Math.min(CONC, todo.length); w++) workers.push(worker(w));
  async function worker(){
    while (next < todo.length){
      const f = todo[next];
      const t = Date.now();
      await runOne(f);
      process.stdout.write(`done ${f.replace(SRC+"/","")} (${((Date.now()-t)/1000).toFixed(0)}s, ${finished}/${todo.length}, ${((Date.now()-started)/1000).toFixed(0)}s elapsed)\n`);
    }
  }
  await Promise.all(workers);
  console.log(`[parallel] complete: ${finished} files in ${((Date.now()-started)/1000).toFixed(0)}s`);
})();
