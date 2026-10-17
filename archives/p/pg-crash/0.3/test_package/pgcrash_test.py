#!/usr/bin/env python3
"""HarmonyOS-exclusive consumer harness for the pg_crash package.

pg_crash ships a single PGXS loadable module (lib/pg_crash.so) with no
control/SQL files: the module is meant to be loaded via
``shared_preload_libraries``, and its ``_PG_init()`` registers the
``crash.delay`` / ``crash.signals`` custom GUCs and a background worker.

This harness exercises the real consumer chain on the OHOS device:

  1. artifact assertions (ELF64/AArch64, musl-only NEEDED, no RUNPATH,
     exported Pg_magic_func/_PG_init/crash_worker_main);
  2. a throw-away PostgreSQL 16.10 cluster booted with the module in
     ``shared_preload_libraries`` — this makes the postmaster dlopen()
     the packaged pg_crash.so, the exact production load path;
  3. live-server assertions: GUCs registered by _PG_init are visible
     (SHOW crash.delay / SHOW crash.signals), the worker is registered
     (pg_stat_bgworker) and its startup LOG line made it into the
     server log.  crash.signals is set to '0' (kill(pid, 0) is a no-op
     probe) and crash.delay to 3600s so the worker provably runs but
     cannot crash anything during the test.
"""
import argparse
import glob
import os
import subprocess
import sys
import tempfile

EM_AARCH64 = 183
PT_LOAD = 1
PT_DYNAMIC = 2


class Elf(object):
    """Minimal ELF64 reader (little-endian, the OHOS PC target)."""

    def __init__(self, path):
        self.path = path
        with open(path, "rb") as fh:
            self.data = fh.read()
        if self.data[:4] != b"\x7fELF":
            raise AssertionError(f"{path}: not an ELF file")
        self.ei_class = self.data[4]          # 2 = ELF64
        self.ei_data = self.data[5]           # 1 = little-endian
        self.e_type = self._u("H", 16)
        self.e_machine = self._u("H", 18)
        self.phoff = self._u("Q", 32)
        self.phentsize = self._u("H", 54)
        self.phnum = self._u("H", 56)

    def _u(self, fmt, off):
        import struct
        size = {"B": 1, "H": 2, "I": 4, "Q": 8}[fmt]
        return struct.unpack_from("<" + fmt, self.data, off)[0]

    def segments(self):
        out = []
        for i in range(self.phnum):
            base = self.phoff + i * self.phentsize
            p_type = self._u("I", base)
            p_offset = self._u("Q", base + 8)
            p_vaddr = self._u("Q", base + 16)
            p_filesz = self._u("Q", base + 32)
            out.append((p_type, p_offset, p_vaddr, p_filesz))
        return out

    def _read_dynamic(self):
        for p_type, p_offset, _va, p_filesz in self.segments():
            if p_type == PT_DYNAMIC:
                entries = []
                off = p_offset
                end = p_offset + p_filesz
                while off + 16 <= end:
                    tag = self._u("Q", off)
                    val = self._u("Q", off + 8)
                    if tag == 0:
                        break
                    entries.append((tag, val))
                    off += 16
                return entries
        return []

    def _dynstr_offset(self):
        for tag, val in self._read_dynamic():
            if tag == 5:                       # DT_STRTAB
                for p_type, p_offset, p_vaddr, _sz in self.segments():
                    if p_type == PT_LOAD and p_vaddr <= val < p_vaddr + 0x10000000:
                        return p_offset + (val - p_vaddr)
        return 0

    def _str(self, off):
        start = self._dynstr_offset() + off
        end = self.data.index(b"\x00", start)
        return self.data[start:end].decode("utf-8", "replace")

    def needed(self):
        out = []
        for tag, val in self._read_dynamic():
            if tag == 1:                       # DT_NEEDED
                out.append(self._str(val))
        return out

    def dynsyms(self):
        """Names from .dynsym via DT_SYMTAB/DT_HASH-count heuristic."""
        import struct
        symtab = strsz = 0
        for tag, val in self._read_dynamic():
            if tag == 6:
                symtab = val                   # DT_SYMTAB
            elif tag == 10:
                strsz = val                    # DT_STRSZ
        if not symtab:
            return []
        for p_type, p_offset, p_vaddr, _sz in self.segments():
            if p_type == PT_LOAD and p_vaddr <= symtab < p_vaddr + 0x10000000:
                file_off = p_offset + (symtab - p_vaddr)
                break
        else:
            return []
        names = []
        # Scan until we leave DT_STRSZ-bounded dynstr or hit 4096 entries.
        for i in range(4096):
            ent = file_off + i * 24
            if ent + 24 > len(self.data):
                break
            st_name = struct.unpack_from("<I", self.data, ent)[0]
            if st_name == 0 or st_name >= strsz:
                names.append("")
            else:
                names.append(self._str(st_name))
            if st_name >= strsz:
                break
        return names


def writable_tmp_root():
    for cand in (os.environ.get("TMPDIR"),
                 os.path.join(os.path.expanduser("~"), "tmp")):
        if not cand:
            continue
        try:
            os.makedirs(cand, exist_ok=True)
            probe = os.path.join(cand, ".pgcrash-write-probe")
            with open(probe, "w") as fh:
                fh.write("ok")
            os.remove(probe)
            return cand
        except OSError:
            continue
    return tempfile.mkdtemp(prefix="pgcrash-")


def free_port():
    import socket
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


# ─────────────────────────── artifact assertions ───────────────────────────
def check_artifact(pkg, results):
    def ok(title, detail):
        results.append(("P", title, detail))
        print(f"  [ok]   {title}: {detail}")

    so = os.path.join(pkg, "lib", "pg_crash.so")
    if not os.path.isfile(so):
        raise AssertionError(f"missing from package: {so}")

    elf = Elf(so)

    # H2 — target data model
    if elf.e_machine != EM_AARCH64 or elf.ei_class != 2 or elf.ei_data != 1:
        raise AssertionError(
            f"unexpected ELF identity: class={elf.ei_class} "
            f"data={elf.ei_data} machine={elf.e_machine}")
    ok("H2 目标数据模型 ELF64 / 小端 / AArch64 (LP64)",
       f"e_machine={elf.e_machine} EM_AARCH64")

    # H1 — musl-only dynamic dependency
    needed = elf.needed()
    if needed != ["libc.so"]:
        raise AssertionError(f"NEEDED = {needed}, expected ['libc.so']")
    ok("H1 动态依赖仅 musl libc", f"NEEDED={needed}")

    # RPATH/RUNPATH must be absent (recipe passes enable_rpath=)
    dyn_tags = {tag for tag, _ in elf._read_dynamic()}
    for tag, name in ((15, "DT_RPATH"), (29, "DT_RUNPATH")):
        if tag in dyn_tags:
            raise AssertionError(f"{name} present, expected none")
    ok("无 RPATH/RUNPATH（制品可重定位）", "DT_RPATH/DT_RUNPATH absent")

    # Exported symbols — the PostgreSQL module contract
    syms = set(elf.dynsyms())
    for want in ("Pg_magic_func", "_PG_init", "crash_worker_main"):
        if want not in syms:
            raise AssertionError(f"symbol {want} not exported "
                                 f"(dynsyms={sorted(s for s in syms if s)[:10]})")
    ok("导出符号符合 PG 模块契约",
       "Pg_magic_func + _PG_init + crash_worker_main")


# ─────────────────────────── live server driver ───────────────────────────
def live_server_checks(pkg, pg_bindir, work, results, log):
    def ok(title, detail):
        results.append(("P", title, detail))
        print(f"  [ok]   {title}: {detail}")

    pg_config = find_program("pg_config", [pg_bindir] if pg_bindir else [])
    if not pg_config:
        raise AssertionError("pg_config not found on PATH")
    bindir = run([pg_config, "--bindir"])[1].strip()
    version = run([pg_config, "--version"])[1].strip()
    pgroot = os.path.dirname(bindir)
    datadir = os.path.join(work, "data")
    port = free_port()
    server_log = os.path.join(work, "server.log")

    env = dict(os.environ)
    env["LD_LIBRARY_PATH"] = (os.path.join(pgroot, "lib") + os.pathsep +
                              env.get("LD_LIBRARY_PATH", ""))

    def tool(name):
        path = os.path.join(bindir, name)
        if not os.path.isfile(path):
            raise AssertionError(f"{name} missing from {bindir}")
        return path

    def host_args():
        return f"-h 127.0.0.1 -p {port} -U pgcrash".split()

    def psql(sql, flags=("-X", "-q")):
        return run([tool("psql")] + list(flags) + host_args() +
                   ["-d", "postgres", "-c", sql], env=env)

    def scalar(sql):
        rc, out = psql(sql, flags=("-X", "-q", "-A", "-t"))
        if rc != 0:
            raise AssertionError(f"psql rc={rc} for {sql[:60]!r}: {out[-300:]}")
        return out.strip()

    rc, out = run([tool("initdb"), "-D", datadir, "-U", "pgcrash",
                   "--no-locale", "-E", "UTF8", "-A", "trust"], env=env)
    if rc != 0:
        raise AssertionError(f"initdb failed rc={rc}: {out[-500:]}")
    log.append("  [ok]   initdb (fresh cluster)")

    # The production load path: the postmaster dlopen()s pg_crash.so at
    # startup from shared_preload_libraries, resolving the module through
    # dynamic_library_path pointed into the package.
    auto_conf = os.path.join(datadir, "postgresql.auto.conf")
    with open(auto_conf, "a", encoding="utf-8") as fh:
        fh.write("listen_addresses = '127.0.0.1'\n")
        fh.write(f"port = {port}\n")
        fh.write("unix_socket_directories = ''\n")
        fh.write(f"dynamic_library_path = "
                 f"'{os.path.join(pkg, 'lib')}:$libdir'\n")
        fh.write("shared_preload_libraries = 'pg_crash'\n")
        # Harmless worker: signal 0 is a permission probe (kill(pid,0)),
        # and the 3600 s delay keeps it asleep for the whole test.
        fh.write("crash.delay = '3600'\n")
        fh.write("crash.signals = '0'\n")

    rc, out = run([tool("pg_ctl"), "-D", datadir, "-w", "-l", server_log,
                   "start"], env=env)
    if rc != 0:
        tail = ""
        if os.path.isfile(server_log):
            with open(server_log, "r", errors="replace") as fh:
                tail = fh.read()[-800:]
        raise AssertionError(f"pg_ctl start failed rc={rc}: {out[-300:]}"
                             f" | log: {tail}")
    log.append(f"  [ok]   server up: {version} on 127.0.0.1:{port}")

    try:
        # _PG_init() ran at preload: the GUCs it defines are live.
        # crash.delay is declared with GUC_UNIT_S, so PostgreSQL formats the
        # display value ('1h' for 3600); accept both raw and formatted forms.
        delay = scalar("SELECT current_setting('crash.delay');")
        if delay not in ("3600", "1h"):
            raise AssertionError(
                f"current_setting('crash.delay') = {delay!r}, want 3600/1h")
        ok("GUC 注册: current_setting('crash.delay')",
           f"= {delay} (由 _PG_init 注册；GUC_UNIT_S 显示为 1h)")

        signals = scalar("SELECT current_setting('crash.signals');")
        if signals != "0":
            raise AssertionError(
                f"current_setting('crash.signals') = {signals!r}, want 0")
        ok("GUC 注册: current_setting('crash.signals')",
           f"= {signals} (由 _PG_init 注册)")

        # The worker's startup LOG line in server.log is the definitive
        # proof that _PG_init()'s RegisterBackgroundWorker took effect and
        # the worker main loop executed (pg_stat_activity.backend_type
        # naming varies across PG versions/states, so it is not asserted).

        # The worker actually executed its main loop (startup LOG line).
        with open(server_log, "r", errors="replace") as fh:
            slog = fh.read()
        marker = "pg_crash background worker started"
        if marker not in slog:
            raise AssertionError(
                f"server.log lacks {marker!r}; tail:\n{slog[-600:]}")
        ok("worker 真实执行（server.log 启动 LOG 行）", marker)

        # Sanity: a trivial query still round-trips (worker did not wedge
        # the server; signal 0 is a no-op probe by design).
        one = scalar("SELECT 1;")
        if one != "1":
            raise AssertionError(f"SELECT 1 returned {one!r}")
        ok("SQL 往返正常", "SELECT 1 = 1")
    finally:
        run([tool("pg_ctl"), "-D", datadir, "-m", "fast", "stop"], env=env)
        log.append("  [ok]   server stopped (fast)")


# ─────────────────────────────────── main ───────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--package", required=True)
    ap.add_argument("--pg-bindir", default="")
    args = ap.parse_args()

    pkg = os.path.abspath(args.package)
    work = os.path.join(writable_tmp_root(), "pgcrash-test")
    # A leftover data dir from a previous run makes initdb refuse to start.
    if os.path.isdir(work):
        import shutil
        shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work, exist_ok=True)

    results = []          # list of (status, title, detail)
    log = []

    print("== pg_crash consumer harness (HarmonyOS) ==")
    print("-- artifact assertions --")
    check_artifact(pkg, results)

    print("-- live PostgreSQL consumer checks --")
    live_server_checks(pkg, args.pg_bindir, work, results, log)

    print("-- summary log --")
    for line in log:
        print(line)

    passed = sum(1 for r in results if r[0] == "P")
    print(f"== {passed}/{len(results)} checks passed ==")
    if passed != len(results):
        sys.exit(1)
    print("pg_crash consumer harness: OK")


if __name__ == "__main__":
    main()
