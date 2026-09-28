#!/usr/bin/env python3
"""Conan recipe — qcontrol 0.5.7 (upstream raw Makefile, C only).

qcontrol is a daemon plus command line tool that drives the peripherals of
embedded NAS boxes (LCD panels, buttons, fans, LEDs, watchdogs): the QNAP
TS-109/209/219/409/41x families and Synology Diskstations.
Upstream: https://www.hellion.org.uk/qcontrol/

Adaptation notes for HarmonyOS PC (aarch64, musl libc, clang 15):

1. Dependency discovery is the only real work here.  The upstream Makefile
   locates its single library dependency through pkg-config using a
   hard coded module name:

       CFLAGS       += $(shell $(PKG_CONFIG) --cflags lua5.1)
       LIBS_DYNAMIC += -lpthread $(shell $(PKG_CONFIG) --libs lua5.1)

   Measured on the build host against a PkgConfigDeps generated from
   lua/5.1.5 (see archives/q/qcontrol/0.5.7/notes.md):  the published
   pkg-config module is named "lua-5.1" (cpp_info pkg_config_name), so
   "pkg-config --exists lua5.1" exits 1 with
   "No package 'lua5.1' found" and both $(shell ...) expansions come back
   with the error text on stdout instead of flags.  The module under its
   published name does resolve correctly and yields
   "-DLUA_USE_POSIX -DLUA_USE_DLOPEN -I<lua>/include" and
   "-L<lua>/lib -llua -ldl -lm", so the name is the only defect - and the
   published lib is a static liblua.a, so nothing has to be shared.
   Rather than patching the Makefile or dropping an alias .pc file, both
   pkg-config derived variables are substituted on the make command line
   from the Conan dependency's own cpp_info (CFLAGS, LIBS_DYNAMIC), which
   also keeps the -lpthread that upstream already assumes and does not
   depend on a pkg-config binary being present on the worker.
2. PKG_CONFIG=false additionally neutralises the optional
   libsystemd-daemon probe (Makefile lines 13-17), so -DHAVE_SYSTEMD stays
   off.  OHOS has no systemd, and the socket-activation branch
   (sd_listen_fds) must not be compiled in.
3. Upstream CFLAGS carry -g, which embeds the build-machine path of the
   Conan build folder into the shipped ELF.  -g is therefore dropped; the
   remaining upstream flags (-c -Os -Wall -Wextra) are kept verbatim and
   test_package/test_ohos.sh asserts that no host build path survives in
   the packaged binary.
4. CPPFLAGS (and with it the upstream version string define
   -DQCONTROL_VERSION) and LDFLAGS are deliberately *not* overridden, so
   qcontrol --version keeps reporting the upstream-generated version.
5. Upstream hardware assumptions recorded but not fixed here: every driver
   opens a hard coded serial device (/dev/ttyS0 or /dev/ttyS1) through
   termios, the daemon binds the hard coded AF_UNIX path
   /var/run/qcontrol.sock, and confdir() globs a directory of *.conf
   files.  None of those NAS devices exist on a HarmonyOS PC, so the
   consumer test drives the platform-independent half (argument parsing,
   config loading through the embedded Lua interpreter, command dispatch)
   and reports the device/socket dependent half as a graceful diagnostic
   instead of pretending the hardware is there.

Build system: plain Makefile, no configure script, no install rule
(the binary is packaged by copy(), see package()).
"""
import os
import shlex

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout
from conan.errors import ConanInvalidConfiguration


class QcontrolConan(ConanFile):
    name = "qcontrol"
    version = "0.5.7"
    description = (
        "Daemon and command line tool controlling the peripherals (LCD, "
        "buttons, fans, LEDs, watchdog) of QNAP and Synology NAS devices"
    )
    license = "GPL-2.0-or-later"
    homepage = "https://www.hellion.org.uk/qcontrol/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Upstream's only library dependency (embedded config interpreter).
        self.requires("lua/5.1.5")

    def validate(self):
        # R32: OHOS and Linux are both accepted, never compare os == "Linux".
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "qcontrol needs POSIX termios, glob and AF_UNIX: "
                "supported on Linux and OHOS only"
            )

    def layout(self):
        basic_layout(self)
        # Upstream builds its objects next to the sources (%.o-dyn: %.c),
        # so build in the source tree instead of a sub directory.
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _lua_flags(self):
        """Substitute the two pkg-config derived Makefile variables."""
        lua = self.dependencies["lua"].cpp_info
        compile_flags = []
        link_flags = ["-L" + d for d in lua.libdirs]
        link_flags += ["-l" + lib for lib in lua.libs]
        link_flags += ["-l" + lib for lib in lua.system_libs]
        return {
            "defines": " ".join("-D" + d for d in lua.defines),
            "includes": " ".join("-I" + d for d in lua.includedirs),
            "link": " ".join(link_flags),
        }

    def build(self):
        apply_conandata_patches(self)

        # R33: the compiler comes from the Conan conf, never from ${CC}.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang")
        lua = self._lua_flags()

        cflags = " ".join(
            ["-c", "-Os", "-Wall", "-Wextra", lua["defines"], lua["includes"]]
        )
        libs_dynamic = " ".join(["-lpthread", lua["link"]])

        # "all" builds the dynamic target, i.e. the qcontrol binary.  The
        # upstream "qcontrol-static" target is not built: it hard codes the
        # path $(pkg-config --variable=libdir lua5.1)/liblua5.1.a, a file
        # name that does not exist in the Conan lua/5.1.5 package (liblua.a).
        self.run(" ".join([
            "make", "-j1", "all",
            "CC=" + shlex.quote(cc),
            "PKG_CONFIG=false",
            "CFLAGS=" + shlex.quote(cflags),
            "LIBS_DYNAMIC=" + shlex.quote(libs_dynamic),
        ]))

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        copy(self, "qcontrol", src=self.build_folder, dst=bin_dir)

        packaged_binary = os.path.join(bin_dir, "qcontrol")
        if not os.path.isfile(packaged_binary):
            # Fail closed: never ship a package whose executable is absent.
            raise RuntimeError(
                "qcontrol binary missing from the package: upstream make "
                "did not produce it"
            )

        # Example configurations for the supported NAS models (data files,
        # useful to whoever points -c at them).
        copy(self, "*.lua",
             src=os.path.join(self.source_folder, "examples"),
             dst=os.path.join(self.package_folder, "share", "qcontrol",
                              "examples"))
        copy(self, "README", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "doc", "qcontrol"))
        copy(self, "HACKING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "doc", "qcontrol"))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # The upstream systemd units (systemd/*.service, *.socket) are not
        # packaged: OHOS has no systemd, and they reference /usr/sbin paths
        # that do not exist here.

    def package_info(self):
        # Application package: export the executable only, no cpp_info.libs
        # (nothing here is linkable by a downstream consumer).
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["share"]
