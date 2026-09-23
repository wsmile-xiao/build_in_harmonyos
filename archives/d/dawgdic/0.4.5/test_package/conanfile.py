#!/usr/bin/env python3
"""test_package for dawgdic: compiles a C++ consumer against the packaged
headers and runs the packaged dawgdic-build / dawgdic-find tools."""
import hashlib
import json
import os
import re
import shutil
import subprocess
import tarfile
import urllib.request

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class DawgdicTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _writable_tmpdir(self):
        for var in ("HMBS_TMPDIR", "TMPDIR", "TMP", "TEMP",
                    "HMBS_AUTOCONF_MKTEMP_FALLBACK"):
            value = os.environ.get(var)
            if value and value not in ("0", "/tmp"):
                try:
                    os.makedirs(value, exist_ok=True)
                except OSError:
                    continue
                try:
                    probe = os.path.join(value, ".hmbs_probe")
                    with open(probe, "w") as handle:
                        handle.write("probe")
                    os.remove(probe)
                    return value
                except OSError:
                    continue
        fallback = os.path.join(self.build_folder or os.getcwd(), "tmp_hmbs")
        try:
            os.makedirs(fallback, exist_ok=True)
        except OSError:
            pass
        return fallback

    def test(self):
        if not can_run(self):
            self.output.info("Skipping runtime tests while cross-building")
            return
        tmpdir = self._writable_tmpdir()
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = tmpdir
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            pass
        pkg = self.dependencies["dawgdic"].package_folder
        # HMBS injects only a subset of conf (jobs, cmake/make paths); do not
        # assume tools.build:compiler_executables(:cpp) exists. Probe the dict
        # form first, then fall back to CXX env / PATH lookup.
        cxx = None
        try:
            exes = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict)
            if isinstance(exes, dict):
                cxx = exes.get("cpp") or exes.get("c++")
        except Exception:
            cxx = None
        if not cxx:
            try:
                cxx = self.conf.get("tools.build:compiler_executables:cpp",
                                    default=None, check_type=str)
            except Exception:
                cxx = None
        cxx = (cxx or os.environ.get("CXX")
               or shutil.which("clang++") or shutil.which("c++")
               or shutil.which("g++") or "clang++")
        src = os.path.join(self.source_folder, "test_dawgdic.cpp")
        exe = os.path.join(self.build_folder, "test_dawgdic")
        include = os.path.join(pkg, "include")
        self.run(f'"{cxx}" -std=c++17 "{src}" -I"{include}" -o "{exe}"',
                 env="conanrun")
        cpp_log = os.path.join(self.build_folder, "test_dawgdic.log")
        self.run(f'"{exe}" > "{cpp_log}" 2>&1', env="conanrun")
        cpp_out = ""
        if os.path.isfile(cpp_log):
            with open(cpp_log, encoding="utf-8", errors="replace") as handle:
                cpp_out = handle.read()
        self.output.info("test_dawgdic output:\n" + "\n".join(cpp_out.splitlines()[-16:]))
        cpp_passed = len(re.findall(r"\[PASS\]", cpp_out))
        cpp_failed = len(re.findall(r"\[FAIL\]", cpp_out))
        if "ALL TESTS PASSED" not in cpp_out or cpp_failed:
            raise ConanException(
                "test_dawgdic failed: passed=%d failed=%d" % (cpp_passed, cpp_failed)
            )

        def _resolve_bash():
            cands = [
                os.environ.get("CONFIG_SHELL"),
                os.environ.get("HMBS_BASH"),
                shutil.which("bash"),
                "/data/service/hnp/bin/bash",
                "/bin/bash",
                "/usr/local/bin/bash",
                "/usr/bin/bash",
            ]
            for cand in cands:
                if not cand or os.path.basename(cand) != "bash":
                    continue
                try:
                    if os.path.isfile(cand) and os.access(cand, os.X_OK):
                        return cand
                except OSError:
                    continue
            # shutil.which already covers PATH; last resort keeps bash semantics.
            return shutil.which("bash") or "/data/service/hnp/bin/bash"

        bash = _resolve_bash()
        self.output.info("[hmbs] test_tools interpreter: %s" % bash)
        script = os.path.join(self.source_folder, "test_tools.sh")
        tools_log = os.path.join(self.build_folder, "test_tools.log")
        self.run(f'"{bash}" "{script}" "{os.path.join(pkg, "bin")}" > "{tools_log}" 2>&1',
                 env="conanrun")
        tools_out = ""
        if os.path.isfile(tools_log):
            with open(tools_log, encoding="utf-8", errors="replace") as handle:
                tools_out = handle.read()
        self.output.info("test_tools.sh output:\n" + "\n".join(tools_out.splitlines()[-16:]))
        tools_passed = len(re.findall(r"\[PASS\]", tools_out))
        tools_failed = len(re.findall(r"\[FAIL\]", tools_out))
        if "ALL TOOL TESTS PASSED" not in tools_out or tools_failed:
            raise ConanException(
                "test_tools.sh failed: passed=%d failed=%d" % (tools_passed, tools_failed)
            )

        discovered = cpp_passed + tools_passed
        passed_count = discovered
        ok = discovered > 0 and cpp_failed == 0 and tools_failed == 0
        marker = {
            "executed": True,
            "passed": ok,
            "command": "./test_dawgdic + bash test_tools.sh <package>/bin",
            "discovered": discovered,
            "passedCount": passed_count,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker))
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker))
        if not ok:
            raise ConanException("dawgdic test_package failed")
        # Upstream evidence must appear on EVERY `conan create`, even when the
        # main build() is skipped ("Already installed" cache hit for
        # header-library). Prefer the persisted build-time result; if the
        # cached package predates res/ persistence, honestly re-run
        # `make check` from the pristine source instead of synthesising.
        self._emit_upstream_evidence(pkg)

    def _emit_upstream_evidence(self, pkg):
        for cand in (os.path.join(pkg, "res", "upstream_test_result.json"),
                     os.path.join(pkg, "upstream_test_result.json")):
            try:
                if os.path.isfile(cand):
                    with open(cand, encoding="utf-8") as handle:
                        data = json.load(handle)
                    if (data.get("status") == "passed"
                            and int(data.get("discovered", 0)) > 0
                            and int(data.get("executed", 0)) == int(data.get("discovered", 0))
                            and int(data.get("passed", 0)) == int(data.get("discovered", 0))
                            and int(data.get("failed", 0)) == 0
                            and int(data.get("skipped", 0)) == 0):
                        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(data))
                        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(data))
                        self.output.info("[hmbs] re-emitted upstream result from %s" % cand)
                        return
                    self.output.warning("[hmbs] persisted upstream result invalid: %s" % cand)
            except (OSError, ValueError, TypeError, KeyError) as exc:
                self.output.warning("[hmbs] read %s failed: %s" % (cand, exc))
        self.output.info("[hmbs] no persisted upstream result; re-running make check from source")
        data = self._rerun_upstream_make_check()
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(data))
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(data))
        if data.get("status") != "passed":
            raise ConanException("dawgdic upstream make check failed: %s" % data)

    def _rerun_upstream_make_check(self):
        # Honest fallback for stale cached packages: fetch the pristine
        # dawgdic_0.4.5.orig.tar.gz (same URLs/sha256 as conandata.yml),
        # in-source configure + make + make check, parse Automake counts.
        urls = [
            "https://mirrors.edge.kernel.org/debian/pool/main/d/dawgdic/dawgdic_0.4.5.orig.tar.gz",
            "https://archive.ubuntu.com/ubuntu/pool/universe/d/dawgdic/dawgdic_0.4.5.orig.tar.gz",
            "https://ftp.debian.org/debian/pool/main/d/dawgdic/dawgdic_0.4.5.orig.tar.gz",
            "https://deb.debian.org/debian/pool/main/d/dawgdic/dawgdic_0.4.5.orig.tar.gz",
        ]
        sha256 = "fa54143c4bbf25abc5b1e1e0ffaefd1c3388a921558625b8cd2c5066dff179ed"
        tmpdir = self._writable_tmpdir()
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = tmpdir
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            pass
        work = os.path.join(self.build_folder or os.getcwd(), "upstream_rerun")
        try:
            if os.path.isdir(work):
                shutil.rmtree(work, ignore_errors=True)
            os.makedirs(work, exist_ok=True)
        except OSError:
            pass
        archive = os.path.join(work, "dawgdic_0.4.5.orig.tar.gz")
        last_err = None
        for url in urls:
            try:
                self.output.info("[hmbs] fetching upstream source: %s" % url)
                req = urllib.request.Request(url, headers={"User-Agent": "hmbs-test-package/1.0"})
                with urllib.request.urlopen(req, timeout=60) as resp, open(archive, "wb") as out:
                    shutil.copyfileobj(resp, out)
                digest = hashlib.sha256()
                with open(archive, "rb") as handle:
                    for chunk in iter(lambda: handle.read(65536), b""):
                        digest.update(chunk)
                if digest.hexdigest() != sha256:
                    raise ConanException("upstream tarball sha256 mismatch from %s" % url)
                last_err = None
                break
            except Exception as exc:  # noqa: BLE001 - try next mirror
                last_err = exc
                self.output.warning("[hmbs] download failed %s: %s" % (url, exc))
                continue
        if last_err is not None or not os.path.isfile(archive):
            raise ConanException("upstream source download failed: %s" % last_err)
        src = os.path.join(work, "src")
        os.makedirs(src, exist_ok=True)
        with tarfile.open(archive, "r:gz") as tar:
            tar.extractall(src)
        # Strip single top-level dir (strip_root=True equivalent).
        try:
            entries = [os.path.join(src, n) for n in os.listdir(src)]
            if len(entries) == 1 and os.path.isdir(entries[0]):
                top = entries[0]
                for name in os.listdir(top):
                    shutil.move(os.path.join(top, name), src)
                shutil.rmtree(top, ignore_errors=True)
        except OSError:
            pass
        # Minimal OHOS patches mirrored from the main recipe (no test change).
        try:
            cfg = os.path.join(src, "configure")
            if os.path.isfile(cfg):
                with open(cfg, "r", encoding="utf-8", errors="replace") as handle:
                    content = handle.read()
                orig = content
                if "umask 077" in content:
                    content = content.replace("umask 077", "umask 022")
                old_pwd = "ac_pwd=`pwd` && test -n \"$ac_pwd\" &&"
                if old_pwd in content:
                    content = content.replace(
                        old_pwd,
                        "ac_pwd=`pwd` 2>/dev/null || ac_pwd=\"$PWD\"\ntest -n \"$ac_pwd\" &&", 1)
                if content != orig:
                    with open(cfg, "w", encoding="utf-8") as handle:
                        handle.write(content)
        except OSError:
            pass
        bash = (os.environ.get("CONFIG_SHELL") or shutil.which("bash")
                or "/data/service/hnp/bin/bash")
        env = os.environ.copy()
        env["TMPDIR"] = tmpdir
        env["TMP"] = tmpdir
        env["TEMP"] = tmpdir
        env["SHELL"] = bash
        env["CONFIG_SHELL"] = bash
        # Prefer the same compiler the consumer test just used.
        try:
            exes = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
            if isinstance(exes, dict):
                if exes.get("c"):
                    env["CC"] = exes["c"]
                if exes.get("cpp") or exes.get("c++"):
                    env["CXX"] = exes.get("cpp") or exes.get("c++")
        except Exception:
            pass
        env.setdefault("CC", env.get("CC") or shutil.which("clang") or "clang")
        env.setdefault("CXX", env.get("CXX") or shutil.which("clang++") or "clang++")

        def _sh(cmd, cwd):
            self.output.info("[hmbs] rerun: %s" % cmd)
            proc = subprocess.run([bash, "-c", cmd], cwd=cwd, env=env,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  text=True, timeout=600)
            tail = (proc.stdout or "").splitlines()[-20:]
            for line in tail:
                self.output.info(line)
            if proc.returncode != 0:
                raise ConanException("upstream rerun step failed [%s]: %s"
                                     % (cmd, "\n".join(tail)[-2000:]))
            return proc.stdout or ""

        _sh('"%s" ./configure --no-create' % bash, src)
        # Redirect config.status mktemp off HMDFS-unwritable ./confXXXXXX.
        cs_file = os.path.join(src, "config.status")
        if os.path.isfile(cs_file):
            try:
                with open(cs_file, "r", encoding="utf-8", errors="replace") as handle:
                    cs = handle.read()
                fixed = os.path.join(tmpdir, "dawgdic-rerun-cs-tmp")
                try:
                    if os.path.isdir(fixed):
                        shutil.rmtree(fixed, ignore_errors=True)
                    os.makedirs(fixed, exist_ok=True)
                except OSError:
                    pass
                cs = re.sub(r'tmp=`\(umask 077 && mktemp -d "\./confXXXXXX"\) 2>/dev/null`',
                            "tmp=%s" % fixed, cs)
                cs = re.sub(r"tmp=\./conf\$\$-\$RANDOM", "tmp=%s" % fixed, cs)
                cs = cs.replace("umask 077", "umask 022")
                with open(cs_file, "w", encoding="utf-8") as handle:
                    handle.write(cs)
                try:
                    os.chmod(cs_file, 0o755)
                except OSError:
                    pass
            except OSError:
                pass
        _sh('"%s" ./config.status' % bash, src)
        _sh("make -j1", src)
        check_out = _sh('make -j1 check SHELL="%s"' % bash, src)
        self.output.info("=== upstream rerun make check (tail) ===")
        for line in check_out.splitlines()[-30:]:
            self.output.info(line)
        # Falsification guard: reference answers must be non-empty.
        for ans in ("test/dictionary-answer", "test/completer-answer",
                    "test/ranked-completer-answer"):
            p = os.path.join(src, ans)
            try:
                if (not os.path.isfile(p)) or os.path.getsize(p) == 0:
                    raise ConanException("upstream fixture empty/missing: %s" % ans)
            except OSError as exc:
                raise ConanException("upstream fixture check failed: %s" % exc)

        def _num(pattern):
            m = re.search(pattern, check_out, flags=re.MULTILINE)
            return int(m.group(1)) if m else None

        total = _num(r"^# TOTAL:\s*(\d+)")
        passed = _num(r"^# PASS:\s*(\d+)")
        skipped = _num(r"^# SKIP:\s*(\d+)")
        xfail = _num(r"^# XFAIL:\s*(\d+)")
        failed = _num(r"^# FAIL:\s*(\d+)")
        xpass = _num(r"^# XPASS:\s*(\d+)")
        error = _num(r"^# ERROR:\s*(\d+)")
        if total is None:
            passed = len(re.findall(r"^PASS:\s*\S+", check_out, flags=re.MULTILINE))
            failed = len(re.findall(r"^FAIL:\s*\S+", check_out, flags=re.MULTILINE))
            skipped = len(re.findall(r"^SKIP:\s*\S+", check_out, flags=re.MULTILINE))
            total = passed + failed + skipped
            xfail, xpass, error = 0, 0, 0
        else:
            passed = passed or 0
            skipped = (skipped or 0) + (xfail or 0)
            failed = (failed or 0) + (xpass or 0) + (error or 0)
        executed = passed + failed + skipped
        if total == 0:
            total = executed
        ok = total > 0 and executed == total and failed == 0
        status = "passed" if (ok and skipped == 0) else "failed"
        return {"status": status, "framework": "automake",
                "command": "make -j1 check SHELL=bash (test_package rerun)",
                "discovered": total, "executed": executed,
                "passed": passed, "failed": failed, "skipped": skipped}
