#!/usr/bin/env python3
"""Conan recipe for libpipeline 1.5.8 — Autotools build.

libpipeline is a C library for manipulating pipelines of subprocesses in a
flexible and convenient way.  It is the build dependency of dh-exec (which
uses libpipeline >= 1.2.0 through pkg-config).

The archive previously held only manifest/notes/patches for this version —
no conanfile.py — so this recipe is written from scratch against the real
upstream tarball, reusing the three patches that were recorded for it (all
three re-verified to apply cleanly to this exact source).

OHOS adaptation notes (from the recorded patches, re-verified):
  - build-aux/config.guess and build-aux/config.sub need to know the
    `aarch64-unknown-linux-ohos` triple (patches 0001 / 0002).
  - configure's temporary-directory creation uses `umask 077`; on the OHOS
    HMDFS the resulting permissions break config.status (E011), so it is
    relaxed to `umask 022` (patch 0003).

The tarball ships a pre-generated `configure` / `Makefile.in` / `config.h.in`,
so no autoreconf is required at build time.
"""
from conan import ConanFile
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class LibpipelineConan(ConanFile):
    name = "libpipeline"
    version = "1.5.8"
    description = "Pipeline manipulation library"
    license = "LGPL-2.1-or-later"
    homepage = "https://libpipeline.nongnu.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--disable-shared" if not self.options.shared
                                 else "--enable-shared")
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
        env = tc.environment()
        tc.generate(env)
        PkgConfigDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # autotools.install() adds DESTDIR; the .la files are not useful to
        # consumers and can carry absolute build paths.
        from conan.tools.files import rm
        import os
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["pipeline"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("pkg_config_name", "libpipeline")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
