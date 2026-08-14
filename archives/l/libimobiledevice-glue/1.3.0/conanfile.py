#!/usr/bin/env python3
"""Conan recipe for libimobiledevice-glue 1.3.0 — common glue code for libimobiledevice.

# Dependency: libplist/2.3.0 (PR #4429)
libimobiledevice-glue provides socket helpers, thread/mutex abstraction,
string/file helpers, plist helpers, and SHA-1/256/512 functions shared
across libimobiledevice ecosystem libraries. The pkg-config name is
libimobiledevice-glue-1.0.

Dependencies:
  - libplist/2.3.0 (Apple Property List library, published on ohpcd)

OHOS adaptations:
  - mktemp wrapper: autoconf AS_TMPDIR uses `umask 077 && mktemp -d`
    which creates dirs with drwx--S--- on HMDFS (setgid + MAC), causing
    config.status to fail writing subs*.awk. A fake mktemp that returns
    failure forces the mkdir fallback (E114).
  - --build=aarch64-unknown-linux-gnu: config.guess doesn't recognize OHOS.
  - AutotoolsDeps: feeds -I/-L/-l from libplist into configure/make.
  - LD_LIBRARY_PATH: OHOS loader has no default search path for conan-cached
    shared libs; configure conftest programs need LD_LIBRARY_PATH set.
"""
import stat
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps
from conan.tools.layout import basic_layout
from conan.tools.env import Environment
from conan.tools.gnu import PkgConfigDeps


class LibimobiledeviceGlueConan(ConanFile):
    name = "libimobiledevice-glue"
    version = "1.3.0"
    description = "Common glue code for libimobiledevice libraries (socket, thread, SHA, utils)"
    license = "LGPL-2.1+"
    homepage = "https://libimobiledevice.org/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libimobiledevice-glue is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def requirements(self):
        self.requires("libplist/2.3.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # HarmonyOS: mktemp -d creates dirs with drwx--S--- (broken group perms),
        # causing config.status to fail writing subs*.awk. Create a mktemp wrapper
        # that returns failure to force autoconf AS_TMPDIR to use mkdir fallback.
        wrapper_dir = Path(self.build_folder) / ".hmos_fix"
        wrapper_dir.mkdir(exist_ok=True)
        wrapper = wrapper_dir / "mktemp"
        wrapper.write_text(
            '#!/bin/sh\n'
            '# HarmonyOS: mktemp -d creates dirs with broken perms (hmmac MAC).\n'
            '# Return failure to force autoconf AS_TMPDIR to use mkdir fallback.\n'
            'exit 1\n'
        )
        wrapper.chmod(wrapper.stat().st_mode | stat.S_IEXEC)

        # AutotoolsDeps: feed -I/-L/-l from libplist into configure/make
        deps = AutotoolsDeps(self)
        deps.generate()

        # PkgConfigDeps: generate .pc files for pkg-config based configure checks
        pkgconfig = PkgConfigDeps(self)
        pkgconfig.generate()

        tc = AutotoolsToolchain(self)
        # HarmonyOS: config.guess doesn't recognize the OS, force build triplet
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        # R26: static linking for system-name libraries
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

        # Prepend wrapper to PATH
        env = Environment()
        env.prepend_path("PATH", str(wrapper_dir))
        # OHOS loader has no default search path for conan-cached shared libs.
        # configure's conftest runs compiled programs, which fail with
        # "Error loading shared library" unless LD_LIBRARY_PATH points at deps.
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                env.prepend_path("LD_LIBRARY_PATH", libdir)
        env.vars(self, scope="build").save_script("hmos_env")

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        # R9: single job — parallel make hits HMDFS jobserver fifo EPERM
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # pkg-config name is libimobiledevice-glue-1.0
        self.cpp_info.set_property("cmake_file_name", "libimobiledevice-glue-1.0")
        self.cpp_info.set_property("pkg_config_name", "libimobiledevice-glue-1.0")
        self.cpp_info.libs = ["imobiledevice-glue-1.0"]

