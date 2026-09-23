#!/usr/bin/env python3
"""Conan test_package — libm2k 0.9.0 (R34 real-API test).

Real consumer-side verification without ADALM2000 hardware:
  * test_version: ContextBuilder::getVersion() non-empty, getAllContexts()
    enumeration does not crash, version string matches "0.9.0".
  * test_context: getContextsInfo() enumeration, contextOpen/m2kOpen with
    empty/unknown URI returns nullptr without crashing (negative path).

Both binaries exit non-zero on assertion failure so conan create reflects
a real regression. Upstream's Python/hardware tests (tests/main.py) require
ADALM2000 or iio-emu and are documented as skipped on OHOS
(see notes.md and MANIFEST.yml).
"""

import json
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # libm2k public headers expose <iio.h> (utils.hpp:25), so the
        # consumer's include path must contain libiio. The upstream
        # libm2kConfig.cmake does not call find_dependency(libiio), so we
        # request libiio explicitly to guarantee CMakeDeps/PkgConfig files
        # are generated for the test_package's fallback logic.
        self.requires("libiio/0.25")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            for exe in ("test_version", "test_context"):
                bin_path = os.path.join(self.cpp.build.bindir, exe)
                # Some generators use build_folder directly
                alt = os.path.join(self.build_folder, exe)
                if os.path.isfile(bin_path):
                    self.run(f'"{bin_path}"', env="conanrun")
                elif os.path.isfile(alt):
                    self.run(f'"{alt}"', env="conanrun")
                else:
                    # CMake layout puts binaries in build subdir
                    search = os.path.join(self.build_folder, "build", exe)
                    if os.path.isfile(search):
                        self.run(f'"{search}"', env="conanrun")
                    else:
                        self.run(f'"{bin_path}"', env="conanrun")
            # HMBS evidence: test_package executed 2 binaries successfully.
            # Use dual-channel (print + self.output.info) so hmbs captures
            # regardless of stdout buffering.
            discovered = 2
            passed_count = 2
            # command reflects the real binaries executed; hmbs extracts
            # discovered/passedCount from this marker.
            tp_marker = {
                "executed": True,
                "passed": True,
                "command": "./test_version && ./test_context",
                "discovered": discovered,
                "passedCount": passed_count,
            }
            tp_msg = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(tp_marker, ensure_ascii=False)
            print(tp_msg, flush=True)
            self.output.info(tp_msg)
            # Re-emit upstream marker every run — build() is skipped on cache hits.
            # Prefer the real vendor-run JSON persisted in package res/ (ctre pattern).
            upstream_marker = None
            # Try to load persisted hmbs_upstream.json from package
            for cand in [
                os.path.join(self.cpp.package.bindir, "..", "res", "hmbs_upstream.json"),
                os.path.join(self.cpp.package.package_folder, "res", "hmbs_upstream.json") if hasattr(self.cpp.package, "package_folder") else None,
            ]:
                if cand and os.path.isfile(os.path.normpath(cand)):
                    try:
                        with open(os.path.normpath(cand), "r", encoding="utf-8") as f:
                            upstream_marker = json.load(f)
                        break
                    except Exception:
                        pass
            # Fallback: search in conan cache package folder via dependencies
            if upstream_marker is None:
                try:
                    # The tested package's res is available via deps_cpp_info
                    for dep in self.dependencies.values():
                        if dep.ref.name == "libm2k":
                            p = os.path.join(dep.package_folder, "res", "hmbs_upstream.json")
                            if os.path.isfile(p):
                                with open(p, "r", encoding="utf-8") as f:
                                    upstream_marker = json.load(f)
                                break
                except Exception:
                    pass
            if upstream_marker is None:
                # Last resort: hardware incomplete (should not happen after vendor fix) — status must be incomplete when gaps exist
                upstream_marker = {
                    "status": "incomplete",
                    "framework": "unittest",
                    "command": "python -m unittest discover -s tests -p 'm2k*.py' -v",
                    "discovered": 59,
                    "executed": 0,
                    "passed": 0,
                    "failed": 0,
                    "skipped": 0,
                    "reason": "59 upstream tests require ADALM2000 hardware or iio-emu emulator (tests/open_context.py m2kOpen). Fallback — vendor run not found, marked incomplete.",
                    "gaps": [
                        {
                            "count": 59,
                            "category": "ohos_feature",
                            "detail": "Hardware-dependent: ADALM2000 board or iio-emu required (tests/open_context.py creates live M2k context).",
                            "evidence": "tests/open_context.py: ctx=m2kOpen('ip:192.168.2.1'); grep 'def test_' in tests/ =59; HMBS inventory N=59"
                        }
                    ],
                }
            up_msg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream_marker, ensure_ascii=False)
            print(up_msg, flush=True)
            self.output.info(up_msg)
