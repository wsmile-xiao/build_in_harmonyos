#!/usr/bin/env python3
"""Conan recipe for bsdconv 11.6.

bsdconv is a charset/encoding conversion tool written in pure C.
Build system: plain Makefile (no configure / autotools).

Observations from adaptation:
  - OHOS `uname -s` returns "HarmonyOS", so the Makefile's `LIBS+=-ldl`
    branch (guarded by `ifeq (${UNAME_S}, Linux)`) does NOT trigger; the
    OHOS libc provides dlopen()/dlsym()/dlclose() natively, so linking
    succeeds and runtime module loading works without -ldl.
  - Upstream src/libbsdconv.c had an off-by-one VLA (`char *phase_off[i+1]`)
    that writes phase_off[phasen+1] when strsep() returns NULL. Patched to
    `phase_off[i+2]` (see patches/0002-*). Without the fix, 3-phase
    conversions (e.g. `ASCII:COUNT:ASCII`) fail with EINVAL on clang 15.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class BsdconvConan(ConanFile):
    name = "bsdconv"
    version = "11.6"
    description = "A simple but powerful DSL for charset/encoding conversion and transformation"
    license = "BSD-2-Clause"
    homepage = "https://github.com/buganini/bsdconv"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    # bsdconv 的 Makefile 仅产出共享库 libbsdconv.so.11（无静态库目标），
    # 故不声明 shared/fPIC 选项（避免误导消费者）。

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # bsdconv is pure C with no external dependencies
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: obtain the compiler from Conan conf, never from bare ${CC}.
        # Tools.build:compiler_executables is a dict conf; read it as a whole
        # (same pattern as archives/l/lib3ds/1.3.0/conanfile.py).
        comp_execs = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = comp_execs.get("c", "clang")
        # R9: always -j1. bsdconv is a plain Makefile project (no configure):
        # the Makefile lives in the source folder, so run make there.
        # Makefile builds libbsdconv.so.11 + 4 tools + codec modules.
        self.run(f"make CC={cc} -j1", cwd=self.source_folder)

    def package(self):
        # Makefile install uses ${DESTDIR}${PREFIX}; leave DESTDIR empty and
        # point PREFIX at the Conan package folder.
        self.run(f"make install PREFIX={self.package_folder}", cwd=self.source_folder)

    def package_info(self):
        self.cpp_info.libs = ["bsdconv"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
