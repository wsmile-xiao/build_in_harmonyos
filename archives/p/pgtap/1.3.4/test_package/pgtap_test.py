#!/usr/bin/env python3
"""Consumer harness for the pgTAP Conan package (OHOS PC aarch64).

Three evidence groups, all executed against the *installed* package tree:

  1. artifact assertions - the package carries exactly what upstream
     ``make install`` puts into PostgreSQL's share/extension directory:
     pgtap.control with the right fields, the 1.3.4 install script with the
     full TAP API, the historical upgrade chain, the pgtap-core /
     pgtap-schema bundles, the uninstall script, a deterministic
     ``os_name()`` and no build-machine absolute paths.
  2. consumer assertions - a real PostgreSQL 18.3 server is started, the
     packaged extension is loaded through ``extension_control_path`` (PG 18)
     and exercised through SQL: TAP mini-suite, a deliberate negative control
     (proving a failing assertion is detected as ``not ok``), schema
     assertions and lives_ok / throws_ok.
  3. upstream suite - the upstream pg_regress groups are executed
     byte-exactly, exactly like ``make installcheck`` does on PostgreSQL
     18.3 (build + create setup groups included; extension.sql excluded for
     the same reason the upstream Makefile excludes it: citext / isn / ltree
     are not part of the postgresql/18.3 package).

Exit code 0 only when every group is green.
"""
import argparse
import glob
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile

# File set upstream ``make install`` places into share/extension; the recipe
# must package all of them (VERSION_FILES + BASE_FILES of the upstream
# Makefile; upgrade scripts are checked separately below).
REQUIRED_BASE_FILES = (
    "pgtap.sql",
    "uninstall_pgtap.sql",
    "pgtap-core.sql",
    "pgtap-schema.sql",
    "pgtap--1.3.4.sql",
    "pgtap-core--1.3.4.sql",
    "pgtap-schema--1.3.4.sql",
)

# TAP API entry points that must be defined by the install script.
REQUIRED_API = (
    "CREATE OR REPLACE FUNCTION plan(",
    "CREATE OR REPLACE FUNCTION ok (",
    "CREATE OR REPLACE FUNCTION is (",
    "CREATE OR REPLACE FUNCTION has_table (",
    "CREATE OR REPLACE FUNCTION col_not_null (",
    "CREATE OR REPLACE FUNCTION finish (",
)

# Substrings that would betray a build-machine path leak.
MACHINE_PATH_MARKERS = ("/storage/", "/home/", "/data/service/hnp",
                        ".conan2", "C:\\")


# --------------------------------------------------------------- helpers ---
def writable_tmp_root():
    for cand in (os.environ.get("TMPDIR"),
                 os.path.join(os.path.expanduser("~"), "tmp")):
        if not cand:
            continue
        try:
            os.makedirs(cand, exist_ok=True)
            probe = os.path.join(cand, ".pgtap-write-probe")
            with open(probe, "w") as fh:
                fh.write("ok")
            os.remove(probe)
            return cand
        except OSError:
            continue
    return tempfile.mkdtemp(prefix="pgtap-")


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


def read_text(path):
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


# ------------------------------------------------------------ server ------
class PgServer(object):
    """A throw-away PostgreSQL instance driven over TCP loopback only.

    OHOS rejects Unix-domain-socket bind() (EPERM), so the cluster listens on
    127.0.0.1 with unix_socket_directories='' - the same configuration the
    other PostgreSQL extension harnesses in this repository use.
    """

    def __init__(self, package, work, pg_bindir=""):
        self.package = package
        self.work = work
        self.pg_config = find_program("pg_config",
                                      [pg_bindir] if pg_bindir else [])
        if not self.pg_config:
            raise AssertionError("pg_config not found on PATH")
        self.bindir = run([self.pg_config, "--bindir"])[1].strip()
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
        rc, out = run([self.tool("initdb"), "-D", self.datadir, "-U", "pgtap",
                       "--no-locale", "-E", "UTF8", "-A", "trust"],
                      env=self.env)
        if rc != 0:
            raise AssertionError(f"initdb failed rc={rc}: {out[-500:]}")

        auto_conf = os.path.join(self.datadir, "postgresql.auto.conf")
        with open(auto_conf, "a", encoding="utf-8") as fh:
            fh.write("listen_addresses = '127.0.0.1'\n")
            fh.write(f"port = {self.port}\n")
            fh.write("unix_socket_directories = ''\n")
            # PG 18: <path>/extension/<name>.control is searched under every
            # path item; the package root is a valid "share dir".
            fh.write(f"extension_control_path = '{self.package}:$system'\n")

        rc, out = run([self.tool("pg_ctl"), "-D", self.datadir, "-w", "-l",
                       os.path.join(self.work, "server.log"), "start"],
                      env=self.env)
        if rc != 0:
            tail = ""
            logfile = os.path.join(self.work, "server.log")
            if os.path.isfile(logfile):
                tail = read_text(logfile)[-800:]
            raise AssertionError(f"pg_ctl start failed rc={rc}: {out[-300:]}"
                                 f" | log: {tail}")
        self.started = True

        for db in ("contrib_regression", "pgtap_consumer"):
            rc, out = run([self.tool("createdb")] + self.host_args() + [db],
                          env=self.env)
            if rc != 0:
                raise AssertionError(f"createdb {db} failed rc={rc}: "
                                     f"{out[-300:]}")

    def host_args(self):
        return f"-h 127.0.0.1 -p {self.port} -U pgtap".split()

    def psql(self, sql, db="pgtap_consumer", flags=("-X", "-q")):
        return run([self.tool("psql")] + list(flags) + self.host_args() +
                   ["-d", db, "-c", sql], env=self.env)

    def scalar(self, sql, db="pgtap_consumer"):
        rc, out = self.psql(sql, db, flags=("-X", "-q", "-A", "-t"))
        if rc != 0:
            raise AssertionError(f"psql rc={rc} for {sql[:60]!r}: "
                                 f"{out[-300:]}")
        return out.strip()

    def stop(self):
        if self.started:
            run([self.tool("pg_ctl"), "-D", self.datadir, "-m", "fast",
                 "stop"], env=self.env)
            self.started = False


# ----------------------------------------------------- artifact checks -----
def check_artifact(pkg, results):
    checks = []
    ext = os.path.join(pkg, "extension")

    ctrl_path = os.path.join(ext, "pgtap.control")
    if not os.path.isfile(ctrl_path):
        raise AssertionError(f"missing from package: {ctrl_path}")
    ctrl = read_text(ctrl_path)
    for needle in ("default_version = '1.3.4'", "requires = 'plpgsql'",
                   "relocatable = true"):
        if needle not in ctrl:
            raise AssertionError(f"pgtap.control lacks {needle!r}")
    checks.append(("A1 pgtap.control 字段完整（1.3.4 / plpgsql / relocatable）",
                   "3 项字段存在"))

    install = os.path.join(ext, "pgtap--1.3.4.sql")
    if not os.path.isfile(install):
        raise AssertionError(f"missing from package: {install}")
    text = read_text(install)
    if len(text) < 50000:
        raise AssertionError(f"install script suspiciously small: "
                             f"{len(text)} bytes")
    nfunc = text.count("CREATE OR REPLACE FUNCTION")
    if nfunc < 500:
        raise AssertionError(f"only {nfunc} functions in install script")
    checks.append(("A2 安装脚本完整（>=500 个 CREATE OR REPLACE FUNCTION）",
                   f"{nfunc} 个函数, {len(text)} bytes"))

    missing_api = [api for api in REQUIRED_API if api not in text]
    if missing_api:
        raise AssertionError(f"TAP API missing from install script: "
                             f"{missing_api}")
    checks.append(("A3 TAP API 入口齐备（plan/ok/is/has_table/col_not_null/finish）",
                   "6/6 存在"))

    if "SELECT ''harmonyos''::text" not in text:
        raise AssertionError("os_name() is not pinned to 'harmonyos' - "
                             "OSNAME substitution failed")
    checks.append(("A4 os_name() 钉为 harmonyos（OSNAME 注入生效）",
                   "harmonyos"))

    upgrades = sorted(glob.glob(os.path.join(ext, "pgtap--*--*.sql")))
    needed = os.path.join(ext, "pgtap--1.3.3--1.3.4.sql")
    if len(upgrades) < 17 or not os.path.isfile(needed):
        raise AssertionError(f"upgrade chain incomplete: "
                             f"{len(upgrades)} files, 1.3.3->1.3.4 present="
                             f"{os.path.isfile(needed)}")
    checks.append((f"A5 历史升级脚本链完整（{len(upgrades)} 个 --*--*.sql）",
                   ">=17 且含 1.3.3->1.3.4"))

    for name in REQUIRED_BASE_FILES:
        path = os.path.join(ext, name)
        if not os.path.isfile(path) or os.path.getsize(path) == 0:
            raise AssertionError(f"missing/empty base bundle: {path}")
    checks.append(("A6 基础/版本化 bundle 齐备（uninstall + pgtap/core/schema 各 2 件）",
                   f"{len(REQUIRED_BASE_FILES)}/7"))

    leaks = []
    for path in sorted(glob.glob(os.path.join(ext, "*.sql"))) + [ctrl_path]:
        body = read_text(path)
        for marker in MACHINE_PATH_MARKERS:
            if marker in body:
                leaks.append((os.path.basename(path), marker))
    if leaks:
        raise AssertionError(f"build-machine paths leaked into package: "
                             f"{leaks[:5]}")
    checks.append(("A7 无构建机绝对路径泄漏（/storage、/home、.conan2 等）",
                   f"扫描 {len(glob.glob(os.path.join(ext, '*.sql'))) + 1} 个文件"))

    up_sql = os.path.join(pkg, "upstream", "test", "sql")
    up_exp = os.path.join(pkg, "upstream", "test", "expected")
    n_sql = len(glob.glob(os.path.join(up_sql, "*.sql")))
    n_exp = len(glob.glob(os.path.join(up_exp, "*.out")))
    if n_sql != 37 or n_exp != 54:
        raise AssertionError(f"upstream assets not packaged correctly: "
                             f"sql={n_sql}, expected={n_exp}")
    checks.append((f"A8 上游回归资产随包（{n_sql} sql / {n_exp} expected）",
                   "37/54"))

    results["artifact"] = checks


# ----------------------------------------------------- consumer checks -----
def tap_lines(out):
    return [ln.strip() for ln in out.splitlines() if ln.strip()]


def assert_tap_ok(title, out, expected_plan, checks, note=""):
    lines = tap_lines(out)
    ok_lines = [ln for ln in lines if ln.startswith("ok ")]
    bad_lines = [ln for ln in lines if ln.startswith("not ok")]
    if expected_plan not in lines:
        raise AssertionError(f"{title}: plan line {expected_plan!r} missing; "
                             f"got: {lines[:8]}")
    if len(ok_lines) != int(expected_plan.split("..")[1]):
        raise AssertionError(f"{title}: expected "
                             f"{expected_plan.split('..')[1]} passing TAP "
                             f"lines, got {len(ok_lines)}: {lines[:8]}")
    if bad_lines:
        raise AssertionError(f"{title}: unexpected not-ok lines: {bad_lines}")
    checks.append((title, note or f"{len(ok_lines)} TAP lines, 0 failures"))


def consumer_checks(pg, results):
    checks = []
    tap_flags = ("-X", "-q", "-A", "-t")

    def expect(title, sql, want, db="pgtap_consumer"):
        got = pg.scalar(sql, db)
        if got != want:
            raise AssertionError(f"{title}: got {got!r}, want {want!r}")
        checks.append((title, got))

    rc, out = pg.psql("CREATE EXTENSION pgtap;", "pgtap_consumer")
    if rc != 0:
        raise AssertionError(f"CREATE EXTENSION pgtap failed rc={rc}: "
                             f"{out[-400:]}")
    checks.append(("C1 CREATE EXTENSION pgtap 生效（control+SQL 从包目录解析）",
                   "CREATE EXTENSION rc=0"))

    expect("C2 extversion = 1.3.4",
           "SELECT extversion FROM pg_extension WHERE extname = 'pgtap';",
           "1.3.4")
    expect("C3 pgtap_version() = 1.3", "SELECT pgtap_version();", "1.3")
    expect("C4 os_name() = harmonyos（平台标识）", "SELECT os_name();",
           "harmonyos")
    expect("C5 pg_version_num() 匹配 PG 18 版本号",
           "SELECT pg_version_num() > 180000;", "t")

    # C6 - a real TAP mini-suite (plan/ok/is/isnt + finish)
    rc, out = pg.psql(
        "SELECT plan(3);"
        "SELECT ok(true, 'ok() passes');"
        "SELECT is(2 + 2, 4, 'is() integer equality');"
        "SELECT isnt('a'::text, 'b'::text, 'isnt() strings differ');"
        "SELECT * FROM finish();", flags=tap_flags)
    if rc != 0:
        raise AssertionError(f"TAP mini-suite rc={rc}: {out[-300:]}")
    assert_tap_ok("C6 TAP mini-suite（plan/ok/is/isnt/finish）3/3",
                  out, "1..3", checks)

    # C7 - negative control: a deliberately failing assertion MUST be
    # reported as "not ok".  This proves the assertions are not vacuous.
    rc, out = pg.psql(
        "SELECT plan(1);"
        "SELECT is(1, 2, 'deliberately wrong');"
        "SELECT * FROM finish();", flags=tap_flags)
    lines = tap_lines(out)
    if "not ok 1 - deliberately wrong" not in lines:
        raise AssertionError("negative control: failing assertion was NOT "
                             f"reported as not ok; got: {lines[:8]}")
    checks.append(("C7 负向对照：故意失败的断言报 not ok（断言非空壳）",
                   "not ok 1 - deliberately wrong"))

    # C8 - schema assertions on a real table, all inside a rolled-back tx.
    rc, out = pg.psql(
        "BEGIN;"
        "CREATE TABLE public.widgets (id serial PRIMARY KEY,"
        " name text NOT NULL, price numeric);"
        "SELECT plan(4);"
        "SELECT has_table('public', 'widgets', 'table exists');"
        "SELECT has_column('public', 'widgets', 'name', 'column exists');"
        "SELECT col_not_null('public', 'widgets', 'name', 'NOT NULL');"
        "SELECT col_is_pk('public', 'widgets', 'id', 'PK');"
        "SELECT * FROM finish();"
        "ROLLBACK;", flags=tap_flags)
    if rc != 0:
        raise AssertionError(f"schema assertions rc={rc}: {out[-300:]}")
    assert_tap_ok("C8 schema 断言（has_table/has_column/col_not_null/col_is_pk）",
                  out, "1..4", checks)

    # C9 - lives_ok / throws_ok
    rc, out = pg.psql(
        "SELECT plan(2);"
        "SELECT lives_ok('SELECT 1', 'lives_ok() executes');"
        "SELECT throws_ok('SELECT 1/0', '22012', NULL,"
        " 'throws_ok() catches division by zero');"
        "SELECT * FROM finish();", flags=tap_flags)
    if rc != 0:
        raise AssertionError(f"lives_ok/throws_ok rc={rc}: {out[-300:]}")
    assert_tap_ok("C9 lives_ok / throws_ok 行为正确", out, "1..2", checks)

    results["consumer"] = checks


# --------------------------------------------------- upstream regress ------
def expected_candidates(exp_dir, name):
    cands = [os.path.join(exp_dir, name + ".out")]
    idx = 1
    while True:
        cand = os.path.join(exp_dir, f"{name}_{idx}.out")
        if not os.path.isfile(cand):
            break
        cands.append(cand)
        idx += 1
    return cands


def psql_stdin(pg, run_root, script_path, db="contrib_regression"):
    with open(script_path, "rb") as fin:
        return subprocess.run(
            [pg.tool("psql"), "-X", "-a", "-q", "-d", db] + pg.host_args(),
            stdin=fin, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            cwd=run_root, env=pg.env)


def run_and_compare(pg, run_root, exp_dir, rel_name, log):
    script = os.path.join(run_root, rel_name)
    res = psql_stdin(pg, run_root, script)
    actual = res.stdout or b""
    for cand in expected_candidates(exp_dir, os.path.basename(rel_name)[:-4]):
        with open(cand, "rb") as fh:
            expected = fh.read()
        if res.returncode == 0 and actual == expected:
            log.append(f"  [ok]   {rel_name} (expected: "
                       f"{os.path.basename(cand)})")
            return True
    cands = [os.path.basename(c) for c in
             expected_candidates(exp_dir, os.path.basename(rel_name)[:-4])]
    log.append(f"  [FAIL] {rel_name} (psql rc={res.returncode}, "
               f"expected {cands})")
    return False


def upstream_regress(pg, pkg, work, results, log):
    src = os.path.join(pkg, "upstream")
    pkg_sql_dir = os.path.join(src, "test", "sql")
    exp_dir = os.path.join(src, "test", "expected")
    run_root = os.path.join(work, "upstream-run")
    if os.path.exists(run_root):
        shutil.rmtree(run_root)
    os.makedirs(run_root)
    shutil.copytree(os.path.join(src, "test"),
                    os.path.join(run_root, "test"))
    shutil.copytree(os.path.join(src, "sql"),
                    os.path.join(run_root, "sql"))

    # Generate build.sql / create.sql exactly like the upstream Makefile:
    #   test/sql/%.sql: test/schedule/%.sql
    for name in ("build", "create"):
        body = read_text(os.path.join(run_root, "test", "schedule",
                                      name + ".sql"))
        with open(os.path.join(run_root, "test", "sql", name + ".sql"),
                  "w", encoding="utf-8") as fh:
            fh.write("\\unset ECHO\n"
                     "-- GENERATED FILE! DO NOT EDIT!\n"
                     f"-- Original file: test/schedule/{name}.sql\n")
            fh.write(body)

    # Test selection, mirroring the upstream Makefile:
    #   * build/create/update are schedule-generated setup groups
    #   * extension.sql is excluded while citext/isn/ltree are unavailable
    #     (the upstream Makefile does exactly this via MISSING_EXTENSIONS)
    names = sorted(f[:-4] for f in os.listdir(pkg_sql_dir)
                   if f.endswith(".sql"))
    names = [n for n in names if n not in ("build", "create", "update")]

    skipped = {}
    available = set(
        x for x in pg.scalar(
            "SELECT string_agg(name, ',') FROM pg_available_extensions "
            "WHERE name IN ('citext', 'isn', 'ltree');",
            "contrib_regression").split(",") if x)
    missing_ext = {"citext", "isn", "ltree"} - available
    if missing_ext:
        skipped["extension"] = (
            "needs extensions " + ", ".join(sorted(missing_ext)) +
            " which are not part of postgresql/18.3 (same exclusion the "
            "upstream Makefile applies via MISSING_EXTENSIONS)")

    log.append("  [info] upstream groups: %d selected, skipped: %s"
               % (len(names) - len(skipped), sorted(skipped) or "-"))

    setup_results = {}
    for name in ("build", "create"):
        setup_results[name] = run_and_compare(
            pg, run_root, exp_dir, f"test/sql/{name}.sql", log)
    setup_pass = sum(1 for ok in setup_results.values() if ok)
    setup_fail = len(setup_results) - setup_pass

    passed, failed = 0, []
    for name in names:
        if name in skipped:
            continue
        if run_and_compare(pg, run_root, exp_dir, f"test/sql/{name}.sql",
                           log):
            passed += 1
        else:
            failed.append(name)

    results["upstream"] = {
        "framework": ("pg_regress groups (psql -X -a -q via stdin + "
                      "byte-exact diff against test/expected/*.out)"),
        "discovered": len(names),
        "executed": len(names) - len(skipped),
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "setup_groups": setup_results,
        "setup_passed": setup_pass,
        "setup_failed": setup_fail,
    }
    return passed, failed, setup_fail


# ----------------------------------------------------------------- main ----
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
    work = tempfile.mkdtemp(prefix="pgtap-test-", dir=writable_tmp_root())
    pg = None

    try:
        if not os.path.isdir(os.path.join(pkg, "upstream", "test", "sql")):
            raise AssertionError("upstream regression assets not packaged")
        check_artifact(pkg, results)
        log.append("  [ok]   artifact assertions")
        n_artifact = len(results["artifact"])

        pg = PgServer(pkg, work, args.pg_bindir)
        log.append(f"  [info] {pg.pg_config} -> {pg.version}")
        pg.start()
        log.append(f"  [ok]   server up: {pg.version} on 127.0.0.1:"
                   f"{pg.port}, unix_socket_directories='', "
                   "extension_control_path=<package>")

        consumer_checks(pg, results)
        log.append(f"  [ok]   consumer SQL assertions "
                   f"({len(results['consumer'])} checks)")
        n_consumer = len(results["consumer"])

        passed, failed, setup_fail = upstream_regress(pg, pkg, work,
                                                      results, log)
        upstream = results["upstream"]
        log.append(f"  [{'ok' if not failed and not setup_fail else 'FAIL'}]"
                   f" upstream regress {passed}/{upstream['executed']} + "
                   f"setup build/create "
                   f"{'ok' if setup_fail == 0 else 'FAIL'}")
        if failed or setup_fail:
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
    n_artifact = len(results.get("artifact", []))
    n_consumer = len(results.get("consumer", []))
    local_total = n_artifact + n_consumer
    upstream = results.get("upstream") or {
        "framework": "pg_regress groups", "discovered": 0, "executed": 0,
        "passed": 0, "failed": [], "skipped": {},
    }
    upstream_ok = (not upstream["failed"] and upstream.get("setup_failed", 1)
                   == 0 and upstream["executed"] > 0)

    print("  ".join(log))
    print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
        "executed": True,
        "passed": exit_code == 0,
        "command": ("test_package/pgtap_test.py (artifact + consumer SQL/TAP "
                    "assertions)"),
        "discovered": local_total,
        "passedCount": local_total if exit_code == 0 else 0,
        "failedCount": 0 if exit_code == 0 else local_total,
        "breakdown": {"artifact": n_artifact, "consumer": n_consumer},
    }, ensure_ascii=False))
    print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
        "status": "passed" if upstream_ok else "failed",
        "framework": upstream["framework"],
        "command": ("make installcheck equivalent: initdb -> pg_ctl start -> "
                    "psql -X -a -q per group -> byte-exact diff against "
                    "test/expected"),
        "discovered": upstream["discovered"],
        "executed": upstream["executed"] + upstream.get("setup_passed", 0),
        "passed": upstream["passed"] + upstream.get("setup_passed", 0),
        "failed": len(upstream["failed"]) + upstream.get("setup_failed", 0),
        "skipped": len(upstream["skipped"]),
        "reason": ("all upstream pg_regress groups matched their expected "
                   "output byte-exactly (build/create setup groups included)"
                   if upstream_ok else
                   "failed groups: " + ", ".join(upstream["failed"] or
                                                 ["build/create"])),
        "not_executed": ("extension.sql - " + upstream["skipped"]["extension"]
                         if "extension" in upstream["skipped"] else ""),
        "skipped_groups": sorted(upstream["skipped"]),
    }, ensure_ascii=False))
    print("PGTAP_TEST_DETAIL=" + json.dumps(results, ensure_ascii=False))
    if args.result:
        with open(args.result, "w", encoding="utf-8") as fh:
            json.dump(results, fh, ensure_ascii=False, indent=2)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
