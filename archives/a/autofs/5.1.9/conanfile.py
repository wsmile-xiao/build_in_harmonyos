#!/usr/bin/env python3
"""Conan recipe for autofs 5.1.9 (automount daemon) on OHOS.

The automount daemon depends on libtirpc for TI-RPC support, and on the
POSIX thread cancellation API that the OHOS SDK sysroot does not export.
This recipe:

 * requires libtirpc/1.3.7 from the ohos PC package registry (R36);
 * applies the bundled patch adding lib/ohos_pthread_shim.c (a deferred
   cancellation shim backed by per-thread flags);
 * applies in-build Python source fixes (HMDFS umask, procfs probe,
   link order) that the toybox `patch` on the OHOS worker cannot apply
   reliably.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class AutofsConan(ConanFile):
    name = "autofs"
    version = "5.1.9"
    description = "Kernel-based automounter for Linux (automount daemon)"
    license = "GPL-2.0-only"
    homepage = "https://www.kernel.org/pub/linux/daemons/autofs/"
    url = "https://www.kernel.org/pub/linux/daemons/autofs/v5/"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("autofs supported only on Linux/OHOS")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require aarch64/armv8")

    def requirements(self):
        self.requires("libtirpc/1.3.7")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        pc = PkgConfigDeps(self)
        # Explicitly set the sysroot and compiler flags via environment
        # (AutotoolsToolchain.extra_cflags is unreliable on OHOS CI)
        tc.extra_cflags = ["--sysroot=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot"]
        tc.extra_cxxflags = ["--sysroot=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot"]
        tc.extra_ldflags = ["--sysroot=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot"]
        tc.configure_args.extend([
            "--with-libtirpc",
            "--with-path=/data/service/hnp/bin:/storage/Users/currentUser/usr/local/bin:/usr/bin:/bin",
            "--disable-gssapi",
            "--disable-ldap",
            "--disable-sasl",
            "--disable-nisplus",
            "--without-hesiod",
            "--without-systemd",
        ])
        tc.generate()
        pc.generate()

    # ------------------------------------------------------------------
    # OHOS-specific source fixes that toybox `patch` cannot apply
    # ------------------------------------------------------------------
    def _fix_makefiles(self):
        """Patch lib/Makefile and daemon/Makefile for OHOS build."""
        lib_mk = os.path.join(self.source_folder, "lib", "Makefile")
        with open(lib_mk, "r") as f:
            content = f.read()
        if "ohos_pthread_shim.c" not in content:
            content = content.replace(
                "\tparse_subs.c dev-ioctl-lib.c\n",
                "\tparse_subs.c dev-ioctl-lib.c ohos_pthread_shim.c\n")
            content = content.replace(
                "\tparse_subs.o dev-ioctl-lib.o\n",
                "\tparse_subs.o dev-ioctl-lib.o ohos_pthread_shim.o\n")
            with open(lib_mk, "w") as f:
                f.write(content)

        daemon_mk = os.path.join(self.source_folder, "daemon", "Makefile")
        with open(daemon_mk, "r") as f:
            content = f.read()
        old_link = "$(CC) $(DAEMON_LDFLAGS) -o automount $(OBJS) $(LDFLAGS) $(LIBS) $(AUTOFS_LIB_LINK)"
        new_link = "$(CC) $(DAEMON_LDFLAGS) -o automount $(OBJS) $(LDFLAGS) $(AUTOFS_LIB_LINK) $(LIBS) -pthread"
        if old_link in content:
            content = content.replace(old_link, new_link)
            with open(daemon_mk, "w") as f:
                f.write(content)

    def _fix_procfs_check(self):
        """Relax the /proc probe for OHOS (ostype reports HarmonyOS)."""
        hdr = os.path.join(self.source_folder, "include", "automount.h")
        with open(hdr, "r") as f:
            content = f.read()
        if "__OHOS__" not in content:
            content = content.replace(
                "#ifndef HAVE_LINUX_PROCFS\n",
                "#if !defined(HAVE_LINUX_PROCFS) && !defined(__OHOS__)\n", 1)
            with open(hdr, "w") as f:
                f.write(content)

    def _fix_configure_umask(self):
        """umask 077 in config.status breaks on HMDFS (Permission denied).

        NOTE (deviation from R6): OHOS workers ship the toybox `patch`
        which silently no-ops hunks that edit existing files (verified
        experimentally), so edits to the bundled `configure` cannot be
        expressed as a reliable conandata patch.  Hence this in-build
        Python rewrite.  The replaced string is inside configure's
        AC_CONFIG_STATUS generation block and is stable across autoconf
        regenerations of this release.
        """
        cfg = os.path.join(self.source_folder, "configure")
        with open(cfg, "r") as f:
            content = f.read()
        if "umask 000" not in content:
            content = content.replace("umask 077", "umask 000")
            with open(cfg, "w") as f:
                f.write(content)

    def build(self):
        apply_conandata_patches(self)
        self._fix_makefiles()
        self._fix_procfs_check()
        self._fix_configure_umask()
        autotools = Autotools(self)
        src_dir = self.source_folder
        # HMDFS (E046) does not honour chmod +x, run configure via sh(1).
        # basic_layout puts build_folder in a subdirectory; configure must
        # run from the source root (where Makefile lives).
        self.run("cd " + src_dir + " && test -f include/config.h || "
                 "{ CFLAGS=\"$CFLAGS --sysroot=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot\" "
                 "CXXFLAGS=\"$CXXFLAGS --sysroot=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot\" "
                 "LDFLAGS=\"$LDFLAGS --sysroot=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot\" "
                 "PATH=/data/service/hnp/bin:$PATH /bin/sh configure"
                 " --prefix=/ --with-libtirpc "
                 "--with-path=/data/service/hnp/bin:/storage/Users/currentUser/usr/local/bin:/usr/bin:/bin "
                 "--disable-gssapi --disable-ldap --disable-sasl --disable-nisplus "
                 "--without-hesiod --without-systemd; }",
                 env="conanbuild")
        self.run("make -C " + src_dir + " -j1", env="conanbuild")

    def package(self):
        # autofs does in-source builds: Makefile lives in src_dir
        self.run("make -C " + self.source_folder + " install DESTDIR=" + self.package_folder,
                 env="conanbuild")
        copy(self, "*.conf", src=os.path.join(self.source_folder, "samples"),
             dst=os.path.join(self.package_folder, "etc", "autofs"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["sbin"]
        self.cpp_info.libs = ["autofs"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "sbin"))