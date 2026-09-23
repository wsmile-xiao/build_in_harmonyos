#!/usr/bin/env python3
"""Conan recipe — stdex 0.2.9 (custom POSIX-thread C++ extensions library).

stdex provides a C++11 standard-library implementation with extra features,
built on top of the compiler's standard library and POSIX threads. Upstream
ships a small static archive (libstdex.a) built from src/{chrono,mutex,thread}
plus a header tree in include/. There is no configure/cmake/make build system,
so this recipe reproduces build_lib.sh manually with the Conan toolchain
compiler (R33: flags come from the toolchain profile, not shell env vars).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class StdexConan(ConanFile):
    name = "stdex"
    version = "0.2.9"
    description = (
        "C++11 standard library implementation with extra features "
        "using C++98 and POSIX threads"
    )
    license = "MIT"
    homepage = "https://github.com/oktonion/stdex"
    url = "https://github.com/oktonion/stdex"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"

    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def configure(self):
        # R32: platform whitelist instead of == "Linux"
        if self.settings.os not in ("Linux", "OHOS", "FreeBSD", "Macos", "Windows"):
            raise ConanInvalidConfiguration(
                "stdex only supports Linux/OHOS/FreeBSD/MacOS/Windows, "
                "current: {}".format(self.settings.os)
            )
        # Upstream ships only a static archive (build_lib.sh does ar rcs);
        # there is no shared-library build path, so reject shared=True.
        if self.options.shared:
            raise ConanInvalidConfiguration(
                "stdex upstream only provides a static library build"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        if self.settings.os not in ("Linux", "OHOS"):
            self.fail("stdex static build requires Linux or OHOS")
        apply_conandata_patches(self)

        # R33: compiler executable and standard come from the Conan toolchain
        # (profile [conf] tools.build:compiler_executables), never bare env.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cxx = compilers.get("cpp", "clang++") if compilers else "clang++"
        cppstd = str(self.settings.compiler.cppstd).replace("gnu", "")
        std_flag = "-std=c++{}".format(cppstd)

        src_dir = os.path.join(self.source_folder, "stdex", "src")
        obj_dir = os.path.join(self.build_folder, "obj")
        os.makedirs(obj_dir, exist_ok=True)

        objects = []
        for cpp in sorted(os.listdir(src_dir)):
            if not cpp.endswith(".cpp"):
                continue
            obj = os.path.join(obj_dir, os.path.splitext(cpp)[0] + ".o")
            self.run(
                "{cxx} {std} -c {src} -o {obj}".format(
                    cxx=cxx, std=std_flag,
                    src=os.path.join(src_dir, cpp), obj=obj,
                )
            )
            objects.append(obj)

        lib = os.path.join(self.build_folder, "libstdex.a")
        self.run("llvm-ar rcs {lib} {objs}".format(lib=lib, objs=" ".join(objects)))

    def package(self):
        # Install headers under include/stdex/ so wrapper headers named like
        # standard ones (thread, mutex, chrono, type_traits, ...) never shadow
        # the consumer's real standard library headers.
        copy(
            self,
            "*",
            src=os.path.join(self.source_folder, "stdex", "include"),
            dst=os.path.join(self.package_folder, "include", "stdex"),
        )
        copy(
            self,
            "libstdex.a",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "lib"),
        )

    def package_info(self):
        self.cpp_info.libs = ["stdex"]
        self.cpp_info.includedirs = ["include"]