#!/usr/bin/env python3
"""Conan recipe — nnom 0.4.3 (bare C neural-network library, custom build).

Upstream (github.com/majianjia/nnom) ships only src/*.c + inc/*.h +
port/nnom_port.h with an RT-Thread SConscript — there is no
configure/Makefile/CMake build system usable standalone.  This recipe
compiles all core/layers/backends sources directly with the Conan
toolchain compiler into a static archive and installs the public headers.

OHOS adaptations:
  - no upstream standalone build system: compile the C sources directly
    (R33 — compiler comes from Conan conf, never a shell ${CC} variable);
  - CMSIS-NN backends are guarded by NNOM_USING_CMSIS_NN (undefined here),
    so only the portable local C backends are compiled — no ARM CMSIS
    dependency is pulled in;
  - static-only default: embedded use case consumes a static archive.
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class NnomConan(ConanFile):
    name = "nnom"
    version = "0.4.3"
    description = "nnom: A higher-level Neural Network library for microcontrollers (C)"
    license = "Apache-2.0"
    homepage = "https://github.com/majianjia/nnom"
    url = "https://github.com/majianjia/nnom"

    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: compiler from Conan conf, never shell env.
        try:
            cc = self.conf.get("tools.build:compiler_executables:c", "clang",
                               check_type=str)
        except Exception:
            cc = "clang"
            self.output.warning("conf tools.build:compiler_executables:c "
                                "缺失，回退 clang（配方环境未注入编译器）")
        try:
            ar = self.conf.get("tools.build:compiler_executables:ar",
                               "llvm-ar", check_type=str)
        except Exception:
            ar = "llvm-ar"
            self.output.warning("conf tools.build:compiler_executables:ar "
                                "缺失，回退 llvm-ar")
        src_dir = self.source_folder
        inc_dir = os.path.join(src_dir, "inc")
        port_dir = os.path.join(src_dir, "port")
        objs = []
        for sub in ("core", "layers", "backends"):
            for src in sorted(os.listdir(os.path.join(src_dir, "src", sub))):
                if not src.endswith(".c"):
                    continue
                base = os.path.splitext(src)[0]
                obj = os.path.join(self.build_folder, f"nnom_{sub}_{base}.o")
                self.run(f"{cc} -c -O2 -fPIC -std=c99 -I{inc_dir} -I{port_dir} "
                         f"{os.path.join(src_dir, 'src', sub, src)} -o {obj}")
                objs.append(obj)
        lib = os.path.join(self.build_folder, "libnnom.a")
        self.run(f"{ar} rcs {lib} " + " ".join(objs))

    def package(self):
        copy(self, "*.h", src=os.path.join(self.source_folder, "inc"),
             dst=os.path.join(self.package_folder, "include"), keep_path=False)
        copy(self, "*.h", src=os.path.join(self.source_folder, "inc", "layers"),
             dst=os.path.join(self.package_folder, "include", "layers"),
             keep_path=False)
        copy(self, "nnom_port.h", src=os.path.join(self.source_folder, "port"),
             dst=os.path.join(self.package_folder, "include"), keep_path=False)
        copy(self, "libnnom.a", src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["nnom"]
        self.cpp_info.system_libs = ["m"]
