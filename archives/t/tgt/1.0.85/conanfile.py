#!/usr/bin/env python3
"""Conan recipe — tgt 1.0.85 (Linux SCSI target framework, plain Makefile build).

Build notes (HarmonyOS PC / aarch64 / musl-based libc):

* Build system is a plain recursive Makefile (no configure/autotools/cmake).
  Only the `usr` (C programs) and `scripts` (tgt-admin, tgt-setup-lun) subtrees
  are built and installed:
    - `doc`  needs xsltproc + docbook XSL (absent in the CI/OHOS image),
    - `conf` installs into /etc, which is outside the Conan package layout.
* Default feature switches are used, so the build needs no third-party Conan
  dependency: ISCSI_RDMA (libibverbs/librdmacm), CEPH_RBD (librados/librbd),
  GLFS_BD (libgfapi) and SD_NOTIFY (libsystemd) are all off, and the aio
  backing store is auto-skipped because OHOS has no <libaio.h>.
* The required Linux UAPI headers (<linux/fs.h>, <linux/major.h>,
  <linux/falloc.h>, <scsi/sg.h>, <asm/byteorder.h>, <sys/eventfd.h>,
  <sys/timerfd.h>, <sys/epoll.h>) are all present in the OHOS native sysroot.
* R33: the compiler comes from Conan conf, never from a shell environment
  variable.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class TgtConan(ConanFile):
    name = "tgt"
    version = "1.0.85"
    description = "Linux SCSI target framework (TGT): user-space iSCSI target daemon (tgtd) and tools (tgtadm, tgtimg)"
    license = "GPL-2.0-only"
    homepage = "https://github.com/fujita/tgt"
    url = ""

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # No third-party dependency: default feature switches only need libc,
    # libpthread and libdl, all provided by the platform.
    requires = ()
    tool_requires = ()

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _cc(self):
        """R33: compiler from Conan conf, never from ${CC}.

        `tools.build:compiler_executables` is a single dict conf (c/cpp/...);
        the dotted `...:c` form is not a registered conf name and would raise.
        """
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        return compilers.get("c") or "clang"

    def build(self):
        apply_conandata_patches(self)
        cc = self._cc()
        # PREFIX=/usr so the compiled-in backing-store module directory
        # (BSDIR) stays /usr/lib/tgt/backing-store as upstream intends.
        # LDFLAGS drops the -rpath to $(libdir): no loadable backing-store
        # module is built with the default feature switches.
        # R9: -j1.
        # basic_layout() puts the build folder in build/<type>; the Makefile is
        # in the source tree, so make must run from the source folder.
        self.run(f"make -C usr CC={cc} PREFIX=/usr LDFLAGS=-Wl,-E -j1",
                 cwd=self.source_folder)

    def package(self):
        # sbindir=/bin puts the programs at <package>/bin (upstream default is
        # $(PREFIX)/sbin, which is not a Conan bindir).
        self.run(f"make -C usr install DESTDIR={self.package_folder} "
                 f"PREFIX=/usr sbindir=/bin", cwd=self.source_folder)
        self.run(f"make -C scripts install DESTDIR={self.package_folder} "
                 f"PREFIX=/usr sbindir=/bin", cwd=self.source_folder)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libs = []
        bin_path = os.path.join(self.package_folder, "bin")
        self.buildenv_info.prepend_path("PATH", bin_path)
        self.runenv_info.prepend_path("PATH", bin_path)
