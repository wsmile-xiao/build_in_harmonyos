#!/usr/bin/env python3
"""Conan recipe — embedded-log 1.0.1 (bare C logging library, custom build).

Upstream (github.com/to9/embedded-log) ships only src/log.c + src/log.h +
src/log_cfg.h — there is no configure/Makefile/CMake build system.  The recipe
compiles log.c directly with the Conan toolchain compiler into a static
archive and installs the two public headers flat into include/.

OHOS adaptations:
  - no upstream build system: compile log.c directly (R33 — compiler comes
    from Conan conf, never a shell ${CC} variable; make -j1 not applicable);
  - LOG_ENABLE is enabled by the bundled src/log_cfg.h, so the real symbols
    (printk/log_init/printk_hex/log_hook) are emitted, as shipped upstream;
  - static-only default: no system-name collision on OHOS and the embedded
    use case consumes a static archive.
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class EmbeddedLogConan(ConanFile):
    name = "embedded-log"
    version = "1.0.1"
    description = "embedded-log: small pretty embedded logging library (C)"
    license = "MIT"
    homepage = "https://github.com/to9/embedded-log"
    url = ""  # CI fills this

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
        # R33: compiler from Conan conf, never shell env.  Some conan builds
        # reject the subkey access (settings-only profile merge), so fall
        # back to the plain toolchain name (PATH-resolved, same as
        # AutotoolsToolchain emits).
        try:
            cc = self.conf.get("tools.build:compiler_executables:c", "clang",
                               check_type=str)
        except Exception:
            cc = "clang"
        try:
            ar = self.conf.get("tools.build:compiler_executables:ar",
                               "llvm-ar", check_type=str)
        except Exception:
            ar = "llvm-ar"
        src_dir = os.path.join(self.source_folder, "src")
        obj = os.path.join(self.build_folder, "log.o")
        lib = os.path.join(self.build_folder, "libembedded-log.a")
        self.run(f"{cc} -c -O2 -fPIC -std=c99 -I{src_dir} "
                 f"{os.path.join(src_dir, 'log.c')} -o {obj}")
        self.run(f"{ar} rcs {lib} {obj}")

    def package(self):
        copy(self, "log.h", src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "include"), keep_path=False)
        copy(self, "log_cfg.h", src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "include"), keep_path=False)
        copy(self, "libembedded-log.a", src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["embedded-log"]