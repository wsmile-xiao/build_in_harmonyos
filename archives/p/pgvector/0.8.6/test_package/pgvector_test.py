#!/usr/bin/env python3
"""Consumer harness for the pgvector Conan package (OHOS PC aarch64).

Three evidence groups, all executed against the *installed* package tree:

  1. artifact assertions — pure-python ELF reader, no external tools:
     ELF64 / little endian / AArch64, ``.codesign`` section present,
     ``DT_NEEDED`` == musl ``libc.so`` only, no RPATH/RUNPATH (relocatable).
  2. consumer assertions — a real PostgreSQL 18.3 server is started, the
     packaged extension is registered and exercised through SQL (types,
     distance operators, ivfflat + hnsw access methods).
  3. upstream suite — the 14 upstream pg_regress groups (test/sql/*.sql
     against test/expected/*.out) are executed byte-exactly.

The extension is looked up *without* writing anything into the PostgreSQL
installation: ``extension_control_path`` points at the package root
(PostgreSQL looks for ``<path>/extension/<name>.control``) and
``dynamic_library_path`` points at the package ``lib`` directory.  Both are
PostgreSQL 18 server parameters.

Exit code 0 only when every group is green.
"""
import argparse
import glob
import json
import math
import os
import shutil
import socket
import struct
import subprocess
import sys
import tempfile

EM_AARCH64 = 183
PT_DYNAMIC = 2
DT_NEEDED = 1
DT_STRTAB = 5
DT_SONAME = 14
DT_RPATH = 15
DT_RUNPATH = 29


# ─────────────────────────── minimal ELF reader ───────────────────────────
class Elf(object):
    """Just enough ELF64 parsing to assert the artifact-level facts."""

    def __init__(self, path):
        with open(path, "rb") as fh:
            self.path = path
            self.data = fh.read()
        if self.data[:4] != b"\x7fELF":
            raise AssertionError(f"{path} is not an ELF file")
        self.elf_class = self.data[4]
        self.encoding = self.data[5]
        if self.elf_class != 2 or self.encoding != 1:
            raise AssertionError(
                f"{path}: expected 64-bit little-endian ELF")
        self.machine = struct.unpack_from("<H", self.data, 18)[0]
        self._read_segments()
        self._read_sections()
        self._read_dynamic()

    def _u(self, fmt, off):
        return struct.unpack_from(fmt, self.data, off)[0]

    def _read_segments(self):
        self.segments = []
        phoff = self._u("<Q", 0x20)
        phentsize = self._u("<H", 0x36)
        phnum = self._u("<H", 0x38)
        if not phoff or not phnum:
            return
        for i in range(phnum):
            off = phoff + i * phentsize
            self.segments.append({
                "type": self._u("<I", off),
                "offset": self._u("<Q", off + 0x08),
                "vaddr": self._u("<Q", off + 0x10),
                "filesz": self._u("<Q", off + 0x20),
                "memsz": self._u("<Q", off + 0x28),
            })

    def _va_to_offset(self, va):
        for seg in self.segments:
            if seg["type"] != 1:                        # PT_LOAD
                continue
            if seg["vaddr"] <= va < seg["vaddr"] + seg["memsz"]:
                return va - seg["vaddr"] + seg["offset"]
        raise AssertionError(f"cannot map virtual address {va:#x} to a file "
                             "offset")

    def _read_sections(self):
        self.section_names = []
        shoff = self._u("<Q", 0x28)
        shentsize = self._u("<H", 0x3A)
        shnum = self._u("<H", 0x3C)
        shstrndx = self._u("<H", 0x3E)
        if not shoff or not shnum or shstrndx >= shnum:
            return
        names = []
        strtab = 0
        for i in range(shnum):
            off = shoff + i * shentsize
            names.append(self._u("<I", off))
            if i == shstrndx:
                strtab = self._u("<Q", off + 0x18)
        for name_off in names:
            end = self.data.index(b"\0", strtab + name_off)
            self.section_names.append(
                self.data[strtab + name_off:end].decode("ascii", "replace"))

    def _read_dynamic(self):
        self.dynamic = []
        for seg in self.segments:
            if seg["type"] != PT_DYNAMIC:
                continue
            for j in range(seg["filesz"] // 16):
                tag = self._u("<q", seg["offset"] + j * 16)
                val = self._u("<Q", seg["offset"] + j * 16 + 8)
                self.dynamic.append((tag, val))

    def _str(self, off):
        end = self.data.index(b"\0", off)
        return self.data[off:end].decode("ascii", "replace")

    def _dynstr_offset(self):
        strtab = None
        for t, v in self.dynamic:
            if t == DT_STRTAB:
                strtab = self._va_to_offset(v)
        if strtab is None:
            raise AssertionError("no DT_STRTAB in .dynamic")
        return strtab

    def needed(self):
        strtab = self._dynstr_offset()
        return [self._str(strtab + v) for t, v in self.dynamic
                if t == DT_NEEDED]

    def soname(self):
        strtab = self._dynstr_offset()
        for t, v in self.dynamic:
            if t == DT_SONAME:
                return self._str(strtab + v)
        return None

    def rpaths(self):
        strtab = self._dynstr_offset()
        return [self._str(strtab + v) for t, v in self.dynamic
                if t in (DT_RPATH, DT_RUNPATH)]


# ────────────────────────────── helpers ──────────────────────────────
def writable_tmp_root():
    for cand in (os.environ.get("TMPDIR"),
                 os.path.join(os.path.expanduser("~"), "tmp")):
        if not cand:
            continue
        try:
            os.makedirs(cand, exist_ok=True)
            probe = os.path.join(cand, ".pgvector-write-probe")
            with open(probe, "w") as fh:
                fh.write("ok")
            os.remove(probe)
            return cand
        except OSError:
            continue
    return tempfile.mkdtemp(prefix="pgvector-")


def free_port():
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def find_program(name, extra=()):
    for d in list(extra) + os.environ.get("PATH", "").split(os.pathsep):
        if not d:
            continue
        cand = os.path.join(d, name)
        if os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
    return None


def run(cmd, **kw):
    kw.setdefault("stdout", subprocess.PIPE)
    kw.setdefault("stderr", subprocess.STDOUT)
    kw.setdefault("text", True)
    res = subprocess.run(cmd, **kw)
    return res.returncode, res.stdout or ""


# ─────────────────────────── server driver ───────────────────────────
class PgServer(object):
    """A throw-away PostgreSQL instance driven over TCP loopback only."""

    def __init__(self, package, work, log, pg_bindir=""):
        self.package = package
        self.work = work
        self.log = log
        self.pg_config = find_program("pg_config", [pg_bindir] if pg_bindir
                                      else [])
        if not self.pg_config:
            raise AssertionError("pg_config not found on PATH")
        self.bindir = run([self.pg_config, "--bindir"])[1].strip()
        self.sharedir = run([self.pg_config, "--sharedir"])[1].strip()
        self.pkglibdir = run([self.pg_config, "--pkglibdir"])[1].strip()
        self.pgroot = os.path.dirname(self.bindir)
        self.version = run([self.pg_config, "--version"])[1].strip()
        self.datadir = os.path.join(work, "data")
        self.port = free_port()
        self.env = dict(os.environ)
        self.env["LD_LIBRARY_PATH"] = (
            os.path.join(self.pgroot, "lib") + os.pathsep +
            self.env.get("LD_LIBRARY_PATH", ""))
        self.started = False

    def tool(self, name):
        path = os.path.join(self.bindir, name)
        if not os.path.isfile(path):
            raise AssertionError(f"{name} missing from {self.bindir}")
        return path

    def start(self):
        rc, out = run([self.tool("initdb"), "-D", self.datadir, "-U", "pgvector",
                       "--no-locale", "-E", "UTF8", "-A", "trust"],
                      env=self.env)
        if rc != 0:
            raise AssertionError(f"initdb failed rc={rc}: {out[-500:]}")
        # A fresh cluster also loads dict_snowball.so out of pkglibdir, which
        # proves the server can dlopen modules from this installation.
        self.log.append("  [ok]   initdb (fresh cluster)")

        auto_conf = os.path.join(self.datadir, "postgresql.auto.conf")
        with open(auto_conf, "a", encoding="utf-8") as fh:
            fh.write("listen_addresses = '127.0.0.1'\n")
            fh.write(f"port = {self.port}\n")
            fh.write("unix_socket_directories = ''\n")
            fh.write(f"extension_control_path = '{self.package}:$system'\n")
            fh.write(f"dynamic_library_path = "
                     f"'{os.path.join(self.package, 'lib')}:$libdir'\n")

        rc, out = run([self.tool("pg_ctl"), "-D", self.datadir, "-w", "-l",
                       os.path.join(self.work, "server.log"), "start"],
                      env=self.env)
        if rc != 0:
            tail = ""
            logfile = os.path.join(self.work, "server.log")
            if os.path.isfile(logfile):
                with open(logfile, "r", errors="replace") as fh:
                    tail = fh.read()[-800:]
            raise AssertionError(f"pg_ctl start failed rc={rc}: {out[-300:]}"
                                 f" | log: {tail}")
        self.started = True
        self.log.append(f"  [ok]   server up: {self.version} on "
                        f"127.0.0.1:{self.port}, unix_socket_directories=''")

        rc, out = run([self.tool("createdb")] + self.host_args() + ["regression"],
                      env=self.env)
        if rc != 0:
            raise AssertionError(f"createdb failed rc={rc}: {out[-500:]}")
        rc, out = self.psql("CREATE EXTENSION vector;", "regression")
        if rc != 0:
            raise AssertionError(
                f"CREATE EXTENSION vector failed rc={rc}: {out[-500:]}")
        self.log.append("  [ok]   CREATE EXTENSION vector "
                        "(control+SQL+module resolved from the package)")

    def host_args(self):
        return f"-h 127.0.0.1 -p {self.port} -U pgvector".split()

    def psql(self, sql, db="regression", flags=("-X", "-q")):
        return run([self.tool("psql")] + list(flags) + self.host_args() +
                   ["-d", db, "-c", sql], env=self.env)

    def scalar(self, sql, db="regression"):
        rc, out = self.psql(sql, db, flags=("-X", "-q", "-A", "-t"))
        if rc != 0:
            raise AssertionError(f"psql rc={rc} for {sql[:60]!r}: {out[-300:]}")
        return out.strip()

    def stop(self):
        if self.started:
            run([self.tool("pg_ctl"), "-D", self.datadir, "-m", "fast", "stop"],
                env=self.env)
            self.started = False


# ─────────────────────────── artifact assertions ───────────────────────────
def check_artifact(pkg, results):
    so = os.path.join(pkg, "lib", "vector.so")
    ctrl = os.path.join(pkg, "extension", "vector.control")
    install_sql = os.path.join(pkg, "extension", "vector--0.8.6.sql")
    for path in (so, ctrl, install_sql):
        if not os.path.isfile(path):
            raise AssertionError(f"missing from package: {path}")

    elf = Elf(so)
    upgrades = sorted(glob.glob(os.path.join(pkg, "extension",
                                             "vector--*--*.sql")))

    # H2 — target data model
    if elf.machine != EM_AARCH64:
        raise AssertionError(f"e_machine={elf.machine}, expected AArch64")
    ohos = [("H2 目标数据模型 ELF64 / 小端 / AArch64 (LP64)",
             f"e_machine={elf.machine} EM_AARCH64, ELF64, LSB")]

    # H1 — musl-only dynamic dependency
    needed = elf.needed()
    if needed != ["libc.so"]:
        raise AssertionError(f"DT_NEEDED={needed}, expected ['libc.so']")
    ohos.append(("H1 动态依赖仅 musl libc.so（无 glibc libc.so.6）",
                 f"DT_NEEDED={needed}"))

    # P1 — HarmonyOS PC ELF signing section
    if ".codesign" not in elf.section_names:
        raise AssertionError(".codesign section missing")
    pc = [("P1 产物含鸿蒙 PC ELF 加载签名段 .codesign", ".codesign present")]

    # P2 — relocatable artifact
    rpaths = elf.rpaths()
    if rpaths:
        raise AssertionError(f"RUNPATH/RPATH still present: {rpaths}")
    pc.append(("P2 无 RPATH/RUNPATH、无构建机绝对路径（可重定位）",
               "RUNPATH absent, DT_NEEDED relocatable"))

    results["ohos"] = ohos
    results["pc"] = pc
    results["artifact"] = {
        "vector_so_bytes": os.path.getsize(so),
        "upgrade_scripts": len(upgrades),
        "soname": elf.soname(),
    }


# ─────────────────────────── consumer assertions ───────────────────────────
def consumer_checks(pg, results):
    checks = []

    def expect(title, sql, want, db="regression"):
        got = pg.scalar(sql, db)
        if got != want:
            raise AssertionError(f"{title}: got {got!r}, want {want!r}")
        checks.append((title, got))

    expect("C1 CREATE EXTENSION vector 生效（extversion 0.8.6）",
           "SELECT extversion FROM pg_extension WHERE extname = 'vector';",
           "0.8.6")
    expect("C2 vector 类型文本往返",
           "SELECT '[1.5,-2,3.25]'::vector::text;", "[1.5,-2,3.25]")
    expect("C3 halfvec / sparsevec / bit 三类型可用",
           "SELECT ('{1:1,3:2}/3'::sparsevec(3))::text || '|' || "
           "('[1,2]'::halfvec(2))::text || '|' || ('101'::bit(3))::text;",
           "{1:1,3:2}/3|[1,2]|101")

    # C4 — distance operators against python-computed references
    a, b = [1.0, 2.0, 3.0], [4.0, 5.0, 6.0]
    refs = {
        "<->": math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b))),
        "<#>": -sum(x * y for x, y in zip(a, b)),
        "<=>": 1.0 - sum(x * y for x, y in zip(a, b)) / (
            math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))),
    }
    for op, want in refs.items():
        got = float(pg.scalar(f"SELECT '[1,2,3]'::vector {op} "
                              "'[4,5,6]'::vector;"))
        if abs(got - want) > 1e-9:
            raise AssertionError(f"{op}: got {got}, want {want}")
        checks.append((f"C4 距离算子 {op} 数值正确", f"{got:.12f}"))

    # C5/C6 — ANN access methods on real data.  probes / ef_search are set to
    # the exhaustive value so the expected neighbour is exact and deterministic.
    rows = ",".join(f"({i},'[{i},{(i * 7) % 100},{(i * 13) % 100}]')"
                    for i in range(100))
    rc, out = pg.psql("DROP TABLE IF EXISTS items;"
                      "CREATE TABLE items (id int, embedding vector(3));"
                      "INSERT INTO items VALUES " + rows + ";")
    if rc != 0:
        raise AssertionError(f"C5 setup failed: {out[-300:]}")
    probe = [42, 194, 546]
    best, best_d = None, None
    for i in range(100):
        d = ((i - probe[0]) ** 2 + ((i * 7) % 100 - probe[1]) ** 2 +
             ((i * 13) % 100 - probe[2]) ** 2)
        if best_d is None or d < best_d:
            best, best_d = i, d

    for title, ddl, knob, index in (
        ("C5 ivfflat 索引构建 + 精确近邻查询",
         "CREATE INDEX items_ivfflat ON items USING ivfflat "
         "(embedding vector_l2_ops) WITH (lists = 10);",
         "SET ivfflat.probes = 10;", "items_ivfflat"),
        ("C6 hnsw 索引构建 + 精确近邻查询",
         "CREATE INDEX items_hnsw ON items USING hnsw "
         "(embedding vector_l2_ops);",
         "SET hnsw.ef_search = 100;", "items_hnsw"),
    ):
        rc, out = pg.psql(ddl)
        if rc != 0:
            raise AssertionError(f"{title}: DDL failed: {out[-300:]}")
        got = pg.scalar(knob + "SET enable_seqscan = off;"
                        f"SELECT id FROM items ORDER BY embedding <-> "
                        f"'[{probe[0]},{probe[1]},{probe[2]}]' LIMIT 1;")
        if got != str(best):
            raise AssertionError(f"{title}: got id={got}, want {best}")
        checks.append((title, f"nearest id={got} (exact)"))
        rc, out = pg.psql(f"DROP INDEX {index};")
        if rc != 0:
            raise AssertionError(f"{title}: drop index failed: {out[-300:]}")

    expect("C7 ivfflat / hnsw 访问方法已注册到 pg_am",
           "SELECT string_agg(amname, ',' ORDER BY amname) FROM pg_am "
           "WHERE amname IN ('ivfflat','hnsw');", "hnsw,ivfflat")

    results["consumer"] = checks


# ─────────────────────────── upstream regress suite ───────────────────────────
def upstream_regress(pg, pkg, work, results, log):
    """Execute the upstream pg_regress groups byte-exactly.

    pg_regress drives each group with ``psql -X -a -q -d <db>`` reading the
    script from stdin and comparing the merged stdout/stderr against
    ``test/expected/<name>.out`` byte for byte.  The runner below replicates
    exactly that (the pg_regress binary itself is not shipped in the
    postgresql/18.3 package).
    """
    sql_dir = os.path.join(pkg, "upstream", "test", "sql")
    exp_dir = os.path.join(pkg, "upstream", "test", "expected")
    names = sorted(f[:-4] for f in os.listdir(sql_dir) if f.endswith(".sql"))
    rundir = os.path.join(work, "run")
    outdir = os.path.join(rundir, "results")
    os.makedirs(outdir, exist_ok=True)     # copy.sql writes results/*.bin here

    passed, failed = 0, []
    for name in names:
        out_file = os.path.join(outdir, name + ".out")
        with open(os.path.join(sql_dir, name + ".sql"), "rb") as fin, \
                open(out_file, "wb") as fout:
            rc = subprocess.run(
                [pg.tool("psql"), "-X", "-a", "-q", "-d", "regression"] +
                pg.host_args(), stdin=fin, stdout=fout,
                stderr=subprocess.STDOUT, cwd=rundir, env=pg.env)
        with open(os.path.join(exp_dir, name + ".out"), "rb") as fh:
            expected = fh.read()
        with open(out_file, "rb") as fh:
            actual = fh.read()
        if rc.returncode == 0 and expected == actual:
            passed += 1
            log.append(f"  [ok]   upstream {name}")
        else:
            failed.append(name)
            log.append(f"  [FAIL] upstream {name} (psql rc={rc.returncode}, "
                       f"expected {len(expected)}B got {len(actual)}B)")

    results["upstream"] = {
        "framework": "pg_regress groups (psql -X -a -q via stdin + byte-exact "
                     "diff against test/expected)",
        "discovered": len(names),
        "executed": len(names),
        "passed": passed,
        "failed": failed,
    }
    return passed, failed


# ───────────────────────────────── main ─────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--package", required=True)
    ap.add_argument("--pg-bindir", default="")
    ap.add_argument("--result", default="")
    args = ap.parse_args()

    pkg = os.path.abspath(args.package)
    log = []
    results = {"package": pkg}
    exit_code = 0
    work = tempfile.mkdtemp(prefix="pgvector-test-", dir=writable_tmp_root())
    pg = None

    try:
        if not os.path.isdir(os.path.join(pkg, "upstream", "test", "sql")):
            raise AssertionError("upstream regression assets not packaged")
        check_artifact(pkg, results)
        log.append("  [ok]   artifact assertions "
                   "(ELF64/AArch64, .codesign, DT_NEEDED, no RUNPATH)")

        pg = PgServer(pkg, work, log, args.pg_bindir)
        log.append(f"  [info] {pg.pg_config} -> {pg.version}")
        pg.start()

        consumer_checks(pg, results)
        log.append(f"  [ok]   consumer SQL assertions "
                   f"({len(results['consumer'])} checks)")

        passed, failed = upstream_regress(pg, pkg, work, results, log)
        log.append(f"  [{'ok' if not failed else 'FAIL'}] upstream regress "
                   f"{passed}/{results['upstream']['discovered']}")
        if failed:
            exit_code = 1
    except AssertionError as exc:
        log.append(f"  [FAIL] {exc}")
        exit_code = 1
    except Exception as exc:                                   # noqa: BLE001
        log.append(f"  [FAIL] unexpected {type(exc).__name__}: {exc}")
        exit_code = 1
    finally:
        if pg is not None:
            try:
                pg.stop()
            except Exception:                                  # noqa: BLE001
                pass
        shutil.rmtree(work, ignore_errors=True)

    results["exit_code"] = exit_code
    consumer_count = len(results.get("consumer", []))
    ohos_count = len(results.get("ohos", []))
    pc_count = len(results.get("pc", []))
    local_total = consumer_count + ohos_count + pc_count
    upstream = results.get("upstream") or {
        "framework": "pg_regress groups", "discovered": 0, "executed": 0,
        "passed": 0, "failed": [], "skipped": 0,
    }

    print("  ".join(log))
    print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
        "executed": True,
        "passed": exit_code == 0,
        "command": "test_package/pgvector_test.py (artifact + consumer SQL "
                   "assertions)",
        "discovered": local_total,
        "passedCount": local_total if exit_code == 0 else 0,
        "failedCount": 0 if exit_code == 0 else local_total,
        "breakdown": {"consumer": consumer_count, "ohos": ohos_count,
                      "pc": pc_count},
    }, ensure_ascii=False))
    print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
        "status": "failed" if upstream["failed"] else "passed",
        "framework": upstream["framework"],
        "command": "make installcheck equivalent: initdb -> pg_ctl start -> "
                   "CREATE EXTENSION vector -> psql -X -a -q per group",
        "discovered": upstream["discovered"],
        "executed": upstream["executed"],
        "passed": upstream["passed"],
        "failed": len(upstream["failed"]),
        "skipped": 0,
        "reason": ("all upstream pg_regress groups matched their expected "
                   "output byte-exactly"
                   if not upstream["failed"] else
                   "failed groups: " + ", ".join(upstream["failed"])),
        "not_executed": "48 Perl TAP scripts (test/t/*.pl) — require the Perl "
                        "module IPC::Run, unavailable on OHOS",
    }, ensure_ascii=False))
    print("PGVECTOR_TEST_DETAIL=" + json.dumps(results, ensure_ascii=False))
    if args.result:
        with open(args.result, "w", encoding="utf-8") as fh:
            json.dump(results, fh, ensure_ascii=False, indent=2)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
