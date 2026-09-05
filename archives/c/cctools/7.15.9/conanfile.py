#!/usr/bin/env python3
"""Conan recipe for cctools 7.15.9 (Cooperative Computing Tools).

cctools is a suite of tools for cooperative computing, including
Makeflow (workflow engine), Work Queue (task scheduling), Chirp
(distributed storage), and TaskVine.

Upstream: https://github.com/cooperative-computing-lab/cctools
Official source: Debian orig tarball (deb.debian.org is the official Debian mirror)
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, chdir, copy
from conan.tools.gnu import AutotoolsToolchain


class CctoolsConan(ConanFile):
    name = "cctools"
    version = "7.15.9"
    description = "Cooperative Computing Tools (Makeflow, Work Queue, Chirp, TaskVine)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/cooperative-computing-lab/cctools"
    url = "https://github.com/cooperative-computing-lab/cctools"

    package_type = "library"

    # R32: settings.os must use in ("Linux", "OHOS")
    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
    }
    default_options = {
        "shared": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        pass  # Use default layout

    def requirements(self):
        # cctools core requires zlib (link fails without it).
        # R36: zlib must be published first — it is (zlib/1.3.1 in ohpcd).
        self.requires("zlib/1.3.1")

    def validate(self):
        # R32: only Linux/OHOS are supported. Raise early so consumers
        # on other platforms get a clean error instead of a late autotools failure.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"cctools {self.version} only supports os in ('Linux', 'OHOS'), "
                f"got '{self.settings.os}'"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # cctools uses a CUSTOM configure (not standard autotools).
        # It only accepts --prefix and a few --with-*/--without-* options.
        # We bypass AutotoolsToolchain.configure() (which injects --bindir
        # etc. that cctools configure rejects with "Unknown option") but
        # still use AutotoolsToolchain.generate() to create the aggregated
        # conanbuild env that exports CC/CXX from the profile's
        # tools.build:compiler_executables (R33: compiler from Conan conf,
        # not bare shell variable).
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Install into a build-local prefix, NOT package_folder.
        # Conan 2 contract: build() produces artifacts in build_folder,
        # package() copies them to package_folder.
        install_prefix = os.path.join(self.build_folder, "install")
        # cctools configure looks for DIR/include/zlib.h and DIR/lib/libz.a
        zlib_root = self.dependencies["zlib"].package_folder
        with chdir(self, self.source_folder):
            self.run(
                f"./configure --prefix={install_prefix} --with-zlib-path={zlib_root}",
                env="conanbuild",
            )
            self.run("make -j1", env="conanbuild")
            self.run("make install", env="conanbuild")

    def package(self):
        # make install with --prefix=install_prefix places files directly
        # under install_prefix/ (bin/, lib/, include/, ...). Copy them
        # into package_folder/usr/ to match cpp_info.libdirs=["usr/lib"].
        install_prefix = os.path.join(self.build_folder, "install")
        copy(self, "*", src=install_prefix, dst=os.path.join(self.package_folder, "usr"), keep_path=True)

    def package_info(self):
        # cctools installs 6 static libraries under usr/lib/
        self.cpp_info.libs = ["dttools", "chirp", "work_queue",
                              "batch_job", "ftp_lite", "taskvine"]
        self.cpp_info.includedirs = ["usr/include"]
        # cctools also installs executables (makeflow, chirp_server, etc.)
        self.cpp_info.bindirs = ["usr/bin"]
        self.cpp_info.libdirs = ["usr/lib"]
        # zlib is a runtime dependency of cctools
        self.cpp_info.requires = ["zlib::zlib"]
