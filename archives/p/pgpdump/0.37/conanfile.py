#!/usr/bin/env python3
"""Conan recipe for pgpdump 0.37 — PGP packet visualizer."""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, save
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class PgpdumpConan(ConanFile):
    name = "pgpdump"
    version = "0.37"
    description = "PGP packet visualizer for dumping OpenPGP packet structure"
    license = "BSD-2-Clause"
    homepage = "https://github.com/kazu-yamamoto/pgpdump"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def requirements(self):
        self.requires("zlib/1.3.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.extra_ldflags.append("-static")
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"
        tc.configure_args.append(f"CONFIG_SHELL={bash}")
        tc.generate()

    def build(self):
        save(
            self,
            os.path.join(self.build_folder, "config.h"),
            "\n".join(
                [
                    "#define HAVE_LIBZ 1",
                    "#define HAVE_STDIO_H 1",
                    "#define HAVE_STDLIB_H 1",
                    "#define HAVE_STRING_H 1",
                    "#define HAVE_INTTYPES_H 1",
                    "#define HAVE_STDINT_H 1",
                    "#define HAVE_STRINGS_H 1",
                    "#define HAVE_SYS_STAT_H 1",
                    "#define HAVE_SYS_TYPES_H 1",
                    "#define HAVE_UNISTD_H 1",
                    "#define HAVE_SYS_TIME_H 1",
                    "#define HAVE_STRUCT_TM_TM_ZONE 1",
                    "#define PACKAGE_VERSION \"0.37\"",
                    "",
                ]
            ),
        )
        sources = [
            "buffer.c",
            "keys.c",
            "packet.c",
            "pgpdump.c",
            "signature.c",
            "subfunc.c",
            "tagfuncs.c",
            "types.c",
            "uatfunc.c",
        ]
        src_dir = os.path.join(self.source_folder, "src")
        include_dirs = [self.build_folder, self.source_folder, src_dir]
        lib_dirs = []
        libs = []
        zlib = self.dependencies["zlib"].cpp_info
        include_dirs.extend(zlib.includedirs)
        lib_dirs.extend(zlib.libdirs)
        libs.extend(zlib.libs or ["z"])
        include_flags = " ".join(f'-I"{path}"' for path in include_dirs)
        lib_flags = " ".join(f'-L"{path}"' for path in lib_dirs)
        libs_flags = " ".join(f"-l{lib}" for lib in libs)
        objects = []
        for source in sources:
            src = os.path.join(src_dir, source)
            obj = os.path.join(self.build_folder, source.replace(".c", ".o"))
            objects.append(obj)
            self.run(
                f'${{CC:-clang}} -DHAVE_CONFIG_H {include_flags} ${{CFLAGS:-}} -O -Wall -c "{src}" -o "{obj}"',
                env="conanbuild",
            )
        objects_flags = " ".join(f'"{obj}"' for obj in objects)
        self.run(
            f'${{CC:-clang}} ${{LDFLAGS:-}} -static -o "{os.path.join(self.build_folder, "pgpdump")}" '
            f"{objects_flags} {lib_flags} {libs_flags}",
            env="conanbuild",
        )

    def package(self):
        copy(self, "pgpdump", src=self.build_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "pgpdump.1", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
