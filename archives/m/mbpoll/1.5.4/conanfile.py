#!/usr/bin/env python3
"""Conan recipe for mbpoll 1.5.4 - Modbus master simulator (CLI tool).

mbpoll is a command line utility to communicate with ModBus slaves (RTU or
TCP). Its only runtime dependency is libmodbus (>= 3.1.7). libmodbus is not
published as a Conan package in the OHOS artifact registry, so it is vendored
here: the official libmodbus 3.1.7 release tarball is built as a *static*
library during this recipe's build(), and mbpoll is then configured (via
pkg-config) and linked against it. The resulting package ships only the
`mbpoll` executable (libmodbus is statically embedded).
"""
import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import (
    get,
    save,
    apply_conandata_patches,
    export_conandata_patches,
)
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.layout import basic_layout

# Minimal <linux/serial.h> kernel-header shim. The musl-based OHOS toolchain
# does not ship linux/serial.h; libmodbus' modbus-rtu.c includes it (behind
# HAVE_DECL_TIOCSRS485) for the RS485 ioctl (struct serial_rs485). This is the
# standard, stable kernel definition.
_LINUX_SERIAL_H = """\
#ifndef _LINUX_SERIAL_H
#define _LINUX_SERIAL_H
#include <stdint.h>

struct serial_rs485 {
    uint32_t flags;
    uint32_t delay_rts_before_send;
    uint32_t delay_rts_after_send;
    uint32_t padding[5];
};

#define SER_RS485_ENABLED        (1u << 0)
#define SER_RS485_RTS_ON_SEND    (1u << 1)
#define SER_RS485_RTS_AFTER_SEND (1u << 2)
#define SER_RS485_RX_DURING_TX   (1u << 4)
#define SER_RS485_TERMINATE_BUS  (1u << 5)

#endif /* _LINUX_SERIAL_H */
"""


class MbpollConan(ConanFile):
    name = "mbpoll"
    version = "1.5.4"
    description = "Command line utility to communicate with ModBus slave (RTU or TCP)"
    license = "GPL-3.0-only"
    homepage = "https://github.com/epsilonrt/mbpoll"
    url = ""  # filled by CI

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        sources = self.conan_data["sources"]
        # mbpoll sources -> source root
        get(self, **sources[0], strip_root=True)
        # vendored libmodbus sources -> libmodbus/ subfolder
        get(self, **{k: v for k, v in sources[1].items() if k != "folder"},
            strip_root=True, destination=os.path.join(self.source_folder, "libmodbus"))

    def generate(self):
        tc = CMakeToolchain(self)
        # Build the mbpoll tool only; upstream unit tests are exercised locally
        # (see notes.md), not wired into the packaged build.
        tc.variables["BUILD_TESTING"] = False
        # piduino (GPIO RS-485 RTS control) is unavailable on OHOS; disable it.
        tc.variables["MBPOLL_CUSTOM_RTS_GPIO"] = False
        # libmodbus is statically linked, so no runtime RPATH is needed; skipping
        # RPATH also avoids cmake's install-time CMakeRelink.dir step failing.
        tc.cache_variables["CMAKE_SKIP_RPATH"] = True
        tc.generate()

        # Expose the vendored libmodbus to mbpoll's pkg_check_modules() lookup.
        lm_pkgconfig = os.path.join(
            self.build_folder, "libmodbus-root", "lib", "pkgconfig")
        env = Environment()
        env.define_path("PKG_CONFIG_PATH", lm_pkgconfig)
        env.vars(self, scope="build").save_script("conan_libmodbus_pkgconfig")

    def build(self):
        apply_conandata_patches(self)
        self._build_libmodbus()

        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    # -- vendored libmodbus (static) --------------------------------------
    def _build_libmodbus(self):
        lm_src = os.path.join(self.source_folder, "libmodbus")
        lm_prefix = os.path.join(self.build_folder, "libmodbus-root")

        # R33: compiler path comes from the Conan conf, not a shell variable.
        comp = self.conf.get("tools.build:compiler_executables", check_type=dict) or {}
        cc = comp.get("c") or comp.get("cpp") or "clang"

        # Provide the linux/serial.h shim on the include path.
        shim = os.path.join(self.build_folder, "include_shim")
        save(self, os.path.join(shim, "linux", "serial.h"), _LINUX_SERIAL_H)

        # E011: HMDFS umask trap - the generated configure/config.status create
        # intermediate dirs with a restrictive umask; relax it.
        for fn in ("configure", "config.status"):
            p = os.path.join(lm_src, fn)
            if os.path.isfile(p):
                _relax_umask(p)

        # libmodbus' bundled config.guess predates OHOS and mis-detects the
        # platform on HarmonyOS workers. Pass an explicit, standard native
        # triplet (build == host with the hnp toolchain) so config.guess is not
        # consulted; aarch64-unknown-linux-gnu validates against config.sub.
        arch = self.settings.arch
        arch_cpu = "aarch64" if str(arch).startswith("arm") else str(arch)
        triplet = "{}-unknown-linux-gnu".format(arch_cpu)

        # Scope CC/CFLAGS to the libmodbus build only so they (and the serial.h
        # shim -I) do not leak into the mbpoll CMake build below.
        saved = {k: os.environ.get(k) for k in ("CC", "CFLAGS")}
        os.environ["CC"] = cc
        os.environ["CFLAGS"] = "-I{} -O2".format(shim)
        try:
            self.run(
                './configure --disable-shared --enable-static '
                '--prefix="{prefix}" --build={triplet} --host={triplet} --quiet'.format(
                    prefix=lm_prefix, triplet=triplet),
                cwd=lm_src)
            self.run("make -j2", cwd=lm_src)
            self.run("make install", cwd=lm_src)
        finally:
            for key, prev in saved.items():
                if prev is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = prev

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # mbpoll is a standalone executable tool (libmodbus is statically linked
        # in); there are no libraries to export.
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]


def _relax_umask(path):
    with open(path, "r") as f:
        content = f.read()
    content = content.replace("umask 077", "umask 022")
    content = content.replace("umask 000", "umask 022")
    with open(path, "w") as f:
        f.write(content)
