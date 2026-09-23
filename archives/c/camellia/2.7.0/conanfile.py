#!/usr/bin/env python3
"""Conan recipe for the Camellia image processing library (CamelliaLib)."""
import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

# mtime of the release tarball entries (2008-01-07); used to pin the whole
# autotools dependency chain to one historical timestamp after patching.
_AUTOTOOLS_PIN_TS = 1199654400


class CamelliaConan(ConanFile):
    name = "camellia"
    version = "2.7.0"
    description = "Camellia low-level image processing and computer vision library"
    license = "BSD-3-Clause"
    homepage = "https://camellia.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("camellia is supported only on Linux/OHOS")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if self.settings.os == "OHOS":
            # The bundled 2007 config.guess cannot classify the OHOS host
            # (patched config.sub accepts the explicit aarch64 triple).
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-gnu",
            ])
        env = tc.environment()
        # The generated src/Makefile hardcodes -I../inc, which only resolves
        # for in-tree builds; Conan builds out-of-tree, so the public header
        # directory must be provided through CPPFLAGS.
        env.append("CPPFLAGS", ["-I{}".format(os.path.join(self.source_folder, "inc"))])
        tc.generate(env=env)

    def _pin_autotools_timestamps(self):
        """Pin the autotools chain to one historical timestamp.

        The patches touch configure and config.sub; automake-generated rules
        rebuild such generated files when their inputs appear newer, which
        would silently roll the patches back. Pinning every chain file to the
        same historical timestamp keeps all rebuild rules inactive.
        """
        chain_names = {
            "configure", "config.guess", "config.sub", "ltmain.sh",
            "compile", "depcomp", "missing", "install-sh",
            "aclocal.m4", "configure.in", "configure.ac",
            "Makefile.am", "Makefile.in",
        }
        chain_suffixes = (".m4", ".am", ".in", ".ac")
        for root, _dirs, files in os.walk(self.source_folder):
            for f in files:
                if f in chain_names or f.endswith(chain_suffixes):
                    path = os.path.join(root, f)
                    os.utime(path, (_AUTOTOOLS_PIN_TS, _AUTOTOOLS_PIN_TS))

    def build(self):
        apply_conandata_patches(self)
        self._pin_autotools_timestamps()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # Conan 2 copy() has no delete= argument; remove libtool *.la wrappers manually.
        for la in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(la)

    def package_info(self):
        self.cpp_info.libs = ["Camellia"]
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.bindirs = ["bin"]
