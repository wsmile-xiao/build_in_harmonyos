#!/usr/bin/env python3
"""Conan recipe — avce00 2.0.0

C library and tools for converting between ESRI Arc/Info Vector Coverage
binary (AVC) and E00 (ASCII export) formats.

Build system: GNUmakefile (plain Makefile, no configure).
License: MIT.
Dependencies: none (self-contained; bundles CPL utility headers).
"""
import json
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.env import Environment
from conan.tools.layout import basic_layout


class Avce00Conan(ConanFile):
    name = "avce00"
    version = "2.0.0"
    description = "C library and tools for ESRI Arc/Info AVC BIN <-> E00 conversion"
    license = "MIT"
    homepage = "http://avce00.maptools.org/"
    url = ""  # CI fills this

    package_type = "static-library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"avce00 supports Linux/OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Do NOT use VirtualBuildEnv — its printenv call overflows the OHOS
        # argument-list limit when the profile buildenv has many entries.
        # Instead, write a minimal env script with only what we need.
        comp_execs = self.conf.get("tools.build:compiler_executables",
                                   default={}, check_type=dict)
        if isinstance(comp_execs, str):
            comp_execs = json.loads(comp_execs)
        cc = comp_execs.get("c", "clang") if comp_execs else "clang"
        ar = comp_execs.get("ar", "llvm-ar") if comp_execs else "llvm-ar"

        # Detect sysroot from compiler location
        cc_dir = os.path.dirname(cc)
        sysroot = os.path.normpath(os.path.join(cc_dir, "..", "sysroot"))
        if not os.path.isdir(sysroot):
            sysroot = ""  # fallback: hope the compiler knows its own sysroot

        # Build CFLAGS: sysroot + code-sign + our defines
        cflags_parts = []
        if sysroot:
            cflags_parts.append(f"--sysroot={sysroot}")
            cflags_parts.append("-fuse-ld=lld -Wl,--code-sign")
            cflags_parts.append(f"-L{sysroot}/usr/lib/aarch64-linux-ohos")
        cflags_parts.append("-DCPL_LSB -DAVC_MAP_TYPE40_TO_DOUBLE")
        if str(self.options.get_safe("fPIC", True)) == "True":
            cflags_parts.append("-fPIC")
        cflags = " ".join(cflags_parts)

        # Build LDFLAGS: sysroot + linker flags
        ldflags = ""
        if sysroot:
            ldflags = f"--sysroot={sysroot} -fuse-ld=lld -Wl,--code-sign -L{sysroot}/usr/lib/aarch64-linux-ohos"

        env = Environment()
        env.define("CC", cc)
        env.define("AR", ar)
        env.define("CFLAGS", cflags)
        env.define("LDFLAGS", ldflags)
        tmpdir = os.environ.get("TMPDIR",
                                os.path.join(os.path.expanduser("~"), "tmp-build"))
        env.define("TMPDIR", tmpdir)
        env.vars(self).save_script("avce00_build_env")

    def build(self):
        apply_conandata_patches(self)
        # R33: CC/CFLAGS come from avce00_build_env script, not shell variables.
        # The GNUmakefile hardcodes CC=gcc and CFLAGS=...; override via make vars.
        self.run(
            'make -j1 CC="$CC" AR="$AR" CFLAGS="$CFLAGS" LFLAGS="$LDFLAGS"',
            env="avce00_build_env",
            cwd=self.source_folder,
        )

    def package(self):
        # Install static library
        copy(self, "avc.a", src=self.source_folder,
             dst=os.path.join(self.package_folder, "lib"))
        # Rename to libavce00.a for Conan convention
        src_lib = os.path.join(self.package_folder, "lib", "avc.a")
        dst_lib = os.path.join(self.package_folder, "lib", "libavce00.a")
        if os.path.isfile(src_lib):
            os.rename(src_lib, dst_lib)

        # Install public headers
        # avc.h and avc_mbyte.h are the primary public headers.
        # cpl_*.h, dbfopen.h are required by avc.h includes.
        headers = [
            "avc.h", "avc_mbyte.h",
            "cpl_error.h", "cpl_port.h", "cpl_conv.h",
            "cpl_string.h", "cpl_vsi.h", "cpl_config.h", "dbfopen.h",
        ]
        for hdr in headers:
            copy(self, hdr, src=self.source_folder,
                 dst=os.path.join(self.package_folder, "include"))

        # Install command-line tools
        for tool in ("avcimport", "avcexport", "avcdelete"):
            copy(self, tool, src=self.source_folder,
                 dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = ["avce00"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]
        # Make tools available in PATH for consumers
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
