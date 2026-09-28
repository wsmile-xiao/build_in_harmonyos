#!/usr/bin/env python3
"""Conan recipe — trompeloeil 49 (header-only C++ mocking framework).

trompeloeil is a header-only C++ mocking framework (Boost Software License
1.0) with no runtime dependencies. Its upstream test suite needs Catch2 and,
for the negative compilation tests, GNU parallel.

Adaptation summary (patches: {} — no upstream source is modified):
  * Build-time network is forbidden. upstream test/CMakeLists.txt silently
    downloads catch.hpp from GitHub when no Catch2 package is found, so
    Catch2 v3 is pre-provisioned through tool_requires and its package
    folder is passed via CMAKE_PREFIX_PATH (verified: no download happens).
  * The 68 expect-to-fail translation units in compilation_errors/ are driven
    from Python: upstream check_errors.sh relies on GNU parallel, which is
    absent on OHOS. Each case runs with TMPDIR pinned to the build folder
    because /tmp is read-only on OHOS.
  * The upstream suite is executed at C++14 (default) and C++20 (adds the
    coroutine coverage in test_co_mock.cpp) inside build(), so conan create
    is a real upstream-test gate (R51).
"""
import os
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class TrompeloeilConan(ConanFile):
    name = "trompeloeil-cpp"
    version = "49"
    package_type = "header-library"
    description = ("Header-only C++ mocking framework that turns mock expectations "
                   "into compile-time and run-time testable behaviour "
                   "(rollbear/trompeloeil)")
    license = "BSL-1.0"
    homepage = "https://github.com/rollbear/trompeloeil"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("testing", "mock", "header-only", "cpp")

    # Kept for structural consistency (L0p); package_id is cleared below
    # because a header-only package is identical for every configuration.
    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # Upstream test/CMakeLists.txt falls back to downloading catch.hpp
        # from GitHub when Catch2 is not found. Provide Catch2 v3 from the
        # registry so the build never touches the network.
        self.tool_requires("catch2/3.8.1")

    def layout(self):
        basic_layout(self, src_folder="src")

    def package_id(self):
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        cc, cxx = self._compiler_paths()
        catch2_folder = self._catch2_package_folder()
        jobs = str(self._jobs())
        self._run_selftest_suite(cc, cxx, catch2_folder, "14", jobs)
        self._run_selftest_suite(cc, cxx, catch2_folder, "20", jobs)
        self._run_negative_compile_suite(cxx, "14")
        self._run_negative_compile_suite(cxx, "20")

    # ── helpers ────────────────────────────────────────────────────────

    def _compiler_paths(self):
        # R33: the compiler comes from the Conan conf, never from undefined
        # shell variables.
        exes = self.conf.get("tools.build:compiler_executables", default={})
        cc = exes.get("c") or shutil.which("clang") or "clang"
        cxx = exes.get("cpp") or shutil.which("clang++") or "clang++"
        return cc, cxx

    def _jobs(self):
        jobs = self.conf.get("tools.build:jobs", default=2)
        try:
            return max(1, int(jobs))
        except (TypeError, ValueError):
            return 2

    def _catch2_package_folder(self):
        dep = self.dependencies.build.get("catch2")
        folder = getattr(dep, "package_folder", None) if dep else None
        if not folder or not os.path.isdir(folder):
            raise ConanException(
                "catch2 tool_requires did not provide a package folder; "
                "the upstream test suite cannot run without it (a fallback "
                "would download catch.hpp at build time)")
        return folder

    def _run_selftest_suite(self, cc, cxx, catch2_folder, std, jobs):
        build_dir = os.path.join(self.build_folder, "build-cxx" + std)
        targets = ["self_test"]
        if std == "14":
            # thread_terror / custom_recursive_mutex are standalone C++14
            # upstream programs; run them once (not part of the C++20 matrix).
            targets += ["thread_terror", "custom_recursive_mutex"]
        cmake = shutil.which("cmake") or "cmake"
        self.run(
            '"{cmake}" -S "{src}" -B "{build}" '
            '-DTROMPELOEIL_BUILD_TESTS=YES -DCXX_STANDARD={std} '
            '-DCMAKE_BUILD_TYPE="{build_type}" '
            '-DCMAKE_PREFIX_PATH="{catch2}" '
            '-DCMAKE_C_COMPILER="{cc}" -DCMAKE_CXX_COMPILER="{cxx}"'.format(
                cmake=cmake, src=self.source_folder, build=build_dir, std=std,
                build_type=self.settings.build_type, catch2=catch2_folder,
                cc=cc, cxx=cxx,
            )
        )
        self.run('"{cmake}" --build "{build}" --target {targets} -j {jobs}'.format(
            cmake=cmake, build=build_dir, targets=" ".join(targets), jobs=jobs))
        for target in targets:
            binary = os.path.join(build_dir, "test", target)
            if not os.path.isfile(binary):
                raise ConanException("expected upstream test binary not found: " + binary)
            self.run('"{0}"'.format(binary))

    def _run_negative_compile_suite(self, cxx, std):
        neg_dir = os.path.join(self.source_folder, "compilation_errors")
        cases = sorted(name for name in os.listdir(neg_dir) if name.endswith(".cpp"))
        if not cases:
            raise ConanException("no compilation_errors/*.cpp cases found")
        driver = os.path.normpath(
            os.path.join(neg_dir, os.pardir, "verify_compilation_error.sh"))
        if not os.path.isfile(driver):
            raise ConanException("upstream verify_compilation_error.sh not found")
        sh = shutil.which("sh") or "/bin/sh"
        tmpdir = os.path.join(self.build_folder, "negative-tests-tmp")
        os.makedirs(tmpdir, exist_ok=True)

        def run_case(case):
            env = dict(os.environ)
            env["CXX"] = cxx
            env["CXXFLAGS"] = "-std=c++" + std
            env["TMPDIR"] = tmpdir
            proc = subprocess.run(
                [sh, driver, case], cwd=neg_dir, env=env,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            return case, proc.stdout or ""

        results = {}
        with ThreadPoolExecutor(max_workers=2) as pool:
            for case, out in pool.map(run_case, cases):
                results[case] = out

        executed = 0
        failed = []
        for case in cases:
            out = results[case]
            if "FAIL" in out:
                failed.append((case, out))
            elif "PASS" in out:
                executed += 1
        excluded = len(cases) - executed - len(failed)
        self.output.info(
            "[negative-compile c++{0}] cases={1} executed={2} pass={3} fail={4} excluded={5}"
            .format(std, len(cases), executed, executed, len(failed), excluded))
        if failed:
            for case, out in failed:
                self.output.error(
                    "[negative-compile c++{0}] FAIL {1}\n{2}".format(std, case, out))
            raise ConanException(
                "{0} negative compilation case(s) failed at C++{1}".format(
                    len(failed), std))

    def package(self):
        include = os.path.join(self.source_folder, "include")
        copy(self, "*.hpp", src=include,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "**/*.hpp", src=include,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE_1_0.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # Name-disambiguated twin of the merged `trompeloeil/49` recipe: this
        # package YIELDS the upstream CMake names to it. Both recipes otherwise
        # publish the same headers, so keeping "trompeloeil" here would make
        # CMakeDeps write byte-identical trompeloeil-config.cmake /
        # trompeloeilTargets.cmake / *-Target-release.cmake files for two
        # different references into one generators/ directory - the later write
        # silently wins and a project requiring both packages loses one
        # imported target. Deliberately NO cmake_target_aliases and NO
        # namespaced_targets/compat return of "trompeloeil::trompeloeil":
        # aliasing the upstream name back only moves the clash from the config
        # file into the target namespace. Consumers that need the upstream
        # target name must require `trompeloeil`.
        self.cpp_info.set_property("cmake_file_name", "trompeloeil-cpp")
        self.cpp_info.set_property("cmake_target_name", "trompeloeil-cpp::trompeloeil-cpp")
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
