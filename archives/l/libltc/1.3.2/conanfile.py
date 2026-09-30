#!/usr/bin/env python3
"""Conan recipe for libltc, the Linear/Longitudinal Time Code library."""
import glob as _glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibltcConan(ConanFile):
    name = "libltc"
    version = "1.3.2"
    description = "Linear/Longitudinal Time Code (LTC) Library - encode and decode SMPTE/EBU timecode to/from LTC audio"
    license = "LGPL-3.0-or-later"
    homepage = "https://x42.github.io/libltc/"
    url = "https://github.com/x42/libltc"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS", "FreeBSD", "Macos"):
            raise ConanInvalidConfiguration("libltc is supported only on POSIX-like systems (Linux/OHOS)")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def requirements(self):
        # libltc has no external dependencies: only libc and libm are used.
        pass

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        # Official release tarball; ships a pre-generated configure script,
        # so no autoreconf is needed (unlike the GitHub auto-generated archive).
        get(self, **self.conan_data["sources"], strip_root=True)

    def _ohos_configure_args(self, tc):
        # The bundled config.guess/config.sub date from 2018 and do not
        # know linux-ohos; use a GNU host triple so no patch is needed.
        if str(self.settings.os) == "OHOS":
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-gnu",
            ])

    def generate(self):
        tc = AutotoolsToolchain(self)
        self._ohos_configure_args(tc)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        if self.settings_build.os == "OHOS":
            # E232: HMDFS workers reject direct exec of the configure script
            # (binfmt_script path, Error 126); run it through the native
            # shell instead. Linux CI workers keep Autotools.configure().
            tc = AutotoolsToolchain(self)
            self._ohos_configure_args(tc)
            cmd = 'sh "{}" {}'.format(
                os.path.join(self.source_folder, "configure"),
                " ".join(tc.configure_args),
            )
            self.run(cmd, env="conanbuild")
        else:
            autotools = Autotools(self)
            autotools.configure()
        autotools = Autotools(self)
        autotools.make(args=["-j1"])
        # Upstream self-test: ltcencode/ltcdecode diff against expected
        # output plus the ltcloop encode-decode round trip.
        autotools.make(target="check", args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # Conan 2 copy() has no delete= argument; remove libtool *.la wrappers manually.
        for _la in _glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(_la)

    def package_info(self):
        self.cpp_info.libs = ["ltc"]
        self.cpp_info.system_libs = ["m"]
