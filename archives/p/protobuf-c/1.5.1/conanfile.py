#!/usr/bin/env python3
"""Conan recipe for protobuf-c 1.5.1 (CMake build system, upstream test suite run).

libprotobuf-c is built from the build-cmake/ subdirectory: upstream's autotools
path cannot configure on HarmonyOS PC (config.status fails with EACCES).

The upstream test programs (top-level Makefile.am `TESTS`, 11 of them) need C
fixtures that exist in neither the release tarball nor the git tag -- upstream's
`dist-hook` deletes every `*.pb-c.[ch]` -- so they have to be generated at build
time by `protoc --c_out` with this project's own `protoc-gen-c` plugin. That is
why protobuf is a build-context requirement here, exactly like upstream's
`./configure` requires the protobuf compiler to enable the test suite. The
published package does not link protobuf: consumers only get libprotobuf-c.
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get

# The top-level Makefile.am lists 11 programs in TESTS; the ctest registration is the
# authoritative count of what this build actually runs.
REQUIRED_UPSTREAM_TESTS = 11


class ProtobufcConan(ConanFile):
    name = "protobuf-c"
    version = "1.5.1"
    description = "Protocol Buffers implementation in C"
    license = "BSD-2-Clause"
    homepage = "https://github.com/protobuf-c/protobuf-c"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # protoc (from protobuf) + libprotoc are only needed to generate the
        # upstream test fixtures; zlib is protobuf's own dependency and
        # protobuf's CMake package config looks it up through find_dependency().
        self.tool_requires("protobuf/3.17.3")
        self.tool_requires("zlib/1.3.1")

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_PROTOC"] = True
        tc.variables["BUILD_TESTS"] = True
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        # CMake adds -DNDEBUG to its Release flags, which would compile every
        # assert() in upstream's t/ programs away.
        tc.variables["CMAKE_C_FLAGS_RELEASE"] = "-O2"
        tc.variables["CMAKE_CXX_FLAGS_RELEASE"] = "-O2"
        # Point CMake straight at the config files the protobuf package installs,
        # and at the zlib that config's find_dependency(ZLIB) needs.
        tc.cache_variables["protobuf_DIR"] = os.path.join(
            self.dependencies.get("protobuf", build=True).package_folder, "lib", "cmake", "protobuf").replace("\\", "/")
        tc.cache_variables["ZLIB_ROOT"] = self.dependencies.get("zlib", build=True).package_folder.replace("\\", "/")
        tc.generate()

    @property
    def _binary_dir(self):
        for root, _dirs, files in os.walk(self.build_folder):
            if "CMakeCache.txt" in files:
                return root
        raise ConanException("no CMakeCache.txt under " + self.build_folder)

    def _built_executable(self, name):
        binary_dir = self._binary_dir
        path = os.path.join(binary_dir, name)
        if os.path.isfile(path):
            return path
        for root, _dirs, files in os.walk(binary_dir):
            if name in files:
                return os.path.join(root, name)
        raise ConanException(name + " was not produced by the build")

    def _registered_test_count(self):
        count = 0
        for root, _dirs, files in os.walk(self._binary_dir):
            if "CTestTestfile.cmake" not in files:
                continue
            with open(os.path.join(root, "CTestTestfile.cmake"), encoding="utf-8") as handle:
                count += sum(1 for line in handle if line.lstrip().startswith("add_test("))
        return count

    def _write_packed_data_fixture(self):
        """Produce t/generated-code2/test-full-cxx-output.inc.

        Upstream's custom command passes ">t/generated-code2/...inc" as an
        *argument* to cxx-generate-packed-data instead of a shell redirection, so
        the fixture is never written and test-generated-code2 cannot compile.
        the top-level Makefile.am gets it right (`cxx-generate-packed-data > file`);
        this is that same step.
        """
        fixture = os.path.join(self._binary_dir, "t", "generated-code2", "test-full-cxx-output.inc")
        os.makedirs(os.path.dirname(fixture), exist_ok=True)
        self.run('"{}" > "{}"'.format(self._built_executable("cxx-generate-packed-data"), fixture),
                 env="conanbuild")
        size = os.path.getsize(fixture)
        if size == 0:
            raise ConanException("test-full-cxx-output.inc is empty")
        self.output.info("upstream_test_fixture: {} bytes".format(size))

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(build_script_folder="build-cmake")
        cmake.build(target="protoc-gen-c")
        cmake.build(target="cxx-generate-packed-data")
        self._write_packed_data_fixture()
        cmake.build()
        self.run_upstream_tests()

    def run_upstream_tests(self):
        registered = self._registered_test_count()
        self.output.info("upstream_test_audit: {} ctest programs registered "
                         "(upstream Makefile.am TESTS = {})".format(registered, REQUIRED_UPSTREAM_TESTS))
        if registered < REQUIRED_UPSTREAM_TESTS:
            raise ConanException("only {} of {} upstream test programs are wired up".format(
                registered, REQUIRED_UPSTREAM_TESTS))
        self.run("ctest --output-on-failure --timeout 120", cwd=self._binary_dir, env="conanbuild")
        self.output.info("upstream_test_summary: {}/{} upstream ctest programs passed".format(
            registered, registered))

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # protoc-gen-c is a build-time code generator for the test fixtures, not
        # part of this library's deliverables: shipping bin/ would turn a library
        # package into a CLI package.
        bin_dir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bin_dir):
            shutil.rmtree(bin_dir)

    def package_info(self):
        self.cpp_info.libs = ["protobuf-c"]
        self.cpp_info.set_property("cmake_file_name", "protobuf-c")
        self.cpp_info.set_property("cmake_target_name", "protobuf-c::protobuf-c")
        self.cpp_info.set_property("pkg_config_name", "libprotobuf-c")
