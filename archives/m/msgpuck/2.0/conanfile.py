#!/usr/bin/env python3
"""Conan recipe for msgpuck 2.0 — MessagePack serializer for C.

msgpuck is tarantool's tiny MessagePack library: header + one source
file, zero external dependencies.  The public API is a set of
mp_encode_*/mp_decode_* inlines over a caller-owned buffer, plus
mp_check() for validating a serialized blob.

Upstream tests: test/ holds a single test binary (test/msgpuck.c, ~177
assertions) driven by a custom CMake target.  The recipe builds it and
runs the binary directly, so a failing assertion fails the recipe
(R34: no fake logs).

Platform note: upstream declares cmake_minimum_required(VERSION 2.8.5),
which CMake 4.x rejects outright (support for <3.5 was removed); patch
0001 raises that floor.  Nothing else about the build needed changing.
"""

import os
import shlex

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.layout import basic_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class MsgpuckConan(ConanFile):
    name = "msgpuck"
    version = "2.0"
    description = ("msgpuck - a MessagePack serializer/deserializer for C "
                   "(header-only style API over a static library)")
    license = "BSD-2-Clause"
    homepage = "https://github.com/tarantool/msgpuck"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"msgpuck is adapted for Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        # url may arrive as a candidate list (the CI pre-download step
        # rewrites conandata's url into [mirror, official]).
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.variables["BUILD_SHARED_LIBS"] = (
            "ON" if self.options.shared else "OFF")
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        # Explicitly neutralize LD_LIBRARY_PATH: some CI workers carry an
        # ambient LD pointing at /usr/local/lib whose incompatible
        # libxml2.so.16 breaks the SDK's lld on every link (CI-021 build
        # #48068 — mechanism documented in libodfgen/libabw).
        shield = Environment()
        shield.define("LD_LIBRARY_PATH", "")
        with shield.vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build(build_tool_args=["-j1"])
            self._run_upstream_tests()

    def _run_upstream_tests(self):
        """Run upstream's test binary (test/msgpuck.c).

        The tests are registered as a custom CMake target rather than
        through ctest, so the binary is invoked directly; its exit code
        is the verdict.
        """
        exe = os.path.join(self.build_folder, "test", "msgpuck.test")
        if not os.path.isfile(exe):
            raise ConanException(
                f"upstream test binary was not built: {exe}")
        # The scratch-file check inside test_mp_print writes under TMPDIR
        # (patch 0002) because this platform's /tmp is read-only.
        tmpdir = os.path.join(self.build_folder, ".tmp")
        os.makedirs(tmpdir, exist_ok=True)
        command = f"TMPDIR={shlex.quote(tmpdir)} {shlex.quote(exe)}"
        self.run(command, cwd=os.path.join(self.build_folder, "test"))
        self.output.info("[upstream-tests] msgpuck.test: PASS")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "msgpuck")
        self.cpp_info.set_property("cmake_target_name", "msgpuck::msgpuck")
        self.cpp_info.set_property("pkg_config_name", "msgpuck")
        self.cpp_info.libs = ["msgpuck"]
