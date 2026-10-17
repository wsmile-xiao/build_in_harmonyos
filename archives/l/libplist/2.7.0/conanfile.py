#!/usr/bin/env python3
"""Conan recipe for libplist 2.7.0 — Apple Property List library.

libplist handles Apple Property List files in binary, XML, JSON, and
OpenStep formats.  The release tarball also builds the ``plistutil`` CLI.

OHOS adaptations:
  - a private mktemp wrapper makes autoconf use its mkdir fallback because
    mktemp-created directories can have unusable HMDFS permissions;
  - --build=aarch64-unknown-linux-gnu bypasses config.guess's OHOS gap;
  - Cython bindings are disabled because this package provides the C library;
  - the upstream tools and tests stay enabled so ``make check`` is available.
"""
import stat
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibplistConan(ConanFile):
    name = "libplist"
    version = "2.7.0"
    description = "A library to handle Apple Property List files (binary and XML)"
    license = "LGPL-2.1+"
    homepage = "https://libimobiledevice.org/"
    url = ""  # CI fills this

    # The package exports the libplist library and the upstream plistutil CLI.
    # Keep library semantics for Conan consumers and expose the CLI directory
    # for the repository's mixed library/tool catalog checks.
    package_type = "library"
    bindirs = ["bin"]

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libplist is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def requirements(self):
        # libcnary is bundled by the upstream source; no Conan dependencies.
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if self.settings.os == "OHOS":
            wrapper_dir = Path(self.build_folder) / ".hmos_fix"
            wrapper_dir.mkdir(exist_ok=True)
            wrapper = wrapper_dir / "mktemp"
            wrapper.write_text(
                "#!/bin/sh\n"
                "# HarmonyOS: force autoconf's mkdir fallback for config.status.\n"
                "exit 1\n",
                encoding="utf-8",
            )
            wrapper.chmod(wrapper.stat().st_mode | stat.S_IEXEC)

            # config.guess does not identify HarmonyOS reliably.
            tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
            env = Environment()
            env.prepend_path("PATH", str(wrapper_dir))
            env.vars(self).save_script("hmos_env")

        tc.configure_args.append("--without-cython")
        tc.configure_args.append("--with-tools")
        tc.configure_args.append("--with-tests")
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        # R9: HMDFS can reject make's parallel jobserver fifo.
        autotools.make(args=["-j1"])
        if can_run(self):
            autotools.make(args=["-j1", "check"])

    def package(self):
        Autotools(self).install()

    def package_info(self):
        # The upstream pkg-config module is libplist-2.0.
        self.cpp_info.set_property("cmake_file_name", "libplist-2.0")
        self.cpp_info.set_property("pkg_config_name", "libplist-2.0")
        self.cpp_info.libs = ["plist-2.0"]
        self.cpp_info.bindirs = ["bin"]
        # Static builds use fmin/pow; Autotools discovers and links libm.
        self.cpp_info.system_libs = ["m"]
