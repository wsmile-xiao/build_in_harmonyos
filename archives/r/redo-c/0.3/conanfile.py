#!/usr/bin/env python3
"""Conan recipe — redo-c 0.3 (portable C implementation of the redo build system).

redo-c is Daniel J. Bernstein's redo build system implemented in a single
portable C file (redo.c) with zero external dependencies. The upstream build
is driven by .do files: redo.do compiles redo.c into the `redo` executable,
links.do creates the redo-ifcreate / redo-ifchange / redo-always symlinks.

OHOS adaptation: compile redo.c directly with the Conan-provided clang
toolchain (R33: never use bare ${CC} from the shell), then install the
`redo` binary and its symlinks under bin/. No source patches required.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class RedoCConan(ConanFile):
    name = "redo-c"
    version = "0.3"
    description = "redo-c — the redo build system (D. J. Bernstein) implemented in portable C with zero dependencies"
    license = "CC0-1.0"
    homepage = "https://github.com/leahneukirchen/redo-c"
    url = "https://github.com/leahneukirchen/redo-c"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # R33: obtain the C compiler from Conan conf, never from bare shell env vars
        apply_conandata_patches(self)
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        # redo.do: cc -g -Os -Wall -Wextra -Wwrite-strings -o redo redo.c
        # Strip -g/-Os for release parity with the OHOS profile build_type.
        self.run(f"{cc} -O2 -Wall -Wextra -Wwrite-strings -o redo redo.c",
                 cwd=self.source_folder)

    def package(self):
        copy(self, "redo", self.source_folder, os.path.join(self.package_folder, "bin"))
        # links.do: ln -sf redo redo-ifcreate / redo-ifchange / redo-always
        for link in ("redo-ifcreate", "redo-ifchange", "redo-always"):
            os.symlink("redo", os.path.join(self.package_folder, "bin", link))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
