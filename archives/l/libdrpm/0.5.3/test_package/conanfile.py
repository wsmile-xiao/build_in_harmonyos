#!/usr/bin/env python3
"""Conan test_package for libdrpm 0.5.3."""
import json
import os
import tempfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class LibdrpmTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _writable_tmpdir(self, phase=""):
        # Mirror of the main recipe: /tmp is read-only on HMBS
        # preflight. Probe real writability, reuse injected TMPDIR,
        # else fall back to build_folder/tmp. No test skipped.
        def _writable(p):
            try:
                if not p or not os.path.isdir(p):
                    return False
                fd, tmp = tempfile.mkstemp(prefix=".hmbs-probe-", dir=p)
                try:
                    os.close(fd)
                finally:
                    try:
                        os.unlink(tmp)
                    except OSError:
                        pass
                return True
            except Exception:
                return False

        for key in ("TMPDIR", "TMP", "TEMP"):
            val = os.environ.get(key)
            if val and _writable(val):
                tmpdir = val
                break
        else:
            try:
                base = self.build_folder or os.getcwd()
            except Exception:
                base = os.getcwd()
            tmpdir = os.path.join(base, "tmp")
            try:
                os.makedirs(tmpdir, exist_ok=True)
            except Exception:
                pass
            if not _writable(tmpdir):
                tmpdir = tempfile.mkdtemp(prefix="hmbs-tmp-")
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = tmpdir
        os.environ.setdefault("CMAKE_BUILD_PARALLEL_LEVEL", "1")
        os.environ.setdefault("CTEST_PARALLEL_LEVEL", "1")
        # Mirror main recipe OOM guard (2026-09-23): single job plus
        # single-thread (de)compression so test subprocess forks stay
        # light on the constrained device. setdefault: no overwrite.
        os.environ.setdefault("MAKEFLAGS", "-j1")
        os.environ.setdefault("XZ_OPT", "-T1")
        os.environ.setdefault("GZIP", "-1")
        return tmpdir

    def build(self):
        self._writable_tmpdir("test-build")
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        self._writable_tmpdir("test-run")
        if not can_run(self):
            self.output.info("cross-building: skip runtime test")
            return
        # NOTE: the package defaults to static, so the consumer links
        # statically and performs no runtime .so lookup (immune to the
        # stale system libdrpm.so.0 and the sandbox dlopen
        # "Permission denied"). Plain run; no LD_* or dlopen tricks.
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_drpm")
        if not os.path.isabs(test_bin):
            test_bin = os.path.join(self.build_folder, test_bin)
        if not os.path.isfile(test_bin):
            import glob as _gb
            for h in _gb.glob(os.path.join(self.build_folder, "**", "test_drpm*"), recursive=True):
                try:
                    if not os.path.isfile(h) or h.endswith((".c", ".log", ".cmake")):
                        continue
                    with open(h, "rb") as fh:
                        if fh.read(4) == b"\x7fELF":
                            test_bin = h
                            break
                except OSError:
                    continue
        log_path = os.path.join(self.build_folder, "test_drpm.log")
        cmd = '"%s" > "%s" 2>&1' % (test_bin, log_path)
        try:
            self.run(cmd, env="conanrun")
            rc = 0
        except ConanException:
            rc = 1
        out = ""
        try:
            with open(log_path, "r", encoding="utf-8", errors="replace") as fh:
                out = fh.read()
        except OSError:
            out = ""
        self.output.info("test output:\n" + out)
        # test_drpm.c prints one "ok:" line per passing check (7 checks) plus
        # a final "PASS:" summary line; count lines starting with "ok:"
        # (deterministic line scan of the framework output, one line per check).
        discovered = 7
        passed_count = sum(1 for _line in out.splitlines() if _line.strip().startswith("ok:"))
        ok = rc == 0 and "PASS: all libdrpm consumer checks passed" in out
        marker = {
            "executed": True,
            "passed": bool(ok and passed_count == discovered),
            "command": "./test_drpm (drpm consumer-api checks)",
            "discovered": discovered,
            "passedCount": passed_count,
        }
        msg = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker)
        print(msg, flush=True)
        self.output.info(msg)
        self._emit_upstream_result()
        if not marker["passed"]:
            raise ConanException(
                "test_package failed: %d/%d checks passed" % (passed_count, discovered)
            )

    def _emit_upstream_result(self):
        dep = self.dependencies[self.tested_reference_str.split("/")[0]]
        path = os.path.join(dep.package_folder, "res", "upstream_test_result.json")
        if not os.path.isfile(path):
            raise ConanException("upstream_test_result.json not found in package")
        with open(path, "r", encoding="utf-8") as fh:
            result = json.load(fh)
        msg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result)
        print(msg, flush=True)
        self.output.info(msg)
        if not isinstance(result, dict) or result.get("status") != "passed":
            raise ConanException("upstream test evidence invalid: %s" % (result,))
