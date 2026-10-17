#!/usr/bin/env python3
"""Conan recipe for libprotoc 31.1 — the Protocol Buffers compiler library.

libprotoc has no standalone upstream repository: it is the ``libprotoc`` CMake
target of the Protocol Buffers project (``cmake/libprotoc.cmake``), whose
sources live under ``src/google/protobuf/compiler``. This recipe therefore
builds from the official protobuf 31.1 release tarball and packages only the
compiler library together with the runtime pieces it links against.

Targets HarmonyOS PC (aarch64-linux-ohos, musl).

Scope of the package (libprotoc only — the ``protoc`` command line tool is
intentionally not built or installed):

* ``libprotoc.a``               the deliverable compiler library
* ``libprotobuf.a``             required, libprotoc links it PRIVATE
* ``libupb.a``                  required, libprotoc links it PUBLIC
* libprotobuf-lite.a            pulled in by the upstream export set
* public headers + CMake export config so consumers can use
  ``protobuf::libprotoc`` directly

libprotoc reports ~1300 undefined symbols on its own, so the runtime libraries
and headers above must ship in the same package for it to be usable.

Upstream ships no vendored googletest, so the pinned Googletest source is
fetched separately and wired in through ``protobuf_GTEST_SOURCE_DIR``.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run, check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    mkdir,
    replace_in_file,
)


class LibprotocConan(ConanFile):
    name = "libprotoc"
    version = "31.1"
    description = "Protocol Buffers compiler library (libprotoc) from protobuf 31.1"
    license = "BSD-3-Clause"
    homepage = "https://github.com/protocolbuffers/protobuf"
    url = "https://github.com/protocolbuffers/protobuf"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_zlib": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_zlib": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("libprotoc supports Linux and OHOS targets")
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        check_min_cppstd(self, "17")
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("libprotoc supports OHOS armv8 only")

    def requirements(self):
        self.requires("abseil-cpp/20260107.1", transitive_headers=True)
        if self.options.with_zlib:
            self.requires("zlib/1.3.1")

    def layout(self):
        cmake_layout(self)

    def _apply_patches(self, prefix):
        """Apply only the conandata patches whose filename starts with prefix."""
        entries = [
            entry
            for entry in self.conan_data.get("patches", [])
            if os.path.basename(entry.get("patch_file", "")).startswith(prefix)
        ]
        if not entries:
            return
        original = self.conan_data["patches"]
        self.conan_data["patches"] = entries
        try:
            apply_conandata_patches(self)
        finally:
            self.conan_data["patches"] = original

    def source(self):
        get(self, **self.conan_data["sources"]["protobuf"], strip_root=True)
        get(
            self,
            **self.conan_data["sources"]["googletest"],
            strip_root=True,
            destination=os.path.join(self.source_folder, "googletest"),
        )
        # Keep a pinned native Abseil source tree for the test helper build.
        get(
            self,
            **self.conan_data["sources"]["host_abseil"],
            strip_root=True,
            destination=os.path.join(self.source_folder, "host-abseil"),
        )
        # Upstream ships no vendored Googletest, so its patch is applied here
        # against the freshly fetched tree, with base_path pointing at it.
        self._apply_patches("0002-")

    def generate(self):
        CMakeDeps(self).generate()

        tc = CMakeToolchain(self)
        # The upstream CTest suites need a runnable protoc to generate their
        # test protos (CMakeLists.txt requires it whenever tests are enabled),
        # so the tool is built as test scaffolding and stripped again in
        # package(): this package ships libprotoc only.
        tc.variables["protobuf_BUILD_TESTS"] = True
        tc.variables["protobuf_BUILD_CONFORMANCE"] = False
        tc.variables["protobuf_BUILD_EXAMPLES"] = False
        tc.variables["protobuf_BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["protobuf_BUILD_PROTOBUF_BINARIES"] = True
        tc.variables["protobuf_BUILD_PROTOC_BINARIES"] = True
        tc.variables["protobuf_BUILD_LIBPROTOC"] = True
        tc.variables["protobuf_BUILD_LIBUPB"] = True
        tc.variables["protobuf_FORCE_FETCH_DEPENDENCIES"] = False
        tc.variables["protobuf_LOCAL_DEPENDENCIES_ONLY"] = True
        tc.variables["protobuf_GTEST_SOURCE_DIR"] = os.path.join(
            self.source_folder, "googletest"
        ).replace("\\", "/")
        tc.variables["protobuf_WITH_ZLIB"] = bool(self.options.with_zlib)
        tc.variables["ABSL_PROPAGATE_CXX_STD"] = True
        tc.variables["CMAKE_BUILD_WITH_INSTALL_RPATH"] = True
        tc.variables["absl_DIR"] = os.path.join(
            self.dependencies["abseil-cpp"].package_folder,
            "lib",
            "cmake",
            "absl",
        ).replace("\\", "/")
        if self.options.with_zlib:
            tc.variables["ZLIB_ROOT"] = self.dependencies["zlib"].package_folder.replace(
                "\\", "/"
            )
        tc.generate()

    def build(self):
        # Only the protobuf-tree patches belong here; the Googletest patch was
        # already applied to the separately fetched tree in source().
        self._apply_patches("0001-")
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if can_run(self):
            test_tmpdir = os.path.join(self.build_folder, "test-tmp")
            mkdir(self, test_tmpdir)
            test_env = Environment()
            test_env.define("TEST_TMPDIR", test_tmpdir)
            test_env.define("TMPDIR", test_tmpdir)
            test_env.prepend_path("PATH", self.build_folder)
            with test_env.vars(self).apply():
                cmake.ctest(cli_args=["--output-on-failure", "--no-tests=error"])

    def _strip_tool_targets(self):
        """Drop the protoc tool targets from the exported CMake package.

        Upstream installs ``protobuf::protoc`` and the ``protoc-gen-*`` plugins
        into the same export set as the libraries. Those executables are not
        shipped by this package, so the stale imported targets are removed to
        keep ``find_package(Protobuf CONFIG)`` usable by consumers.
        """
        removed_targets = (
            "protobuf::protoc",
            "protobuf::protoc-gen-upb",
            "protobuf::protoc-gen-upbdefs",
        )
        cmake_dir = os.path.join(self.package_folder, "lib", "cmake", "protobuf")
        targets_file = os.path.join(cmake_dir, "protobuf-targets.cmake")
        release_file = os.path.join(cmake_dir, "protobuf-targets-release.cmake")

        # protobuf-targets.cmake: drop the expected-target list entries and the
        # add_executable stubs for the removed tools.
        if os.path.isfile(targets_file):
            with open(targets_file, "r", encoding="utf-8") as handle:
                content = handle.read()
            expected = " ".join(removed_targets)
            content = content.replace(f" {expected}", "")
            blocks = []
            for line in content.splitlines(keepends=True):
                stripped = line.strip()
                if any(stripped.startswith(f"add_executable({t} ")
                       for t in removed_targets):
                    blocks.append(None)  # start of a block to drop
                    continue
                if blocks and blocks[-1] is None:
                    # Keep dropping until the blank line that terminates the
                    # add_executable stub block.
                    if stripped == "":
                        blocks[-1] = ""
                    continue
                blocks.append(line)
            content = "".join(b for b in blocks if b is not None)
            with open(targets_file, "w", encoding="utf-8") as handle:
                handle.write(content)

        # protobuf-targets-release.cmake: drop the IMPORTED_LOCATION block and
        # the import-check entries for each removed tool.
        if os.path.isfile(release_file):
            with open(release_file, "r", encoding="utf-8") as handle:
                lines = handle.read().splitlines(keepends=True)
            kept = []
            index = 0
            while index < len(lines):
                line = lines[index]
                if any(f'Import target "{t}"' in line for t in removed_targets):
                    # Skip forward to just before the next import section.
                    index += 1
                    while index < len(lines) and "Import target" not in lines[index]:
                        index += 1
                    continue
                if any(f"_cmake_import_check_targets {t} " in line
                       for t in removed_targets):
                    index += 1
                    continue
                if any(f"_cmake_import_check_files_for_{t} " in line
                       for t in removed_targets):
                    index += 1
                    continue
                kept.append(line)
                index += 1
            with open(release_file, "w", encoding="utf-8") as handle:
                handle.write("".join(kept))

    def package(self):
        CMake(self).install()

        # libprotoc is the deliverable: the protoc command line tool and its
        # code-generator plugins were only built as test scaffolding, so they
        # are removed before the package is sealed.
        bin_dir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bin_dir):
            for entry in os.listdir(bin_dir):
                path = os.path.join(bin_dir, entry)
                if os.path.isfile(path) or os.path.islink(path):
                    os.remove(path)
            if not os.listdir(bin_dir):
                os.rmdir(bin_dir)
        self._strip_tool_targets()

        package_prefix = self.package_folder.replace("\\", "/")
        pkgconfig_dir = os.path.join(self.package_folder, "lib", "pkgconfig")
        for pc_name in (
            "protobuf-lite.pc",
            "protobuf.pc",
            "upb.pc",
            "utf8_range.pc",
        ):
            pc_path = os.path.join(pkgconfig_dir, pc_name)
            replace_in_file(
                self,
                pc_path,
                f"includedir={package_prefix}/include",
                "includedir=${prefix}/include",
            )
            replace_in_file(
                self,
                pc_path,
                f"libdir={package_prefix}/lib",
                "libdir=${prefix}/lib",
            )
            replace_in_file(
                self,
                pc_path,
                f"exec_prefix={package_prefix}",
                "exec_prefix=${prefix}",
            )
            replace_in_file(
                self,
                pc_path,
                f"prefix={package_prefix}",
                "prefix=${pcfiledir}/../..",
            )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        # Preserve Protobuf's component-rich CMake config so that the
        # protobuf::libprotoc target and its transitive contracts survive.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.libs = ["protoc"]
        self.cpp_info.system_libs.append("pthread")
        self.cpp_info.requires.append("abseil-cpp::abseil-cpp")
        if self.options.with_zlib:
            self.cpp_info.requires.append("zlib::zlib")
