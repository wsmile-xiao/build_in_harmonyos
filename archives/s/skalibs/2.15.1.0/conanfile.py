#!/usr/bin/env python3
"""Conan recipe for skalibs 2.15.1.0 — skarnet.org C utility library.

skalibs uses skarnet's own configure + make system (NOT standard autotools
or cmake). The configure script auto-detects sysdeps on the target platform;
on OHOS (native aarch64) it correctly detects:
  devurandom=yes, posixspawnearlyreturn=no, procselfexe=/proc/self/exe,
  selectinfinite=yes.

No external dependencies — only the C standard library.
"""
import glob
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class SkalibsConan(ConanFile):
    name = "skalibs"
    version = "2.15.1.0"
    description = "skarnet.org skalibs — general-purpose C utility library (stralloc, buffers, crypto, etc.)"
    license = "ISC"
    homepage = "https://skarnet.org/software/skalibs/"
    url = ""

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"

    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # skarnet configure is NOT standard autotools — do not use AutotoolsToolchain.
        # R33: do NOT reference CC/CFLAGS as shell variables in commands; the skarnet
        #      configure script reads CC/CFLAGS from the environment that Conan's
        #      build env already populates (profile [buildenv] + VirtualBuildEnv).
        #      We rely on the conanbuild env which sets CC/CFLAGS correctly for the
        #      OHOS toolchain.
        src = self.source_folder
        prefix = self.package_folder

        # OHOS clang ships without a default sysroot, so skarnet configure's link
        # probes (tryldflag / detectlibs) cannot locate CRT startup objects
        # (Scrt1.o, crti.o, crtn.o) and abort with "unable to determine required
        # linker flags for socket functions". Inject --sysroot via LDFLAGS so the
        # probes can link; the conanbuild env does not declare LDFLAGS (profile
        # only sets CC/CXX via conf + PATH/SHELL via buildenv), so this passes
        # through env="conanbuild" cleanly.
        # R32: settings.os check must use in ("Linux", "OHOS")
        sysroots = sorted(glob.glob(
            "/data/service/hnp/ohos-sdk.org/*/ohos/native/sysroot"
        ))
        if sysroots:
            sysroot = sysroots[-1]
            cur = os.environ.get("LDFLAGS", "").strip()
            os.environ["LDFLAGS"] = f"{cur} --sysroot={sysroot}".strip()
        configure_cmd = (
            f"cd {src} && ./configure --prefix={prefix} --disable-shared"
        )

        self.run(configure_cmd, env="conanbuild")
        # R9: use -j1 (skarnet build order matters; s6 reference recipe uses -j1)
        self.run(f"cd {src} && make -j1", env="conanbuild")
        self.run(f"cd {src} && make install", env="conanbuild")

    def package(self):
        # make install already places files into package_folder (prefix).
        # The skarnet configure --prefix points to self.package_folder, so
        # make install writes lib/libskarnet.a and include/skalibs/* directly
        # into the package folder. No additional copy is needed.
        pass

    def package_info(self):
        self.cpp_info.libs = ["skarnet"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]
