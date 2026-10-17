#!/usr/bin/env python3
"""Conan recipe — olsrd 0.9.8

OLSR (Optimized Link State Routing, RFC3626) routing daemon (olsr.org).
Hand-rolled Makefile build (top `make` = daemon, `make libs` = plugins).

OHOS adaptation summary:
  - OS must be forced to `linux`: make/guess_os.sh returns UNKNOWN on the OHOS
    kernel and would otherwise fall into the win32 branch.
  - `-D__MUSL__` is injected for OHOS: the NDK sysroot ships a bionic-generated
    linux/socket.h that unconditionally defines `struct sockaddr_storage`, while
    musl sys/socket.h also defines it.  The sysroot reserves the `__MUSL__`
    coordination hook (sys/socket.h includes linux/socket.h and skips its own
    sockaddr_storage when __MUSL__ is defined).  This fixes the E091/E119
    redefinition error for sources mixing sys/socket.h and linux/netlink.h.
  - cfgparser regenerates oparse.c/oscan.c with bison/flex at build time
    (tool_requires; generated files are NOT committed upstream).
  - Build scope: Linux default plugin set MINUS `pud`.  pud uses the pre-3.18
    gpsd client API (gps_data_t.status/online(double)/PRN[]/elevation[] ...)
    which gpsd>=3.20 removed; olsrd 0.9.8 is unmaintained -> exclude pud, so
    gpsd is not required.
  - Binaries are NOT stripped: llvm-stripped ELFs get EACCES on this platform.

Dependencies:
  - openssl/3.0.16  (lib/secure plugin links -lssl -lcrypto)
  - flex/2.6.4.2, bison/3.8.2 (tool_requires, cfgparser generators)
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class OlsrdConan(ConanFile):
    name = "olsrd"
    version = "0.9.8"
    description = "OLSR (RFC3626) routing daemon — olsr.org implementation with loadable plugins"
    license = "BSD-3-Clause"
    homepage = "http://www.olsr.org"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # Linux default plugin set MINUS pud (pud needs gpsd<=3.18 client API,
    # incompatible with gpsd/3.26 available in OHPCD).
    _PLUGINS = (
        "arprefresh bmf dot_draw dyn_gw dyn_gw_plain httpinfo info jsoninfo mdns "
        "mini nameservice netjson poprouting p2pd pgraph quagga secure sgwdynspeed "
        "txtinfo watchdog"
    )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # lib/secure plugin: LIBS += -lssl -lcrypto
        self.requires("openssl/3.0.16")

    def build_requirements(self):
        # src/cfgparser regenerates oparse.c/oscan.c with bison/flex (R36:
        # both published on ohpcd; binaries verified downloadable for armv8).
        self.tool_requires("flex/2.6.4.2")
        self.tool_requires("bison/3.8.2")

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Inject openssl include/lib search dirs for the plain-make build via
        # CPATH / LIBRARY_PATH (clang driver honours them; they propagate to
        # sub-makes because the olsrd Makefiles never redefine these vars).
        dep = self.dependencies.get("openssl")
        if dep:
            pf = dep.package_folder
            for inc in dep.cpp_info.includedirs:
                p = inc if os.path.isabs(inc) or not pf else os.path.join(pf, inc)
                self.buildenv_info.append_path("CPATH", p)
            for libd in dep.cpp_info.libdirs:
                p = libd if os.path.isabs(libd) or not pf else os.path.join(pf, libd)
                self.buildenv_info.append_path("LIBRARY_PATH", p)
        # Put tool_requires (flex/bison) bin/ into the conanbuild PATH.
        VirtualBuildEnv(self).generate()

    def build(self):
        apply_conandata_patches(self)
        # R33: compiler from Conan conf, never bare shell env vars.
        comp_execs = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = comp_execs.get("c") or "clang"
        # __MUSL__ is the OHOS NDK sysroot coordination hook (see module docstring).
        extra = "-D__MUSL__" if self.settings.os == "OHOS" else ""
        common = f'OS=linux CC="{cc}" EXTRA_CPPFLAGS="{extra}" NORPATH=1 -j1'

        # 1. daemon
        self.run(f"make {common}", cwd=self.source_folder, env="conanbuild")
        # 2. plugins (Linux default set minus pud)
        self.run(
            f'make libs SUBDIRS="{self._PLUGINS}" {common}',
            cwd=self.source_folder,
            env="conanbuild",
        )

    def package(self):
        # daemon binary (unstripped — stripped ELFs get EACCES on this platform)
        bin_dst = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dst, exist_ok=True)
        shutil.copy2(
            os.path.join(self.source_folder, "olsrd"),
            os.path.join(bin_dst, "olsrd"),
        )
        # plugins: lib/<plugin>/olsrd_*.so.<VER> -> lib/
        lib_dst = os.path.join(self.package_folder, "lib")
        os.makedirs(lib_dst, exist_ok=True)
        for so in sorted(
            glob_sos(self.source_folder)
        ):
            shutil.copy2(so, os.path.join(lib_dst, os.path.basename(so)))
        # license
        lic_dst = os.path.join(self.package_folder, "share", "doc", "olsrd")
        os.makedirs(lic_dst, exist_ok=True)
        shutil.copy2(
            os.path.join(self.source_folder, "license.txt"),
            os.path.join(lic_dst, "license.txt"),
        )

    def package_info(self):
        # Command-line daemon + dlopen plugins; not a linkable library.
        self.cpp_info.bindirs = ["bin"]


def glob_sos(src_dir):
    """Yield plugin shared objects: lib/*/olsrd_*.so.* (nested per plugin)."""
    for root, _dirs, files in os.walk(src_dir):
        if root.startswith(os.path.join(src_dir, "lib")):
            for name in files:
                if name.startswith("olsrd_") and ".so." in name:
                    yield os.path.join(root, name)
