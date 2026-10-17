#!/usr/bin/env python3
"""isatapd 0.9.7 - ISATAP tunnel daemon for HarmonyOS PC (OHOS/aarch64)."""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class IsatapdConan(ConanFile):
    name = "isatapd"
    version = "0.9.7"
    description = "ISATAP (In-Site Address Autoconfiguration Tunneling) tunnel daemon"
    license = "GPL-2.0-or-later"
    homepage = "https://www.saschahlusiak.de/linux/"
    url = ""  # CI fills this

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # OHOS cross triplets: host=OHOS, build=the GNU host triple (R32/§12.1).
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        # AC_FUNC_MALLOC cross-compile false positive -> would substitute rpl_malloc
        # (undefined at link). Seed the cache to force the real malloc/realloc.
        tc.configure_args.append("ac_cv_func_malloc_0_nonnull=yes")
        tc.configure_args.append("ac_cv_func_realloc_0_nonnull=yes")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        # HMDFS denies mkfifo -> recursive `make -j2` jobserver fails; use -j1.
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING", src=self.source_folder, dst=self.package_folder,
             keep_path=False)

    def package_info(self):
        # Upstream installs the daemon to ${sbindir}, but AutotoolsToolchain passes
        # --sbindir=${prefix}/bin, so the packaged binary lands in bin/ (W3 log).
        self.cpp_info.bindirs = ["bin"]
