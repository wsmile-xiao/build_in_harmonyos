#!/usr/bin/env python3
"""Conan recipe — iftop 1.0_pre4 (Autotools application).

iftop is a real-time bandwidth monitoring tool that displays network
usage by host. On HarmonyOS PC it is adapted as follows (see notes.md):

  * ncurses/6.4 and libpcap/1.10.6 come from the ohpcd artifact repo
    (both static packages), so no headers/libs are bundled in the recipe.
  * config.guess/config.sub are patched for HarmonyOS platform detection.
  * pthread_cancel is unavailable on musl/OHOS, replaced with flag +
    pcap_breakloop + pthread_join (guarded by HAVE_PTHREAD_CANCEL).
  * Global variables in ui_common.h are changed to extern declarations.
  * configure umask 077 is replaced with 022 for HMDFS compatibility.

R26: system same-name libs (ncurses) are linked statically to avoid
     shadowing the platform libncursesw.so.6.
R32: settings.os must check in ("Linux", "OHOS").
R38: command-line tool, commands.json declared at software level.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    get, copy, apply_conandata_patches, export_conandata_patches,
)
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class IftopConan(ConanFile):
    name = "iftop"
    version = "1.0_pre4"
    package_type = "application"

    description = "Real-time bandwidth monitoring tool (display bandwidth usage on an interface by host)"
    homepage = "https://pdw.ex-parrot.com/iftop/"
    license = "GPL-2.0-or-later"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        # Patches must be exported with the recipe so apply_conandata_patches
        # can find them in the export sources folder (Conan 2 pattern).
        export_conandata_patches(self)

    def requirements(self):
        # Both dependencies are published on ohpcd with OHOS static binaries.
        self.requires("ncurses/6.4")
        self.requires("libpcap/1.10.6")

    def validate(self):
        # R32: must check in ("Linux", "OHOS"), not == "Linux".
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "iftop only supports Linux/OHOS, not " + str(self.settings.os)
            )

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def _deps_env(self):
        """Collect include/lib dirs from the Conan dependency graph (R33:
        compiler/flags come from the graph, never bare shell variables)."""
        inc = []
        lib = []
        pcap_prefix = None
        ncurses = self.dependencies.get("ncurses")
        if ncurses:
            inc.append(os.path.join(ncurses.package_folder, "include"))
            lib.append(os.path.join(ncurses.package_folder, "lib"))
        libpcap = self.dependencies.get("libpcap")
        if libpcap:
            inc.append(os.path.join(libpcap.package_folder, "include"))
            lib.append(os.path.join(libpcap.package_folder, "lib"))
            pcap_prefix = libpcap.package_folder
        return inc, lib, pcap_prefix

    def build(self):
        top = self.source_folder
        inc, lib, pcap_prefix = self._deps_env()

        # ncurses/6.4 ships curses.h but no ncursesw.h; iftop's configure
        # curses probe tries `#include <ncursesw.h>` with -lncursesw first.
        # Provide a thin wrapper (build-scoped only, never packaged).
        wrapper = os.path.join(self.build_folder, "extra_include")
        os.makedirs(wrapper, exist_ok=True)
        with open(os.path.join(wrapper, "ncursesw.h"), "w") as _f:
            _f.write("#include <curses.h>\n")
        inc.append(wrapper)

        cppflags = " ".join("-I" + p for p in inc)
        ldflags = " ".join("-L" + p for p in lib)
        conf_args = "--prefix=/ --build=aarch64-unknown-linux-ohos"
        # Install sbin binaries to bin/ for CI compatibility (L2/L5 checks)
        conf_args += " --sbindir=${prefix}/bin"
        if pcap_prefix:
            conf_args += " --with-libpcap=" + pcap_prefix

        self.run(
            f"cd {top} && CPPFLAGS='{cppflags}' LDFLAGS='{ldflags}' "
            f"LIBS='-lncursesw -lpcap' bash ./configure {conf_args}",
            env="conanbuild",
        )
        # R26: ncurses is a system same-name lib; the ohpcd ncurses/6.4
        # package is static-only, so the binary links libncursesw.a and
        # libpcap.a statically (NEEDED contains only libc.so).
        self.run(f"cd {top} && make -j1", env="conanbuild")
        # Upstream has no automated test suite (no TESTS target in
        # Makefile.am); run make check to capture that evidence.
        self.run(f"cd {top} && make check 2>&1 || true", env="conanbuild")

    def package(self):
        top = self.source_folder
        self.run(
            f"cd {top} && make install DESTDIR={self.package_folder}",
            env="conanbuild",
        )
        copy(self, "COPYING", src=top,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # iftop is a standalone terminal binary, not a library.
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        # Ensure iftop binary is on PATH for VirtualRunEnv (test_package).
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
