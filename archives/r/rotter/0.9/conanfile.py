#!/usr/bin/env python3
"""Conan recipe — rotter 0.9 (autotools application).

Rotter is a Recording of Transmission / Audio Logger for JACK: it runs
continuously, writing hour-long audio archives (MP3/MP2/WAV/AIFF/...).

Build system: autotools (configure + make, no libtool).
License: GPL-2.0-or-later.
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class RotterConan(ConanFile):
    name = "rotter"
    version = "0.9"
    description = "Rotter — a Recording of Transmission / Audio Logger for JACK (hourly archive files)"
    license = "GPL-2.0-or-later"
    homepage = "https://www.aelius.com/njh/rotter/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("jack/1.9.22")       # JACK audio connection kit (mandatory)
        self.requires("libsndfile/1.2.2")  # file output backend (mandatory)
        self.requires("lame/3.100")        # MP3 codec (optional upstream, enabled here)
        self.requires("twolame/0.4.0")     # MP2 codec (optional upstream, enabled here)

    def layout(self):
        basic_layout(self)

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # PKG_CHECK_MODULES(JACK, jack >= 0.100.0 / TWOLAME, twolame >= 0.3.9 /
        # SNDFILE, sndfile >= 1.0.18): generate .pc files for all deps and
        # point PKG_CONFIG_PATH at them.
        PkgConfigDeps(self).generate()

        tc = AutotoolsToolchain(self)
        # rotter.h defines globals without `extern` (2010-era code written for
        # GCC's default -fcommon); clang >= 10 defaults to -fno-common.
        tc.extra_cflags.append("-fcommon")
        # Start from the toolchain's own environment (carries CFLAGS) and add
        # the paths this project needs on top.
        env = tc.environment()

        # configure link checks run their conftest programs on the host, so the
        # dynamic loader must find the dependency shared libraries. lame ships
        # no .pc file and configure finds it via AC_CHECK_LIB(-lmp3lame), which
        # needs explicit -I/-L paths (AutotoolsToolchain does not add them).
        for dep in self.dependencies.host.values():
            for incdir in dep.cpp_info.includedirs:
                env.append_path("CPPFLAGS", f"-I{incdir}")
            for libdir in dep.cpp_info.libdirs:
                env.append_path("LDFLAGS", f"-L{libdir}")
                env.append_path("LD_LIBRARY_PATH", libdir)
        env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)

        tc.generate(env=env)

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # Command-line application, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
