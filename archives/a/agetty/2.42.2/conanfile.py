#!/usr/bin/env python3
"""Conan recipe for agetty 2.42.2 (component of util-linux 2.42.2).

agetty - alternate Linux getty, built from the util-linux 2.42.2 source tree
(term-utils/agetty.c). Build system: autotools (configure + make).

HarmonyOS PC adaptation points (all OHOS-only, no effect on Linux/other OS):
  1. E007: config.guess cannot detect HarmonyOS -> 0001-config-guess-ohos.patch
  2. HMDFS tmpdir: config.status mktemp 0700 dirs are unwritable on HMDFS
     -> 0002-configure-mktemp-hmdfs.patch ($TMPDIR/conf$$ + mkdir -p)
  3. E119: OHOS linux/socket.h vs musl sys/socket.h both define
     sockaddr_storage -> -D__MUSL__ at compile time
  4. E121: OHOS libc lacks GNU utmpx symbols (updwtmpx/setutxent/getutxent/
     pututxline/endutxent/utmpxname) and vhangup is not declared/exported
     -> local shim (src/ohos-utmpx-shim.c + src/ohos-utmpx-compat.h),
     linked only on OHOS; utmp/wtmp recording is no-op (degraded), vhangup
     uses the real AArch64 SYS_vhangup syscall.
"""
import os

from conan import ConanFile
from conan.tools.files import copy, get, apply_conandata_patches
from conan.tools.layout import basic_layout


class AgettyConan(ConanFile):
    name = "agetty"
    version = "2.42.2"
    description = "agetty - alternate Linux getty (util-linux 2.42.2)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/util-linux/util-linux"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        copy(self, "patches/*", src=self.recipe_folder, dst=self.export_sources_folder)
        copy(self, "src/*", src=self.recipe_folder, dst=self.export_sources_folder)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        tmpdir = os.path.join(self.build_folder, "conftmp")
        os.makedirs(tmpdir, exist_ok=True)
        esf = self.export_sources_folder
        shim = os.path.join(esf, "src", "ohos-utmpx-shim.c")
        compat = os.path.join(esf, "src", "ohos-utmpx-compat.h")
        ohos = self.settings.os == "OHOS"

        # Compile the local utmpx/vhangup shim (OHOS only).
        if ohos:
            self.run(f"clang -c {shim} -o conftmp/ohos-utmpx-shim.o", cwd=self.build_folder)
            self.run("ar rcs conftmp/libohos-utmpx-shim.a conftmp/ohos-utmpx-shim.o",
                     cwd=self.build_folder)

        # Configure + make only agetty (--disable-all-programs --enable-agetty).
        cfg = (
            "./configure --disable-all-programs --enable-agetty --disable-nls "
            "--disable-rpath --disable-plymouth_support "
            "--build=aarch64-unknown-linux-gnu --host=aarch64-linux-ohos "
            f"--prefix={os.path.join(self.build_folder, 'prefix')}"
        )
        if ohos:
            # NOTE: configure probes use `char updwtmpx(void)` which conflicts
            # with the forward declaration in ohos-utmpx-compat.h, so the
            # compat header is only injected at make time, not at configure.
            cfg = (
                f"TMPDIR={tmpdir} CFLAGS='-D__MUSL__' "
                f"LDFLAGS='-L{tmpdir}' LIBS='-lohos-utmpx-shim' " + cfg
            )
            self.run(cfg, cwd=self.source_folder)
            make_cflags = f"-D__MUSL__ -include {compat} -O2"
            self.run(
                f"TMPDIR={tmpdir} make agetty -j4 CFLAGS='{make_cflags}' "
                f"LDFLAGS='-L{tmpdir}' LIBS='-lohos-utmpx-shim'",
                cwd=self.source_folder)
        else:
            self.run(cfg, cwd=self.source_folder)
            self.run("make agetty -j4", cwd=self.source_folder)

    def package(self):
        copy(self, "agetty", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
