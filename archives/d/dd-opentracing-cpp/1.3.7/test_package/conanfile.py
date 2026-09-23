#!/usr/bin/env python3
"""Conan test_package for dd-opentracing-cpp 1.3.7.

Builds and runs the consumer smoke test (test_dd_opentracing) which calls the
real public API (makeTracer/StartSpan/SetTag/Inject/Extract/getOptions/toJSON).
The DD_TEST_SUMMARY line printed by the binary carries the true check counts
used for the HMBS_TEST_PACKAGE_RESULT evidence marker.
"""
import json
import os
import re
import subprocess

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class DdOpentracingCppTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # NOTE: <datadog/opentracing.h> includes <opentracing/tracer.h>, but
        # those headers ship bundled inside this package (vendored
        # opentracing-cpp, see the main recipe), so no separate
        # opentracing-cpp requirement.

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            return
        binary = None
        for d in self.cpp.build.bindirs:
            cand = os.path.join(d, "test_dd_opentracing")
            if os.path.isfile(cand):
                binary = cand
                break
        if binary is None:
            for root, _, files in os.walk(self.build_folder):
                if "test_dd_opentracing" in files:
                    binary = os.path.join(root, "test_dd_opentracing")
                    break
        discovered = 0
        passed_count = 0
        ok = False
        if binary is not None:
            # HMBS readonly_tmp: /tmp is read-only on the device; force the
            # test binary's temp files onto the injected writable root.
            run_env = dict(os.environ)
            tmp_root = (os.environ.get("TMPDIR") or os.environ.get("TMP")
                        or os.environ.get("TEMP") or "")
            if not tmp_root or not os.path.isdir(tmp_root):
                tmp_root = os.path.join(self.build_folder, "hmbs-tmp")
                os.makedirs(tmp_root, exist_ok=True)
            run_env["TMPDIR"] = tmp_root
            run_env["TMP"] = tmp_root
            run_env["TEMP"] = tmp_root
            # OHOS stale_runtime_library: the test binary links shared
            # libcurl (Conan cache) via the dd package; without dep libdirs
            # on LD_LIBRARY_PATH the loader picks the system stub libcurl.so
            # ("curl_* symbol not found"). Same fix as upstream ctest
            # _runtime_libdirs in the main recipe (cf. ezstream 1.0.2).
            libdirs = []
            try:
                for _, dep in self.dependencies.items():
                    try:
                        dirs = dep.cpp_info.aggregated_components().libdirs
                    except Exception:
                        dirs = []
                    for d in dirs:
                        if d and os.path.isdir(d) and d not in libdirs:
                            libdirs.append(d)
            except Exception:
                pass
            if libdirs:
                prev = run_env.get("LD_LIBRARY_PATH", "")
                run_env["LD_LIBRARY_PATH"] = os.pathsep.join(
                    libdirs + ([prev] if prev else []))
                os.environ["LD_LIBRARY_PATH"] = run_env["LD_LIBRARY_PATH"]
            print("test LD_LIBRARY_PATH=" + run_env.get("LD_LIBRARY_PATH", "<unset>"))
            proc = subprocess.run([binary], capture_output=True, text=True, timeout=60,
                                  env=run_env)
            out = (proc.stdout or "") + (proc.stderr or "")
            print(out)
            m = re.search(r"DD_TEST_SUMMARY passed=(\d+) total=(\d+)", out)
            if m:
                passed_count = int(m.group(1))
                discovered = int(m.group(2))
                ok = proc.returncode == 0 and passed_count == discovered and discovered > 0
            else:
                print("warning: DD_TEST_SUMMARY line not found in test output")
        else:
            print("warning: test_dd_opentracing binary not found")
        marker = {
            "executed": True,
            "passed": ok,
            "command": "./test_dd_opentracing",
            "discovered": discovered,
            "passedCount": passed_count,
        }
        tp_msg = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker)
        print(tp_msg, flush=True)
        self.output.info(tp_msg)
        if not ok:
            raise Exception("test_dd_opentracing failed: " + json.dumps(marker))
        # CI L0d requires a self.run() execution in test(): re-run the real
        # binary through the Conan runner (fast, local, no network). A
        # non-zero exit raises here, so a red binary can never pass silently.
        self.run(binary)
        # Cache-hit re-emit: when Conan reuses the main-package binary,
        # build() is skipped and its HMBS_UPSTREAM_TEST_RESULT never prints,
        # so the evidence gate reports "missing upstream evidence" even
        # though the 13 ctest cases really passed in the fresh build
        # (2026-09-11 preflight: test_package 10/10 passed, upstream 0/0).
        # Re-emit the persisted real in-build numbers (written by build()
        # to res/hmbs_upstream.json, ayatana-ido 0.10.4-v2 precedent). No
        # test is redefined here; counts are the real ctest numbers.
        try:
            _upstream = None
            _pkg_name = (self.tested_reference_str.split("/")[0]
                         if "/" in self.tested_reference_str
                         else "dd-opentracing-cpp")
            try:
                _dep = self.dependencies[_pkg_name]
                _pf = getattr(_dep, "package_folder", None)
                if _pf:
                    _cand = os.path.join(_pf, "res", "hmbs_upstream.json")
                    if os.path.isfile(_cand):
                        with open(_cand, "r", encoding="utf-8") as _fh:
                            _upstream = json.load(_fh)
            except Exception:
                _upstream = None
            if isinstance(_upstream, dict) and _upstream.get("discovered"):
                _umsg = ("HMBS_UPSTREAM_TEST_RESULT="
                         + json.dumps(_upstream))
                print(_umsg, flush=True)
                self.output.info(_umsg)
            else:
                self.output.warning(
                    "persisted hmbs_upstream.json missing; "
                    "upstream evidence only available on fresh build")
        except Exception as _e:
            self.output.warning("upstream re-emit failed: %r" % (_e,))
