#!/usr/bin/env python3
"""Conan recipe for protobuf 21.12 (the 3.21 line, pre-Abseil) (CMake).

HarmonyOS PC (aarch64) adaptation notes:
- protobuf 21.12 is the last self-contained release line of Protocol
  Buffers: no Abseil dependency, and its public headers compile from
  -std=gnu++11 up.  This matters for C++11-era consumers such as OLA
  0.10.9, whose code base still uses std::auto_ptr (removed in C++17);
  protobuf >= 22 headers hard-require C++17 via Abseil.
- Upstream unit tests are gtest based and are NOT enabled here.  They
  require a pinned googletest checkout fetched at configure time from
  GitHub plus a multi-target test build that is disproportionate for a
  dependency package; runtime behaviour is verified instead by the
  test_package round-trip, pool, arena and protoc execution tests.
- protoc, libprotobuf, libprotobuf-lite and libprotoc are all built and
  installed; pkg-config files are made relocatable with ${pcfiledir}.
"""

import os
import re
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
)


class ProtobufConan(ConanFile):
    name = "protobuf"
    version = "21.12"
    description = "Google's data serialization library and compiler (3.21 line, no Abseil)"
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
        "with_zlib": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"protobuf supports Linux and OHOS targets, not {self.settings.os}"
            )
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        # R32 uses `in` checks; the 21.12 public headers compile at C++11.
        check_min_cppstd(self, 11)
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("protobuf supports OHOS armv8 only")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Upstream tests stay disabled: they need a pinned googletest
        # checkout fetched from GitHub at configure time (see docstring).
        tc.variables["protobuf_BUILD_TESTS"] = False
        tc.variables["protobuf_BUILD_CONFORMANCE"] = False
        tc.variables["protobuf_BUILD_EXAMPLES"] = False
        tc.variables["protobuf_BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["protobuf_BUILD_PROTOC_BINARIES"] = True
        tc.variables["protobuf_BUILD_LIBPROTOC"] = True
        tc.variables["protobuf_WITH_ZLIB"] = bool(self.options.with_zlib)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        CMake(self).install()
        self._relocate_pkgconfig("protobuf.pc")
        self._relocate_pkgconfig("protobuf-lite.pc")
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def _relocate_pkgconfig(self, pc_name):
        pc_path = Path(self.package_folder, "lib", "pkgconfig", pc_name)
        if not pc_path.is_file():
            raise ConanException(f"installed {pc_name} is missing: {pc_path}")
        pc_content = pc_path.read_text(encoding="utf-8")
        field_replacements = {
            "prefix": "prefix=${pcfiledir}/../..",
            "exec_prefix": "exec_prefix=${prefix}",
            "libdir": "libdir=${prefix}/lib",
            "includedir": "includedir=${prefix}/include",
        }
        for field, replacement in field_replacements.items():
            pc_content = re.sub(
                rf"^{field}=.*$",
                lambda _match: replacement,
                pc_content,
                count=1,
                flags=re.MULTILINE,
            )
        pc_path.write_text(pc_content, encoding="utf-8", newline="\n")

    def package_info(self):
        # Keep upstream's component-rich CMake config files.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.libs = ["protobuf"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.system_libs.append("pthread")
