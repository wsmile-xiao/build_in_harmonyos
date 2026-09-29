#!/usr/bin/env python3
"""Conan recipe for manifold 3.4.1 (elalish/manifold).

manifold is a C++17 geometry library operating on manifold triangle meshes.
CMake build. Optional features (TBB/Python/JS/TRACY/ASSIMP/Fuzz) are all OFF
on HarmonyOS; only the core library + CrossSection(2D) + C FFI bindings + the
GTest test-suite are built.

OHOS notes:
- Upstream would FetchContent (git clone) GTest and Clipper2 when
  MANIFOLD_DOWNLOADS=ON, but git clone is unavailable on the OHOS true device.
  We set MANIFOLD_DOWNLOADS=OFF and provide both via Conan (CMakeDeps +
  find_package): gtest/1.17.0.2 (test-only, invisible to consumers) and
  clipper2/2.0.1 (PRIVATE link for CrossSection, pimpl-isolated from public
  headers but reachable for static-link consumers via cpp_info.requires).
- E092: CMake has no OHOS platform module, but we deliberately do NOT pin
  CMAKE_SYSTEM_NAME (unlike clipper2): manifold discovers its GTest suite via
  gtest_discover_tests, which builds/runs the test binary; forcing a system
  name would make CMake treat this native build as cross-compiling and disable
  test discovery.
- Upstream tests: MANIFOLD_TEST=ON registers every GTest case via
  gtest_discover_tests() as an individual ctest entry. build() runs ctest
  (raises on failure) and counts discovered tests from the generated
  "<target>[N]_tests.cmake" discovery files, then emits
  HMBS_UPSTREAM_TEST_RESULT (persisted to the package res/ dir so cache-hit
  test_package runs can re-emit it).
"""

import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)


class ManifoldConan(ConanFile):
    name = "manifold"
    version = "3.4.1"
    description = ("Manifold - geometry library for topological robustness on "
                   "manifold triangle meshes")
    license = "Apache-2.0"
    homepage = "https://github.com/elalish/manifold"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # Clipper2 backs CrossSection. It is a PRIVATE link dependency of
        # libmanifold (pimpl-isolated headers) but must reach static-link
        # consumers, so it stays a normal (visible) requirement and is
        # propagated via cpp_info.requires.
        self.requires("clipper2/2.0.1")
        # GTest backs the upstream test-suite only (never packaged).
        self.requires("gtest/1.17.0.2", visible=False)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "manifold is adapted for Linux and OHOS, not %s"
                % self.settings.os)

    def layout(self):
        cmake_layout(self)

    def source(self):
        # url may arrive as a candidate list (CI pre-download rewrites
        # conandata's url into [mirror, official]) - get() handles both.
        get(self, **self.conan_data["sources"], strip_root=True)

    def _resolve_compiler(self, configured, names):
        # Tool-specific candidates only (never C<->C++). Prefer the profile's
        # configured absolute path when it exists (CI workers), otherwise
        # resolve via PATH or the true-device migrated ~/usr/local/bin.
        if configured and os.path.exists(configured):
            return configured
        for name in names:
            found = shutil.which(name)
            if found:
                return found
        home_bin = os.path.join(os.path.expanduser("~"), "usr", "local", "bin")
        for name in names:
            cand = os.path.join(home_bin, name)
            if os.path.exists(cand):
                return cand
        return configured or names[0]

    def generate(self):
        tc = CMakeToolchain(self)
        # NOTE: we intentionally do NOT force CMAKE_SYSTEM_NAME=Linux on OHOS
        # (unlike clipper2). manifold registers its GTest suite through
        # gtest_discover_tests, which runs the test binary at build time;
        # forcing a system name makes CMake treat this native build as
        # cross-compiling and can disable test discovery. zydis (a ctest
        # recipe) also leaves the system name alone on OHOS.
        # Pin a real compiler so project() does not fail on a stale profile
        # path pointing at a migrated toolchain location.
        try:
            _compilers = self.conf.get("tools.build:compiler_executables",
                                       default=None)
        except Exception:
            _compilers = None
        if not isinstance(_compilers, dict):
            _compilers = {}
        _cxx = self._resolve_compiler(_compilers.get("cpp"),
                                      ("clang++", "c++"))
        _c = self._resolve_compiler(_compilers.get("c"), ("clang", "cc"))
        if _c:
            tc.cache_variables["CMAKE_C_COMPILER"] = _c
        if _cxx:
            tc.cache_variables["CMAKE_CXX_COMPILER"] = _cxx
        # Let gtest_discover_tests find Python (injected tool directory).
        py = (os.getenv("HMBS_PYTHON3")
              or self.conf.get("user.hmbs:python3_path", None))
        if py and os.path.exists(py):
            tc.cache_variables["Python3_EXECUTABLE"] = py
        elif shutil.which("python3"):
            tc.cache_variables["Python3_EXECUTABLE"] = shutil.which("python3")

        # Manifold feature toggles (all optional deps off for OHOS).
        tc.variables["BUILD_SHARED_LIBS"] = (
            "ON" if self.options.shared else "OFF")
        tc.variables["MANIFOLD_TEST"] = True
        tc.variables["MANIFOLD_CROSS_SECTION"] = True
        tc.variables["MANIFOLD_CBIND"] = True
        tc.variables["MANIFOLD_PAR"] = False
        tc.variables["MANIFOLD_PYBIND"] = False
        tc.variables["MANIFOLD_JSBIND"] = False
        tc.variables["MANIFOLD_STRICT"] = False
        tc.variables["MANIFOLD_DOWNLOADS"] = False
        tc.variables["MANIFOLD_FUZZ"] = False
        tc.variables["TRACY_ENABLE"] = False
        tc.variables["TRACY_MEMORY_USAGE"] = False
        tc.variables["ASSIMP_ENABLE"] = False
        tc.variables["MANIFOLD_USE_BUILTIN_CLIPPER2"] = False
        tc.generate()
        # Provide GTest/Clipper2 find_package configs to manifold's CMake.
        CMakeDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_tests()

    def _count_ctest(self):
        # Deterministic discovered count: manifold registers its upstream
        # GTest suite via gtest_discover_tests(), which at build time emits
        # one "<target>[N]_tests.cmake" discovery file per test executable.
        # That file contains the individual add_test(...) entries (the ctest
        # -N total); the surrounding CTestTestfile.cmake only include()s it
        # and carries no add_test() of its own here. Counting the discovery
        # files therefore gives exactly one ctest entry per registered case.
        discovered = 0
        bf = getattr(self, "build_folder", None) or ""
        for root, _ds, files in os.walk(bf):
            for fn in files:
                # gtest_discover_tests outputs "<target>[<n>]_tests.cmake".
                if fn.endswith("_tests.cmake"):
                    try:
                        with open(os.path.join(root, fn),
                                  encoding="utf-8",
                                  errors="replace") as handle:
                            for line in handle:
                                if line.lstrip().startswith("add_test("):
                                    discovered += 1
                    except Exception:
                        continue
        return discovered

    def _hmbs_emit_upstream(self, payload):
        line = "HMBS_UPSTREAM_TEST_RESULT=%s" % json.dumps(
            payload, separators=(",", ":"))
        self.output.info(line)
        try:
            print(line, flush=True)
        except Exception:
            pass
        try:
            bf = getattr(self, "build_folder", None)
            if bf:
                with open(os.path.join(bf, "hmbs_upstream.json"),
                          "w", encoding="utf-8") as f:
                    json.dump(payload, f)
        except Exception as e:
            self.output.warning("HMBS diag persist upstream failed: %s" % e)
        return line

    def _run_upstream_tests(self):
        # cmake.test() runs `ctest --output-on-failure` in the build folder
        # and raises on any failure, so reaching here means every discovered
        # GTest case (registered by gtest_discover_tests) ran and passed.
        cmake = CMake(self)
        cmake.test()
        discovered = self._count_ctest()
        if discovered <= 0:
            # No registered ctest entries at all: fail loudly rather than
            # fabricate a pass (upstream MANIFOLD_TEST suite must register
            # tests).
            self._hmbs_emit_upstream({
                "status": "failed",
                "framework": "ctest",
                "command": "ctest --output-on-failure",
                "discovered": 0,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
            })
            raise ConanInvalidConfiguration(
                "manifold: ctest reported 0 discovered tests (upstream "
                "MANIFOLD_TEST suite did not register) - refusing to "
                "fabricate a pass")
        self._hmbs_emit_upstream({
            "status": "passed",
            "framework": "ctest",
            "command": "ctest --output-on-failure",
            "discovered": discovered,
            "executed": discovered,
            "passed": discovered,
            "failed": 0,
            "skipped": 0,
        })

    def package(self):
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        # Carry real upstream result into the package so cache-hit test_package
        # runs can re-emit evidence without re-running the build.
        try:
            src = os.path.join(self.build_folder, "hmbs_upstream.json")
            if os.path.isfile(src):
                dst = os.path.join(self.package_folder, "res",
                                   "hmbs_upstream.json")
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copyfile(src, dst)
            else:
                self.output.warning(
                    "HMBS diag hmbs_upstream.json missing in package()")
        except Exception as e:
            self.output.warning("HMBS diag package upstream copy failed: %s"
                                % e)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "manifold")
        self.cpp_info.set_property("cmake_target_name", "manifold::manifold")
        self.cpp_info.set_property("pkg_config_name", "manifold")
        # Static libmanifold references Clipper2 symbols (CrossSection), so
        # downstream static links need clipper2 propagated.
        self.cpp_info.requires = ["clipper2::clipper2"]
        self.cpp_info.libs = ["manifold"]
        self.cpp_info.bindirs = ["bin"]
