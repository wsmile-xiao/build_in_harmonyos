#!/usr/bin/env python3
"""Conan test_package — spglib 2.7.0 consumer test.

Direct clang compile+run against the packaged headers/libs (no CMake
project() call, so the OHOS "compiler identification is unknown"
failure mode cannot recur here either). Runs the test binary, counts
the per-check "CHECK-OK:" lines for the HMBS_TEST_PACKAGE_RESULT
machine-evidence marker (exit-0-alone is not proof: 7 CHECK-OK lines
are required for a pass).

Upstream evidence: the measured ctest result persisted by the main
recipe (package/res/hmbs_upstream.json) is re-emitted as
HMBS_UPSTREAM_TEST_RESULT on every run so cache-hit rounds (build()
skipped) still carry per-run upstream evidence.
"""

import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building
from conan.tools.cmake import cmake_layout

CONSUMER_CHECK_COUNT = 7


class SpglibTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _ensure_writable_tmp(self):
        # Same readonly_tmp handling as the main recipe: prefer the
        # HMBS-injected dir when it probes writable, else use a private
        # build_folder dir. Probe with a real file write (HMDFS ignores
        # chmod/os.access, so isdir alone is not sufficient).
        candidates = []
        for key in ("HMBS_TMPDIR", "TMPDIR", "TMP", "TEMP"):
            value = os.environ.get(key)
            if value and value not in candidates:
                candidates.append(value)
        try:
            build_folder = self.build_folder
        except Exception:
            build_folder = None
        if build_folder:
            candidates.append(os.path.join(build_folder, "hmbs-tmp"))
        chosen = None
        for cand in candidates:
            try:
                os.makedirs(cand, exist_ok=True)
                probe = os.path.join(cand, ".hmbs-tmp-probe")
                with open(probe, "w", encoding="utf-8") as handle:
                    handle.write("ok")
                os.unlink(probe)
                chosen = cand
                break
            except OSError:
                continue
        if chosen is None:
            chosen = candidates[0] if candidates else os.path.join(
                build_folder or ".", "hmbs-tmp")
            os.makedirs(chosen, exist_ok=True)
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = chosen
        return chosen

    def _cc(self):
        # 5th-cycle simplification: no worker-specific absolute paths or
        # SDK/harmonybrew globs (those belong to the retired generate-time
        # hunting family). At build()/test time the profile buildenv PATH
        # is active, so conf-if-present else PATH lookup with a --version
        # run is sufficient and portable.
        try:
            exes = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
        except Exception:
            exes = {}
        candidates = []
        if exes.get("c"):
            candidates.append(exes.get("c"))
        for env_key in ("CC", "HMBS_CC"):
            val = os.environ.get(env_key)
            if val and val not in candidates:
                candidates.append(val)
        for bare in ("clang", "cc"):
            found = shutil.which(bare)
            if found and found not in candidates:
                candidates.append(found)
        for cand in candidates:
            if not cand:
                continue
            try:
                if not os.path.isfile(str(cand)):
                    continue
            except Exception:
                continue
            try:
                proc = subprocess.run(
                    [str(cand), "--version"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    timeout=30,
                    env=dict(os.environ),
                )
                if proc.returncode == 0 and (proc.stdout or "").strip():
                    return str(cand)
            except Exception:
                continue
        path = exes.get("c")
        if path:
            return shutil.which(os.path.basename(path)) or path
        cxx_bin = shutil.which("clang++") or shutil.which("c++")
        if cxx_bin:
            try:
                proc = subprocess.run(
                    [cxx_bin, "--version"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    timeout=30,
                    env=dict(os.environ),
                )
                if proc.returncode == 0 and (proc.stdout or "").strip():
                    return cxx_bin
            except Exception:
                pass
        return shutil.which("clang") or "clang"

    def build(self):
        self._ensure_writable_tmp()
        incs = []
        libdirs = []
        for _ref, dep in self.dependencies.items():
            try:
                incs += ["-I" + p for p in dep.cpp_info.includedirs]
            except Exception:
                pass
            try:
                for p in dep.cpp_info.libdirs:
                    if os.path.isdir(p):
                        libdirs.append("-L" + p)
            except Exception:
                pass
        try:
            libs = " ".join("-l" + lib for lib in self.dependencies["spglib"].cpp_info.libs)
        except Exception:
            libs = "-lsymspg"
        syslibs = ""
        try:
            syslibs = " ".join("-l" + lib for lib in self.dependencies["spglib"].cpp_info.system_libs)
        except Exception:
            syslibs = "-lm"
        cc = self._cc()
        src = os.path.join(self.source_folder, "test.c")
        out = os.path.join(self.build_folder, "test_spglib")
        self.run('%s "%s" -o "%s" %s %s %s %s' % (
            cc, src, out, " ".join(incs), " ".join(libdirs), libs, syslibs))

    def _test_env(self):
        env = dict(os.environ)
        libpaths = []
        for _ref, dep in self.dependencies.items():
            try:
                for p in dep.cpp_info.libdirs:
                    if os.path.isdir(p) and p not in libpaths:
                        libpaths.append(p)
            except Exception:
                pass
        if libpaths:
            prev = env.get("LD_LIBRARY_PATH", "")
            env["LD_LIBRARY_PATH"] = os.pathsep.join(libpaths + ([prev] if prev else []))
        return env

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: compile/link test completed")
            return
        self._ensure_writable_tmp()
        self._run_consumer_binary(raise_on_failure=True)
        self._emit_upstream_marker()
        self.output.info("spglib consumer test_package passed")

    def _run_consumer_binary(self, raise_on_failure):
        bin_path = os.path.join(self.build_folder, "test_spglib")
        if not os.path.isfile(bin_path):
            raise ConanException("test binary missing: %s" % bin_path)
        proc = subprocess.run(
            [bin_path],
            env=self._test_env(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=300,
        )
        output = proc.stdout or ""
        self.output.info(output[-2000:])
        ok_count = output.count("CHECK-OK:")
        marker = {
            "executed": True,
            "passed": proc.returncode == 0 and ok_count == CONSUMER_CHECK_COUNT,
            "command": bin_path,
            "discovered": CONSUMER_CHECK_COUNT,
            "passedCount": ok_count,
        }
        line = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False)
        self.output.info(line)
        try:
            print(line, flush=True)
        except Exception:
            pass
        if not marker["passed"] and raise_on_failure:
            raise ConanException(
                "consumer test failed: rc=%s ok=%s/%s"
                % (proc.returncode, ok_count, CONSUMER_CHECK_COUNT)
            )

    def _emit_upstream_marker(self):
        pkg_folder = None
        try:
            pkg_folder = self.dependencies[self.tested_reference_str].package_folder
        except Exception:
            try:
                pkg_folder = self.dependencies["spglib"].package_folder
            except Exception:
                pkg_folder = None
        up_path = None
        if pkg_folder:
            up_path = os.path.join(str(pkg_folder), "res", "hmbs_upstream.json")
        try:
            if up_path and os.path.isfile(up_path):
                with open(up_path, "r", encoding="utf-8") as handle:
                    obj = json.loads(handle.read())
                if (
                    isinstance(obj, dict)
                    and obj.get("status") == "passed"
                    and int(obj.get("discovered", 0)) > 0
                    and int(obj.get("executed", 0)) > 0
                ):
                    line = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(
                        obj, ensure_ascii=False
                    )
                    self.output.info(line)
                    try:
                        print(line, flush=True)
                    except Exception:
                        pass
                    return
            self.output.warning(
                "spglib test: persisted upstream evidence missing or invalid at %s; "
                "cannot re-emit" % up_path
            )
        except (OSError, ValueError) as exc:
            self.output.warning(
                "spglib test: re-emit upstream evidence failed: %r" % exc
            )
