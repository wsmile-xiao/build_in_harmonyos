#!/usr/bin/env python3
"""Conan recipe for mapcode 2.5.7 — Mapcode library and command line tool.

Upstream: https://github.com/mapcode-foundation/mapcode-cpp (tag v2.5.7)
Builds the C library `mapcodelib` plus the `mapcode` command line utility and
runs the upstream unit test suite (`test/unittest.c`) as part of build().
"""
import os
import platform
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get

# Host machines that can execute aarch64 OpenHarmony binaries directly.
_NATIVE_MACHINES = ("aarch64", "arm64")

# The upstream suite (test/unittest.c) is a single binary whose main() invokes
# 19 test functions, grouped under the 12 section headers it prints at runtime.
# Both numbers are measured during the build instead of being asserted in prose,
# so the reported test-case count is backed by the run that actually happened.
_UPSTREAM_TEST_FUNCTIONS = 19
_UPSTREAM_TEST_SECTIONS = (
    "Environment tests",
    "Robustness tests",
    "Alphabet tests",
    "Alphabet per territory tests",
    "Parser tests",
    "Territory name tests",
    "Territory tests",
    "Distance tests",
    "Mapcode format tests",
    "Encode/decode tests",
    "Re-encode tests",
    "Bug-fix regression tests",
)


class MapcodeConan(ConanFile):
    name = "mapcode"
    version = "2.5.7"
    description = "Mapcode library and command line utility for encoding/decoding locations"
    license = "Apache-2.0"
    homepage = "https://github.com/mapcode-foundation/mapcode-cpp"
    url = ""

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _emulation_needed(self):
        """True when the binaries built here cannot run on this build machine.

        `cross_building()` is not a usable signal here: the OHOS profile is
        passed as both -pr:h and -pr:b, so Conan reports identical host and
        build settings even though the compiler targets aarch64 OpenHarmony
        from an x86_64 Linux builder. The CPU of the build machine is the
        reliable indicator.
        """
        return cross_building(self) or platform.machine().lower() not in _NATIVE_MACHINES

    def _run_target(self, command, **kwargs):
        if self._emulation_needed():
            qemu = shutil.which("qemu-aarch64")
            if not qemu:
                raise ConanInvalidConfiguration(
                    "qemu-aarch64 is required to execute OpenHarmony binaries on this host"
                )
            command = f'"{qemu}" {command}'
        self.run(command, **kwargs)

    def generate(self):
        tc = CMakeToolchain(self)
        # Upstream `add_library(mapcodelib ...)` honours BUILD_SHARED_LIBS; the
        # static variant is the default because it keeps the packaged
        # executables self-contained.
        tc.cache_variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # R32: the platform check must accept OHOS, not just Linux.
        if self.settings.os in ("Linux", "OHOS"):
            # E092: CMake does not know the "HarmonyOS" system name that the
            # OHOS-enabled Conan toolchain maps to, so state the GNU triplet
            # system name explicitly.
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        if self.settings.os == "OHOS":
            # Conan arch is "armv8"; CMake expects "aarch64" (E092).
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
            if not self.options.shared:
                # The OpenHarmony sysroot only ships a static libm, and linking
                # the two upstream executables statically keeps them runnable
                # without a device root filesystem.
                tc.extra_exelinkflags.append("-static")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Upstream official test suite: test/unittest.c, registered as the
        # `unittest` CTest target by patches/0001-*.patch. main() invokes 19
        # test functions grouped under 12 printed sections and performs roughly
        # 245 million assertions; _run_upstream_tests() measures all of that and
        # fails the build if the suite did not really run.
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """Run the upstream unit tests and gate on their real coverage.

        The upstream test reads territories.csv and alphabets.csv relative to
        its working directory, so it has to run from the source test/ folder.
        Output is captured to a log so that the summary can be verified and the
        per-group evidence replayed into the Conan log.
        """
        log = os.path.join(self.build_folder, "upstream_unittest.log")
        self._run_target(
            f'"{os.path.join(self.build_folder, "unittest")}" > "{log}" 2>&1',
            env="conanbuild",
            cwd=os.path.join(self.source_folder, "test"),
        )

        with open(log, encoding="utf-8", errors="replace") as handle:
            output = handle.read()

        # Every group main() runs must have printed its header, otherwise the
        # binary exited early or skipped a section and the run is not a pass.
        missing = [name for name in _UPSTREAM_TEST_SECTIONS if name not in output]
        if missing:
            raise ConanException(
                f"upstream unit test did not report these groups: {missing}"
            )

        # Count the test functions upstream main() invokes, from the fetched
        # source, so the claimed case count cannot drift away from the suite.
        functions = self._count_upstream_test_functions()
        if functions != _UPSTREAM_TEST_FUNCTIONS:
            raise ConanException(
                f"upstream main() invokes {functions} test functions, "
                f"expected {_UPSTREAM_TEST_FUNCTIONS}; the suite changed shape"
            )

        match = re.search(r"Executed (\d+) tests, found (\d+) errors", output)
        if not match:
            raise ConanException(
                "upstream unit test produced no 'Executed ... found ... errors' summary"
            )
        executed, errors = int(match.group(1)), int(match.group(2))
        if errors or "Unit tests passed" not in output:
            raise ConanException(
                f"upstream unit test reported {errors} errors; see {log}"
            )

        for name in _UPSTREAM_TEST_SECTIONS:
            self.output.info(f"  [upstream] {name}")
        self.output.info(
            f"upstream test groups: {len(_UPSTREAM_TEST_SECTIONS)}"
            f"/{len(_UPSTREAM_TEST_SECTIONS)} reported, "
            f"{functions}/{_UPSTREAM_TEST_FUNCTIONS} test functions invoked by main()"
        )
        self.output.info(
            f"upstream assertions: Executed {executed} tests, found {errors} errors"
            " -> Unit tests passed"
        )

    def _count_upstream_test_functions(self):
        """Number of test functions that upstream unittest main() invokes.

        Only the calls in main() are counted; a few helpers are additionally
        called from inside other test functions, and those belong to their
        caller's group rather than being separate cases.
        """
        path = os.path.join(self.source_folder, "test", "unittest.c")
        with open(path, encoding="utf-8", errors="replace") as handle:
            text = handle.read()
        start = text.find("int main(")
        if start < 0:
            raise ConanException(f"no main() found in {path}")
        return len(re.findall(r"nrTests\s*\+=\s*\w+\(\);", text[start:]))

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["mapcodelib"]
        self.cpp_info.system_libs = ["pthread", "m"]
        # The package ships the `mapcode` command line tool next to the library.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "mapcode")
        self.cpp_info.set_property("cmake_target_name", "mapcode::mapcode")
