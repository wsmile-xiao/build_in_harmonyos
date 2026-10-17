#!/usr/bin/env python3
"""Conan recipe for tipidee 0.0.6.0.

tipidee is a small HTTP server library and daemon by skarnet.org.
It provides libtipidee (helpers to write an HTTP server) and
the tipideed HTTP daemon.

Build system: skarnet custom configure + Makefile (not autotools).
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout


class TipideeConan(ConanFile):
    name = "tipidee"
    version = "0.0.6.0"
    description = "A library containing helpers to write an HTTP server, and the tipideed HTTP daemon"
    license = "ISC"
    homepage = "https://skarnet.org/software/tipidee/"
    url = ""
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("tipidee is supported only on Linux/OHOS")

    def requirements(self):
        # skalibs/2.14.4.0 was never published to the registry (its PR stayed
        # open); 2.15.1.0 is the published, API-compatible skarnet release.
        self.requires("skalibs/2.15.1.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass

    def build(self):
        # skarnet configure is NOT autotools — no AutotoolsToolchain.
        # R33: CC/CXX and PATH come from the conanbuild env (profile [buildenv]
        # PATH + tools.build:compiler_executables conf exported as CC/CXX);
        # never read bare ${CC}/${CFLAGS} shell variables here.
        # OHOS clang may ship without a usable default sysroot, in which case
        # skarnet configure's link probes abort with "unable to determine
        # required linker flags for socket functions". Inject --sysroot via
        # LDFLAGS so the probes always link (same approach as the published
        # skalibs/2.15.1.0 recipe).
        sysroots = sorted(glob.glob(
            "/data/service/hnp/ohos-sdk.org/*/ohos/native/sysroot"
        ))
        if sysroots:
            cur = os.environ.get("LDFLAGS", "").strip()
            os.environ["LDFLAGS"] = f"{cur} --sysroot={sysroots[-1]}".strip()

        # Get skalibs paths from dependency
        skalibs = self.dependencies["skalibs"]
        skalibs_prefix = skalibs.package_folder
        skalibs_include = os.path.join(skalibs_prefix, "include")
        skalibs_lib = os.path.join(skalibs_prefix, "lib")
        skalibs_sysdeps = os.path.join(skalibs_prefix, "lib", "skalibs", "sysdeps")

        # skarnet custom configure (not autotools)
        self.run(
            f'./configure --prefix=/usr '
            f'--with-include="{skalibs_include}" '
            f'--with-lib="{skalibs_lib}" '
            f'--with-dynlib="{skalibs_lib}" '
            f'--with-sysdeps="{skalibs_sysdeps}" '
            f'--enable-pkgconfig '
            f'--disable-shared',
            cwd=self.source_folder,
            env="conanbuild",
        )
        # R9: skarnet build order matters — use -j1
        self.run("make -j1", cwd=self.source_folder, env="conanbuild")

    def package(self):
        self.run(
            f'make install DESTDIR="{self.package_folder}"',
            cwd=self.source_folder,
            env="conanbuild",
        )
        src = os.path.join(self.package_folder, "usr")
        # Library
        copy(self, "*.a", src=os.path.join(src, "lib"), dst=os.path.join(self.package_folder, "lib"))
        copy(self, "*.pc", src=os.path.join(src, "lib", "pkgconfig"), dst=os.path.join(self.package_folder, "lib", "pkgconfig"))
        # Headers
        copy(self, "*.h", src=os.path.join(src, "include"), dst=os.path.join(self.package_folder, "include"))
        # Binaries (tipideed, tipidee-config)
        copy(self, "tipideed", src=os.path.join(src, "bin"), dst=os.path.join(self.package_folder, "bin"))
        copy(self, "tipidee-config", src=os.path.join(src, "bin"), dst=os.path.join(self.package_folder, "bin"))
        # Libexec (ls.cgi, tipidee-config-preprocess)
        copy(self, "*", src=os.path.join(src, "libexec"), dst=os.path.join(self.package_folder, "libexec"))
        # Remove the usr/ staging directory
        import shutil
        shutil.rmtree(src, ignore_errors=True)

    def package_info(self):
        self.cpp_info.libs = ["tipidee"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]
        # tipidee headers include skalibs headers - declare transitive dependency
        self.cpp_info.requires = ["skalibs::skalibs"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
