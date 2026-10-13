#!/usr/bin/env python3
"""Conan recipe for umtprd 1.6.8 (uMTP-Responder MTP responder daemon).

uMTP-Responder is a lightweight user-space USB Media Transfer Protocol (MTP)
responder daemon written in C. It hooks the Linux FunctionFS/libcomposite or
GadgetFS layer and serves files through the device USB port. This recipe
adapts the umtprd-1.6.8 tag to HarmonyOS PC (aarch64) and delivers:

  - bin/umtprd        daemon binary (plain hand-written Makefile, `make CC=...`)
  - res/umtprd.conf   sample configuration (upstream conf/umtprd.conf,
                      installed as reference; the daemon default path is
                      /etc/umtprd/umtprd.conf and overridable via -conf)
  - licenses/LICENSE  upstream GPL-3.0 license text

Build notes:
  - No conan requirements: the daemon only needs libc (pthread/inotify/
    System V msgqueue) plus Linux USB gadget headers; all come from the
    OHOS sysroot. SYSTEMD=1 / USE_SYSLOG=1 are intentionally NOT enabled
    (no libsystemd on OHOS; syslog path stays at upstream default off).
  - E085 (OHOS musl has no pthread_cancel symbol:
    musl_use_pthread_cancel=false, `ld.lld: undefined symbol:
    pthread_cancel` from src/usb_gadget.c): on OHOS only, build()
    rewrites the two pthread_cancel call sites into `#ifdef __OHOS__`
    cooperative shutdown (the stop flag is already 1 at both sites and
    io_thread() polls it, so pthread_join alone reaps the thread;
    bwfmetaedit/dvgrab/axel precedent). No patch file: exact-statement
    match with count assertions, idempotent via marker comment.
  - The upstream Makefile has no `check`/`test`/`install` targets
    (targets are only all/clean/help), so build() only builds and
    package() copies the artefacts manually.
  - R33: CC comes from Conan conf (tools.build:compiler_executables:c),
    never from bare ${CC}; make comes from user.hmbs:make_path /
    HMBS_MAKE when HMBS provides it, else plain `make`.
  - R9: always -j1.
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class UmtprdConan(ConanFile):
    name = "umtprd"
    version = "1.6.8"
    description = "Lightweight USB Media Transfer Protocol (MTP) responder daemon for GNU/Linux"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/viveris/uMTP-Responder"
    url = "https://github.com/viveris/uMTP-Responder"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"umtprd is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def layout(self):
        # In-source make build (upstream Makefile has no out-of-source
        # support; objects go to obj/ under the source root).
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()

    def build(self):
        # R33: compiler from Conan conf dict, never bare ${CC}.
        # NOTE: tools.build:compiler_executables is a dict conf
        # ({"c": ..., "cpp": ...}); the ":c" suffix form does not exist
        # and raises ConanException (bzip2 1.0.8.2 precedent).
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc_conf = compilers.get("c") if compilers else None
        # HMBS true-machine 2026-10-12: conf still points at
        # /data/service/hnp/bin/clang but that file no longer exists
        # (make: .../clang: No such file or directory, Error 127).
        # Prefer conf when it exists (R33), otherwise fall back to a
        # compiler resolved via PATH (HMBS prepends its tool dirs, so
        # plain `clang` is the OHOS toolchain there). Never pass a
        # non-existent absolute path to make.
        if cc_conf and os.path.isfile(cc_conf):
            cc = cc_conf
        else:
            if cc_conf:
                self.output.warning(
                    f"HMBS: conf compiler missing ({cc_conf}), "
                    "falling back to PATH lookup"
                )
            cc = (
                os.environ.get("CC")
                or shutil.which("clang")
                or shutil.which("cc")
                or shutil.which("gcc")
                or cc_conf
                or "clang"
            )
        self.output.info(f"HMBS: using CC={cc} (conf={cc_conf})")
        make = (
            self.conf.get("user.hmbs:make_path", default=None, check_type=str)
            or os.environ.get("HMBS_MAKE", "make")
        )
        # E085: OHOS musl provides no pthread_cancel symbol; guard the two
        # call sites before compiling (OHOS-only, idempotent no-op on Linux).
        self._patch_ohos_pthread_cancel()
        # Upstream default flags are kept (no SYSTEMD/USE_SYSLOG/DEBUG):
        # plain `make CC=<conan cc> -j1` builds the ./umtprd binary.
        self.run(f"{make} -j1 CC={cc}", cwd=self.source_folder)

    def _patch_ohos_pthread_cancel(self):
        """Guard pthread_cancel call sites on OHOS (E085).

        OHOS musl is built with musl_use_pthread_cancel=false, so the link
        fails with `ld.lld: error: undefined symbol: pthread_cancel`
        (src/usb_gadget.c: handle_ep0 GADGETFS_DISCONNECT handler and
        deinit_usb_mtp_gadget). Both sites already set the stop flag before
        cancelling, and io_thread() exits once is_usb_up() goes false, so
        on __OHOS__ pthread_join alone reaps the thread after the in-flight
        USB read/write returns (bwfmetaedit 26.01 / dvgrab 3.8 / axel
        2.17.14 precedent: skip pthread_cancel on __OHOS__).

        Build-time exact-statement rewrite (ext4fuse 0.1.3 precedent): no
        line numbers baked in, strict count==1 assertions per site so a
        future upstream reformat fails loudly instead of silently, and a
        marker comment makes re-runs idempotent.
        """
        if self.settings.os != "OHOS":
            return
        path = os.path.join(self.source_folder, "src", "usb_gadget.c")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        if "HMBS-OHOS-NO-PTHREAD-CANCEL" in content:
            self.output.info("HMBS: usb_gadget.c OHOS pthread_cancel guard already applied")
            return
        rewrites = [
            (
                "pthread_cancel(ctx->thread);",
                "#ifdef __OHOS__\n"
                "/* HMBS-OHOS-NO-PTHREAD-CANCEL: OHOS musl has no pthread_cancel\n"
                "   (musl_use_pthread_cancel=false); ctx->stop is already 1 so\n"
                "   io_thread() leaves its loop and pthread_join() reaps it. */\n"
                "#else\n"
                "pthread_cancel(ctx->thread);\n"
                "#endif",
            ),
            (
                "pthread_cancel (usbctx->thread);",
                "#ifdef __OHOS__\n"
                "/* HMBS-OHOS-NO-PTHREAD-CANCEL: see above; stop flag already set. */\n"
                "#else\n"
                "pthread_cancel (usbctx->thread);\n"
                "#endif",
            ),
        ]
        for old, new in rewrites:
            count = content.count(old)
            if count != 1:
                raise ConanException(
                    f"HMBS: expected 1 occurrence of {old!r} in src/usb_gadget.c, found {count}"
                )
            content = content.replace(old, new)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        self.output.info("HMBS: applied OHOS pthread_cancel guard to src/usb_gadget.c (2 sites)")

    def package(self):
        # Upstream has no `install` target: copy artefacts manually.
        copy(self, "umtprd", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "umtprd.conf", src=os.path.join(self.source_folder, "conf"),
             dst=os.path.join(self.package_folder, "res"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # Application package: consumers run bin/umtprd, they do not link it.
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.runenv_info.append(
            "PATH", os.path.join(self.package_folder, "bin"))
