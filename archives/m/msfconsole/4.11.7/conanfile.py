#!/usr/bin/env python3
"""Conan recipe for msfconsole 4.11.7 (Metasploit Framework).

This is a custom (non-autotools) build. The package contains:
  - Ruby console scripts (msfconsole, msfvenom, msfrpc, etc.)
  - Two portable C tools (stat-key, time-key) compiled for aarch64
  - Ruby library/modules/data directories

x86-only C tools (cpuid-key, cpuinfo) and Windows/Ruby-extension tools
are skipped with documented reasons.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    get,
    copy,
    export_conandata_patches,
    apply_conandata_patches,
)
from conan.tools.layout import basic_layout


class MsfconsoleConan(ConanFile):
    name = "msfconsole"
    version = "4.11.7"
    description = "Metasploit Framework penetration testing console and tools"
    license = "BSD-3-Clause"
    homepage = "https://github.com/rapid7/metasploit-framework"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # ------------------------------------------------------------------
    # Source / layout
    # ------------------------------------------------------------------

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def build(self):
        apply_conandata_patches(self)

        # R32: settings.os must be Linux or OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"msfconsole only supports Linux/OHOS, got {self.settings.os}"
            )

        # R33: get compiler from Conan conf, NOT from shell env vars
        compiler_executables = self.conf_info.get(
            "tools.build:compiler_executables", default={}
        )
        cc = compiler_executables.get("c", "clang")

        src = self.source_folder

        # --- Compile portable C tools ---

        # stat-key: POSIX stat(), portable to aarch64
        self.run(
            f"{cc} -fPIC -O2 "
            f"-o tools/context/stat-key tools/context/stat-key.c",
            cwd=src,
        )

        # time-key: POSIX time()/strptime(), needs _GNU_SOURCE for strptime
        self.run(
            f"{cc} -fPIC -O2 -D_GNU_SOURCE "
            f"-o tools/context/time-key tools/context/time-key.c",
            cwd=src,
        )

        # --- Skipped C tools (documented) ---
        # cpuid-key.c  — x86 inline asm (cpuid), not supported on aarch64
        # cpuinfo.c    — x86 __asm__("cpuid"), not supported on aarch64
        # memdump.c    — Windows API (<windows.h>), not portable
        # serialport.c — Ruby C extension (<ruby.h>), not standalone binary

    # ------------------------------------------------------------------
    # Package
    # ------------------------------------------------------------------

    def package(self):
        pkg_bin = os.path.join(self.package_folder, "bin")
        pkg_share = os.path.join(self.package_folder, "share", "msfconsole")

        # Ruby console scripts → bin/
        ruby_scripts = [
            "msfconsole", "msfvenom", "msfrpc", "msfrpcd",
            "msfbinscan", "msfd", "msfelfscan", "msfmachscan",
            "msfpescan", "msfrop", "msfupdate",
        ]
        for script in ruby_scripts:
            copy(self, script, src=self.source_folder, dst=pkg_bin)

        # Compiled C tools → bin/
        ctx_dir = os.path.join(self.source_folder, "tools", "context")
        copy(self, "stat-key", src=ctx_dir, dst=pkg_bin)
        copy(self, "time-key", src=ctx_dir, dst=pkg_bin)

        # Ruby library directories → share/msfconsole/
        ruby_dirs = [
            "lib", "modules", "data", "config", "app", "db",
            "documentation", "external", "features", "plugins",
            "script", "scripts", "spec", "test", "tools",
        ]
        for d in ruby_dirs:
            src_d = os.path.join(self.source_folder, d)
            if os.path.isdir(src_d):
                copy(self, "*", src=src_d, dst=os.path.join(pkg_share, d))

        # Gemfile, gemspec, Rakefile → share/msfconsole/
        for f in ["Gemfile", "metasploit-framework.gemspec", "Rakefile"]:
            copy(self, f, src=self.source_folder, dst=pkg_share)

        # License files
        copy(self, "LICENSE", src=self.source_folder, dst=pkg_share)
        copy(self, "COPYING", src=self.source_folder, dst=pkg_share)

    # ------------------------------------------------------------------
    # Package info
    # ------------------------------------------------------------------

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
