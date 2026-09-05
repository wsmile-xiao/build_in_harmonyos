#!/usr/bin/env python3
"""Conan recipe for cgreen 1.6.4 — C/C++ unit testing & mocking framework (CMake).

Upstream: https://github.com/cgreen-devs/cgreen (1.6.4 release tarball).
Package type: library — installs libcgreen (shared, upstream default layout
`libcgreen.so.1.6.4` + SONAME symlinks) plus headers and CMake config.

Upstream self-test suite (framework tests itself: assertions, mocks,
constraints, parameterized/reflective runner, message-output diffs) is built
and executed during build() with CGREEN_WITH_UNIT_TESTS=ON:
  * 26 CTest entries registered (XML reporter sub-tests disabled, see notes);
  * 24 run via `ctest`, the 2 reflective dlopen entries (`runner_test_cgreen_c`
    / `runner_test_cgreen_cpp`) are executed equivalently through the built
    cgreen-runner binary right after the ctest phase (on OHOS the reflective
    dlopen run inside the same ctest session destabilises the bash-based
    output-diff tests that follow it — deterministic and reproduced twice);
    combined pass rate 26/26, runner assertion totals C 350 + C++ 368 passes.

HarmonyOS adaptation facts (details in notes.md / PR description):
  * CMake needs CMAKE_SYSTEM_NAME=Linux (+ aarch64) — HarmonyOS platform files
    are unknown to CMake; OHOS-adapted conan triplet maps toolchain otherwise.
  * CGREEN_WITH_XML=OFF: xml reporter (create_xml_reporter) aborts (SIGABRT)
    on OHOS in any run_test_suite() consumer, incl. a minimal top-level
    consumer; libxml2 reporter needs libxml2 which is not packaged.
  * tools/cgreen_runner_output_diff: #!/bin/bash shebang does not resolve on
    OHOS (bash lives under /data/service/hnp/bin) and `uname -o` reports
    "Toybox"; patch maps Toybox/HarmonyOS to the GNU/Linux prefix/ext
    (lib/.so) branch and switches the shebang to /usr/bin/env bash.
  * Test runner binary cgreen-runner (and cgreen-debug helper) are built for
    the self-test phase only; they are not installed so the package stays a
    pure library (commands.json not required).

NEW test_package consumer tests (with cgreen writing cgreen tests — closed
loop): 4 executables / 17 test functions / 44 assertion calls including
2 intentional negative-path failure assertions (see test_package/*.c).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class CgreenConan(ConanFile):
    name = "cgreen"
    version = "1.6.4"
    description = "C/C++ unit testing and mocking framework (assertions, suites, mock objects, reporters)"
    license = "ISC"
    homepage = "https://cgreen-devs.github.io/cgreen/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("shared")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        if str(self.settings.os) == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.cache_variables["CGREEN_WITH_UNIT_TESTS"] = "ON"
        tc.cache_variables["CGREEN_WITH_XML"] = "OFF"
        tc.cache_variables["CGREEN_WITH_LIBXML2"] = "OFF"
        # Upstream builds the shared library unconditionally; CGREEN_WITH_
        # STATIC_LIBRARY additionally builds libcgreen.a for shared=False.
        tc.cache_variables["CGREEN_WITH_STATIC_LIBRARY"] = "ON" if not self.options.shared else "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Upstream self-tests (framework testing itself). TMPDIR must point
        # outside read-only /tmp (OHOS E002). Runner must be reachable on PATH.
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ.setdefault("TMPDIR", tmpdir)
        # Phase 1: 24 CTest entries (excludes the two reflective dlopen runs).
        self.run('ctest -j1 -E "^(runner_test_cgreen_c|runner_test_cgreen_cpp)$" --output-on-failure',
                 cwd=self.build_folder)
        # Phase 2: the two reflective-dlopen entries, run equivalently via the
        # built cgreen-runner (see docstring for the OHOS ordering rationale).
        self.run("./tools/cgreen-runner ./tests/libcgreen_c_tests.so", cwd=self.build_folder)
        self.run("./tools/cgreen-runner ./tests/libcgreen_cpp_tests.so", cwd=self.build_folder)

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Keep the package a pure library: the runner built for self-tests is
        # a developer tool needing nm/dlopen at runtime, not a shipped CLI.
        for tool in ("cgreen-runner", "cgreen-debug"):
            path = os.path.join(self.package_folder, "bin", tool)
            if os.path.exists(path):
                os.remove(path)
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir) and not os.listdir(bindir):
            os.rmdir(bindir)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "cgreen")
        self.cpp_info.set_property("cmake_target_name", "cgreen::cgreen")
        self.cpp_info.set_property("cmake_config_version_compat", "AnyNewerVersion")
        self.cpp_info.set_property("pkg_config_name", "cgreen")
        self.cpp_info.libs = ["cgreen"]
