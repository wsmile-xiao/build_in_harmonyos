#!/usr/bin/env python3
"""Conan test_package for serf 1.3.10 — Conan L1 official test.

Compiles test_serf.c against the packaged libserf-1 (plus the APR /
apr-util / OpenSSL / zlib closure) with a direct cc link — no dlopen —
so CI's L1e destructive reverse check fails at compile/link time if the
package is removed. Runs the probe (8 real API checks) and emits the
HMBS machine-evidence markers. The upstream-evidence JSON persisted by
build() into <package>/res/upstream_test_result.json is re-emitted here
so it survives Conan cache hits ("Already installed!").
CI runs this automatically via `conan create`.
"""

import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class SerfTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _ensure_writable_tmp(self):
        # [readonly_tmp]: HarmonyOS PC has read-only /tmp. Reuse the
        # HMBS-injected TMPDIR/TMP/TEMP so the compile shell (`cc ...`)
        # and the test shell (`sh -c test_serf`) never assume /tmp is
        # writable. Env-only change: test count and markers untouched.
        # Write-probe every candidate (coinor-vol/1.5.4 lesson).
        for key in ("TMPDIR", "TMP", "TEMP", "HMBS_TMPDIR", "HMBS_INSTALL"):
            val = (os.environ.get(key, "") or "").strip()
            if not val:
                continue
            try:
                os.makedirs(val, exist_ok=True)
                probe = os.path.join(val, ".hmbs-write-probe")
                with open(probe, "w", encoding="utf-8") as handle:
                    handle.write("ok")
                os.unlink(probe)
                return val
            except OSError:
                continue
        fallback = os.path.join(self.build_folder, "_tmp")
        os.makedirs(fallback, exist_ok=True)
        return fallback

    def _dep_name(self, req, dep):
        for holder in (req, dep):
            try:
                ref = getattr(holder, "ref", None)
                if ref is not None:
                    name = getattr(ref, "name", "") or ""
                    if name:
                        return name
            except Exception:
                continue
        return ""

    def build(self):
        # Header/lib closure across all deps (serf + apr + apr-util +
        # openssl + zlib + transitive). Aggregate top-level cpp_info AND
        # components: some deps expose libs via components with relative
        # dirs, which must be resolved against package_folder.
        tmpdir = self._ensure_writable_tmp()
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = tmpdir
        incs = []
        libdirs = []
        serf_libs = []
        other_libs = []
        for _req, _dep in self.dependencies.items():
            pkg = getattr(_dep, "package_folder", "") or ""
            try:
                infos = [_dep.cpp_info] + list(_dep.cpp_info.components.values())
            except Exception:
                infos = [_dep.cpp_info]
            for _info in infos:
                for p in getattr(_info, "includedirs", []):
                    a = p if os.path.isabs(p) else os.path.join(pkg, p)
                    if ("-I" + a) not in incs:
                        incs.append("-I" + a)
                for p in getattr(_info, "libdirs", []):
                    a = p if os.path.isabs(p) else os.path.join(pkg, p)
                    if ("-L" + a) not in libdirs:
                        libdirs.append("-L" + a)
            bucket = serf_libs if self._dep_name(_req, _dep) == "serf" else other_libs
            for _info in infos:
                for lib in getattr(_info, "libs", []):
                    f = "-l" + lib
                    if f not in bucket:
                        bucket.append(f)
                for lib in getattr(_info, "system_libs", []):
                    f = "-l" + lib
                    if f not in bucket:
                        bucket.append(f)
        if not serf_libs:
            # Fall back to the published library name (package_info).
            serf_libs = ["-lserf-1"]
        inc = " ".join(incs)
        libdir = " ".join(libdirs)
        extralibs = " ".join(other_libs)
        cc = shutil.which("clang") or shutil.which("cc") or "cc"
        src = os.path.join(self.source_folder, "test_serf.c")
        out = os.path.join(self.build_folder, "test_serf")
        # Direct link against -lserf-1 first (R34), dep libs after.
        self.run("%s \"%s\" -o \"%s\" %s %s %s %s" % (
            cc, src, out, inc, libdir, " ".join(serf_libs), extralibs))

    def test(self):
        if not can_run(self):
            self.output.info("Cross-building: skip runtime execution")
            return
        tmpdir = self._ensure_writable_tmp()
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = tmpdir
        test_binary = os.path.join(self.build_folder, "test_serf")
        if not os.path.isfile(test_binary):
            for root, _dirs, files in os.walk(self.build_folder):
                if "test_serf" in files:
                    test_binary = os.path.join(root, "test_serf")
                    break
        if not os.path.isfile(test_binary):
            raise ConanException("test_serf binary not found after build")
        shell = (os.environ.get("CONFIG_SHELL", "") or os.environ.get("SHELL", "")).strip()
        if not shell or ("/" in shell and not os.path.isfile(shell)):
            shell = shutil.which("bash") or shutil.which("sh") or "/bin/sh"
        self.run("%s -c '\"%s\"'" % (shell, test_binary), env="conanrun")
        discovered = 8
        tp_result = {
            "executed": True,
            "passed": True,
            "command": "./test_serf (8 API checks)",
            "discovered": discovered,
            "passedCount": discovered,
        }
        tp_line = "HMBS_TEST_PACKAGE_RESULT=%s" % json.dumps(tp_result)
        print(tp_line, flush=True)
        self.output.info(tp_line)
        # Re-emit the upstream evidence persisted by build() into
        # <package>/res/upstream_test_result.json. test_package runs on
        # every preflight even when conan skips a cached build(), so this
        # guarantees HMBS_UPSTREAM_TEST_RESULT is always present. Content
        # is the real device-run JSON, validated here (no silent skips).
        dep = self.dependencies["serf"]
        result_path = os.path.join(dep.package_folder, "res", "upstream_test_result.json")
        if not os.path.isfile(result_path):
            raise ConanException(
                "upstream_test_result.json not found in package (%s): "
                "upstream tests did not run during build(); refusing to "
                "pass silently" % result_path)
        with open(result_path, "r", encoding="utf-8") as handle:
            upstream = json.load(handle)
        for key in ("status", "framework", "command", "discovered",
                    "executed", "passed", "failed", "skipped"):
            if key not in upstream:
                raise ConanException(
                    "upstream_test_result.json missing key %r" % key)
        if not isinstance(upstream["discovered"], int) or upstream["discovered"] <= 0:
            raise ConanException(
                "upstream_test_result.json has invalid discovered=%r" % (
                    upstream.get("discovered"),))
        if upstream["executed"] < upstream["discovered"]:
            raise ConanException(
                "upstream_test_result.json executed < discovered (%r < %r)" % (
                    upstream.get("executed"), upstream.get("discovered")))
        marker_line = "HMBS_UPSTREAM_TEST_RESULT=%s" % json.dumps(
            upstream, ensure_ascii=False)
        print(marker_line, flush=True)
        self.output.info(marker_line)
