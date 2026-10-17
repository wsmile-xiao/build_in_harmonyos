#!/usr/bin/env python3
"""Conan recipe — hogweed 3.9.1 (autotools, part of GNU Nettle).

hogweed is the public-key cryptography library of the GNU Nettle project.
It has no standalone release: version 3.9.1 corresponds to the nettle-3.9.1
official tarball, which builds both libnettle and libhogweed.
"""
from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class HogweedConan(ConanFile):
    name = "hogweed"
    version = "3.9.1"
    description = "Public-key cryptography library from the GNU Nettle project"
    license = "LGPL-3.0-or-later OR GPL-2.0-or-later"
    homepage = "https://www.lysator.liu.se/~nisse/nettle/"
    url = ""
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # hogweed PKI depends on GMP for large-integer arithmetic (R27 format)
        self.requires("gmp/6.3.0.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        if str(self.settings.os) == "OHOS":
            # Explicit triple avoids the bundled config.guess (HMDFS temp-dir probe fails)
            # and matches the OHOS-adapted Conan triplet mapping.
            tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
            tc.configure_args.append("--host=aarch64-unknown-linux-gnu")
        # Prepend dependency (gmp) include/lib dirs so configure finds -lgmp and gmp.h
        # (ecm/7.0.7 pattern; absolute paths only to avoid relative "-Llib" failures).
        import os as _os
        _env = tc.environment()
        _ipaths = [_d for _dep in self.dependencies.values()
                   for _d in (_dep.cpp_info.includedirs or []) if _os.path.isabs(_d)]
        _lpaths = [_d for _dep in self.dependencies.values()
                   for _d in (_dep.cpp_info.libdirs or []) if _os.path.isabs(_d)]
        if _ipaths:
            _env.prepend("CPPFLAGS", " ".join("-I{}".format(_d) for _d in _ipaths))
        if _lpaths:
            # -L for the linker AND runtime search path: configure's GMP_NUMB_BITS /
            # conftest probes LINK and RUN a test binary that dlopens libgmp.so; without
            # LD_LIBRARY_PATH or -rpath the run fails ("Running simple test program
            # failed") and the whole configure aborts at "cannot find value of
            # GMP_NUMB_BITS". (R36: gmp must be consumable, no --build=missing.)
            _env.prepend("LDFLAGS", " ".join("-L{}".format(_d) for _d in _lpaths)
                         + " " + " ".join("-Wl,-rpath,{}".format(_d) for _d in _lpaths))
            _env.prepend("LD_LIBRARY_PATH", ":".join(_lpaths))
        tc.generate(_env)

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["hogweed"]