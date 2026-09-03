#!/usr/bin/env python3
"""Conan recipe — libpqxx 8.0.1 (official C++ client API for PostgreSQL).

CMake build.  Depends on libpq/18.1 from the ohpcd registry (verified via
conan download with --only-recipe during W0; see notes.md).

OHOS adaptation notes (see patches/ for the three portability patches):
  - clang 15.0.4 + libc++ 15 have no <source_location>; patch 0001 adds a
    minimal std::source_location shim;
  - libc++ 15's incomplete <format> fails consteval format-string checks when
    '<' directly precedes '{...}' in a literal; patch 0002 rewords the four
    affected literals;
  - patch 0003 makes the CMake build consume Conan's libpq::libpq target and
    enables _LIBCPP_ENABLE_EXPERIMENTAL + -lc++experimental on OHOS, where
    the shared libc++ omits the std::format runtime symbols.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rmdir,
)


class LibpqxxConan(ConanFile):
    name = "libpqxx"
    version = "8.0.1"
    description = "The official C++ client API for PostgreSQL"
    license = "BSD-3-Clause"
    homepage = "https://github.com/jtv/libpqxx"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("postgresql", "database", "sql", "db")
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libpq/18.1 is the only published build in the ohpcd registry
        # (W0 download-recipe probe; see notes.md). Only its shared .so is
        # usable: the packaged libpq.a references libpgport/libpgcommon
        # symbols that the package does not ship, so consumers link the
        # shared libpq regardless of this recipe's shared option.
        self.requires("libpq/18.1")

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.get_safe("shared"):
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libpqxx recipe supports Linux and OHOS, not {self.settings.os}"
            )
        # libpqxx 8.x needs C++20 (upstream requirements.json). The shared
        # OHOS profile pins compiler.cppstd=17 for the general ecosystem, but
        # the OHOS clang 15.0.4 + libc++ toolchain does compile libpqxx's
        # C++20 sources (verified; see notes.md), and this recipe forces
        # CMAKE_CXX_STANDARD=20 in generate(). So only reject when the
        # profile explicitly raises the bar, never gate on the lowered one.
        if str(self.settings.compiler.get_safe("cppstd", "17")) not in (
            "17", "20", "gnu17", "gnu20", "23", "gnu23",
        ):
            check_min_cppstd(self, 20)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        toolchain = CMakeToolchain(self)
        # R32: settings.os judgement must include OHOS.
        if str(self.settings.os) == "OHOS":
            # CMake 4.1 on the OHOS worker ships Platform/OHOS.cmake; make the
            # toolchain explicit instead of relying on uname detection, so CI
            # results match the local build (same approach as mp-units).
            toolchain.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            toolchain.blocks["generic_system"].values["cmake_system_processor"] = (
                "aarch64" if str(self.settings.arch) == "armv8" else str(self.settings.arch)
            )
        # The shared OHOS profile pins compiler.cppstd=17 for the general
        # ecosystem, and Conan's cppstd block would inject -std=c++17 into
        # every compile line. libpqxx 8.x requires C++20 (upstream
        # requirements.json: c++ >= 20), so override the block to 20 — the
        # OHOS clang 15.0.4 + libc++ toolchain does compile libpqxx's C++20
        # sources (verified; see notes.md).
        toolchain.blocks["cppstd"].values["cppstd"] = "20"
        toolchain.blocks["cppstd"].values["cppstd_extensions"] = "OFF"
        toolchain.cache_variables["BUILD_DOC"] = False
        toolchain.cache_variables["BUILD_TEST"] = False
        toolchain.cache_variables["SKIP_BUILD_EXAMPLES"] = True
        toolchain.generate()
        CMakeDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        rmdir(self, os.path.join(self.package_folder, "share"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libpqxx")
        self.cpp_info.set_property("cmake_target_name", "libpqxx::pqxx")
        self.cpp_info.set_property("pkg_config_name", "libpqxx")
        self.cpp_info.components["pqxx"].libs = ["pqxx"]
        self.cpp_info.components["pqxx"].set_property(
            "cmake_target_name", "libpqxx::pqxx"
        )
        self.cpp_info.components["pqxx"].set_property("pkg_config_name", "libpqxx")
        self.cpp_info.components["pqxx"].requires = ["libpq::libpq"]
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.components["pqxx"].system_libs = ["m"]
        if str(self.settings.os) == "OHOS":
            # OHOS shared libc++ omits the std::format runtime symbols; they
            # live in the toolchain's libc++experimental.a.  Every consumer
            # of the pqxx headers needs -lc++experimental at link time, and
            # needs _LIBCPP_ENABLE_EXPERIMENTAL at compile time to open the
            # (incomplete) <format> header (same treatment as ladybug 0.18.2
            # in this repository).
            self.cpp_info.components["pqxx"].system_libs.append("c++experimental")
            self.cpp_info.components["pqxx"].defines.append("_LIBCPP_ENABLE_EXPERIMENTAL")
        if self.options.shared:
            self.cpp_info.components["pqxx"].defines = ["PQXX_SHARED"]
