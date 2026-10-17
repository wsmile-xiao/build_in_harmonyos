#!/usr/bin/env python3
"""Conan test_package for libiksemel 1.4.

Single-file consumer test compiled directly with the PATH compiler
(libmseed precedent): CMakeToolchain/CMake configure is fragile on the
OHOS worker (absolute profile compiler path, no Platform/HarmonyOS
module), while a direct -I/-L/-l compile of test.c is robust.
Upstream evidence built by conanfile.py build() is re-emitted here so it
survives Conan cache hits.
"""

import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class LibiksemelTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _pick_writable_tmpdir(self, fallback_sub=".hmbs-tmp"):
        """Prefer HMBS-injected TMPDIR only after a real write probe.

        HMDFS ignores chmod; makedirs success alone does not prove
        writability. Probe with an actual file write, else fall back to
        a build-folder private dir (conan guarantees it writable).
        Only replaces the temp-file root; never skips tests.
        """
        cands = []
        for key in ("TMPDIR", "TMP", "TEMP"):
            try:
                val = os.environ.get(key)
            except Exception:
                val = None
            if val and val not in cands:
                cands.append(val)
        try:
            cands.append(os.path.join(self.build_folder, fallback_sub))
        except Exception:
            pass
        for cand in cands:
            if not cand:
                continue
            try:
                os.makedirs(cand, exist_ok=True)
                probe = os.path.join(cand, ".tmp-write-probe")
                with open(probe, "w", encoding="utf-8") as f:
                    f.write("ok")
                try:
                    os.unlink(probe)
                except OSError:
                    pass
                return cand
            except OSError:
                continue
        return cands[0] if cands else None

    def _pick_executable_cc(self):
        import glob as _glob
        try:
            ccs = self.conf.get("tools.build:compiler_executables", default={})
            hint = ccs.get("c", "") if isinstance(ccs, dict) else ""
        except Exception:
            hint = ""
        cands = []
        if hint and os.path.isfile(hint):
            try:
                with open(hint, "rb") as f:
                    head = f.read(2)
                if head != b"#!":
                    if self._is_elf(hint):
                        return hint
            except OSError:
                pass
            real = os.path.realpath(hint)
            if real != hint and os.path.isfile(real) and self._is_elf(real):
                return real
        for d in ("/data/service/hnp/bin",):
            try:
                for n in os.listdir(d):
                    if n.startswith("clang-") and n[6:].isdigit():
                        p = os.path.join(d, n)
                        if self._is_elf(p):
                            cands.append(p)
            except OSError:
                pass
        if not cands:
            for g in ("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/bin/clang-[0-9]*",):
                for p in sorted(_glob.glob(g)):
                    if self._is_elf(p):
                        cands.append(p)
        if cands:
            return sorted(cands)[-1]
        return shutil.which("clang") or shutil.which("cc") or "clang"

    def build(self):
        # HMBS readonly_tmp: compiler temp files must avoid readonly /tmp.
        _tmp = self._pick_writable_tmpdir()
        if _tmp:
            os.environ["TMPDIR"] = _tmp
            os.environ["TMP"] = _tmp
            os.environ["TEMP"] = _tmp
            self.output.info("test_package using writable TMPDIR=%s" % _tmp)
        dep = self.dependencies["libiksemel"]
        includes = " ".join('"-I%s"' % p for p in dep.cpp_info.includedirs)
        libdirs = " ".join('"-L%s"' % p for p in dep.cpp_info.libdirs)
        libs = " ".join("-l%s" % lib for lib in dep.cpp_info.libs)
        syslibs = " ".join("-l%s" % lib for lib in dep.cpp_info.system_libs)
        # Prefer a directly-executable clang ELF: the profile wrapper
        # (/data/service/hnp/bin/clang) may be inaccessible on some workers.
        cc = self._pick_executable_cc()
        src = os.path.join(self.source_folder, "test.c")
        out = os.path.join(self.build_folder, "test_libiksemel")
        self.run('%s -O2 "%s" -o "%s" %s %s %s %s'
                 % (cc, src, out, includes, libdirs, libs, syslibs))

    def test(self):
        if not can_run(self):
            self.output.info("Cross-building: skip runtime execution")
            return
        # Same writable TMPDIR for the runtime step (no /tmp writes).
        _tmp = self._pick_writable_tmpdir()
        if _tmp:
            os.environ["TMPDIR"] = _tmp
            os.environ["TMP"] = _tmp
            os.environ["TEMP"] = _tmp
        test_binary = os.path.join(self.build_folder, "test_libiksemel")
        if not os.path.isfile(test_binary):
            for root, _, files in os.walk(self.build_folder):
                if "test_libiksemel" in files:
                    test_binary = os.path.join(root, "test_libiksemel")
                    break
        if not os.path.isfile(test_binary):
            raise ConanException("test_libiksemel binary not found after build")
        self.run('"%s"' % test_binary, env="conanrun")
        discovered = 9
        tp_result = {
            "executed": True,
            "passed": True,
            "command": "./test_libiksemel (9 API groups)",
            "discovered": discovered,
            "passedCount": discovered,
        }
        print("HMBS_TEST_PACKAGE_RESULT=%s" % json.dumps(tp_result), flush=True)
        self.output.info("HMBS_TEST_PACKAGE_RESULT=%s" % json.dumps(tp_result))
        dep = self.dependencies["libiksemel"]
        result_path = os.path.join(dep.package_folder, "res", "upstream_test_result.json")
        if not os.path.isfile(result_path):
            raise ConanException(
                "upstream_test_result.json not found in package (%s) - "
                "upstream tests did not run during build(); refusing to pass "
                "silently" % result_path
            )
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
