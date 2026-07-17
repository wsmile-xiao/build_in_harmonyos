#!/usr/bin/env python3
"""Conan recipe - dfu-programmer 1.1.0."""
import os
import shlex

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class DfuProgrammerConan(ConanFile):
    name = "dfu-programmer"
    version = "1.1.0"
    description = "Device firmware update programmer for Atmel chips"
    license = "GPL-2.0-or-later"
    homepage = "https://dfu-programmer.github.io/"
    url = "https://github.com/dfu-programmer/dfu-programmer"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    _sys_prefix = os.path.join(os.path.expanduser("~"), "usr", "local")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()
        libusb_prefix = self._libusb_prefix()
        include_flags = (
            f"-I{libusb_prefix}/include/libusb-1.0 "
            f"-I{libusb_prefix}/include "
            f"-I{self._sys_prefix}/include"
        )
        lib_flags = f"-L{libusb_prefix}/lib -L{self._sys_prefix}/lib -lusb-1.0"
        pkgconfig_dir = self._write_libusb_pc(libusb_prefix)

        tc = AutotoolsToolchain(self)
        tc.extra_cflags.extend(include_flags.split())
        tc.extra_ldflags.extend([f"-L{libusb_prefix}/lib", f"-L{self._sys_prefix}/lib"])
        tc.configure_args.extend([
            f"PKG_CONFIG_PATH={pkgconfig_dir}:{libusb_prefix}/lib/pkgconfig:{self._sys_prefix}/lib/pkgconfig",
            f"LIBUSB_CFLAGS={include_flags}",
            f"LIBUSB_LIBS={lib_flags}",
        ])
        tc.generate()

    def _libusb_prefix(self):
        candidates = [
            os.path.join(self._sys_prefix, "libusb-package"),
            self._sys_prefix,
        ]
        for prefix in candidates:
            if os.path.exists(os.path.join(prefix, "include")):
                return prefix
        return candidates[0]

    def _write_libusb_pc(self, prefix):
        pkgconfig_dir = os.path.join(self.generators_folder, "pkgconfig")
        os.makedirs(pkgconfig_dir, exist_ok=True)
        pc_path = os.path.join(pkgconfig_dir, "libusb-1.0.pc")
        with open(pc_path, "w", encoding="utf-8") as pc:
            pc.write(
                "\n".join([
                    f"prefix={prefix}",
                    "exec_prefix=${prefix}",
                    "libdir=${prefix}/lib",
                    "includedir=${prefix}/include/libusb-1.0",
                    "",
                    "Name: libusb-1.0",
                    "Description: USB access library",
                    "Version: 1.0.27",
                    "Libs: -L${libdir} -lusb-1.0",
                    "Cflags: -I${includedir}",
                    "",
                ])
            )
        return pkgconfig_dir

    def build(self):
        configure = os.path.join(self.source_folder, "configure")
        bootstrap = os.path.join(self.source_folder, "bootstrap.sh")
        if not os.path.exists(configure) and os.path.exists(bootstrap):
            self.run(f"sh {shlex.quote(bootstrap)}", env="conanbuild")

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        Autotools(self).install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
