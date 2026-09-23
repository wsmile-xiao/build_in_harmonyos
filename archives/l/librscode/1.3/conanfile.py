#!/usr/bin/env python3
"""Conan recipe — librscode 1.3 (Reed-Solomon ECC, raw Makefile).

librscode is Henry Minsky's RSCODE 1.3: tiny ANSI C Reed-Solomon
encode/decode library (rs.c, galois.c, berlekamp.c, crcgen.c + ecc.h).
Upstream ships a minimal Makefile that hard-codes CC=gcc / AR=ar /
RANLIB=ranlib with -g -Wall -Wstrict-prototypes, which is not
cross-compile friendly. Rather than patching the upstream Makefile,
this recipe invokes the OpenHarmony toolchain directly on the four
real C sources and archives them into libecc.a (or libecc.so when
shared=True). No upstream source file is modified.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class LibrscodeConan(ConanFile):
    name = "librscode"
    version = "1.3"
    package_type = "library"
    description = "Reed-Solomon error-correcting encoder/decoder library in ANSI C (RSCODE)"
    license = "GPL-3.0-or-later"
    homepage = "http://rscode.sourceforge.net"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("librscode is supported only on Linux/OHOS")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def export_sources(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _resolve_cc(self):
        # R33: read the OpenHarmony toolchain from Conan conf, never from shell env.
        # The conf absolute path may be stale on some workers
        # (preflight: /data/service/hnp/bin/clang reported
        #  "inaccessible or not found"), so verify executability first
        # and fall back to PATH lookup (conanbuild env puts the toolchain
        # dir first). Bare "clang" lets the shell resolve via conanbuild PATH.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        conf_cc = compilers.get("c")
        if conf_cc and os.path.isabs(conf_cc):
            if os.path.isfile(conf_cc) and os.access(conf_cc, os.X_OK):
                return conf_cc
            # Absolute conf path broken: try same basename in PATH, then clang.
            base = os.path.basename(conf_cc)
            found = shutil.which(base) or shutil.which("clang") or shutil.which("cc")
            if found:
                self.output.info(f"conf compiler {conf_cc} not executable, using {found}")
                return found
            self.output.warning(
                f"conf compiler {conf_cc} not executable and no clang in PATH; "
                "falling back to bare 'clang' via conanbuild env"
            )
            return "clang"
        if conf_cc:
            found = shutil.which(conf_cc)
            if found:
                return found
            return conf_cc
        return shutil.which("clang") or "clang"

    def _resolve_ar(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        conf_ar = compilers.get("ar") or os.environ.get("AR")
        candidates = []
        if conf_ar:
            candidates.append(conf_ar)
        candidates += ["llvm-ar", "ar"]
        for c in candidates:
            if os.path.isabs(c):
                if os.path.isfile(c) and os.access(c, os.X_OK):
                    return c
            else:
                found = shutil.which(c)
                if found:
                    return found
        return candidates[-1]

    def build(self):
        cc = self._resolve_cc()
        ar = self._resolve_ar()

        srcs = ("rs.c", "galois.c", "berlekamp.c", "crcgen.c")
        build_dir = self.build_folder
        cflags = ["-O2", "-Wall"]
        if self.options.get_safe("fPIC", True) or self.options.shared:
            cflags.append("-fPIC")

        objs = []
        for src in srcs:
            obj = os.path.join(build_dir, src.replace(".c", ".o"))
            objs.append(obj)
            self.run(
                f'"{cc}" {" ".join(cflags)} -I"{self.source_folder}" '
                f'-c "{os.path.join(self.source_folder, src)}" -o "{obj}"',
                env="conanbuild",
            )

        if self.options.shared:
            # Shared build with relative SONAME so CI L5a passes.
            objs_str = " ".join(f'"{o}"' for o in objs)
            self.run(
                f'"{cc}" -shared -Wl,-soname,libecc.so '
                f'-o "{os.path.join(build_dir, "libecc.so")}" {objs_str}',
                env="conanbuild",
            )
        else:
            objs_str = " ".join(f'"{o}"' for o in objs)
            self.run(
                f'"{ar}" rcs "{os.path.join(build_dir, "libecc.a")}" {objs_str}',
                env="conanbuild",
            )

    def package(self):
        if self.options.shared:
            copy(self, "libecc.so", self.build_folder,
                 os.path.join(self.package_folder, "lib"))
        else:
            copy(self, "libecc.a", self.build_folder,
                 os.path.join(self.package_folder, "lib"))
        copy(self, "ecc.h", self.source_folder,
             os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.libs = ["ecc"]
        self.cpp_info.includedirs = ["include"]
