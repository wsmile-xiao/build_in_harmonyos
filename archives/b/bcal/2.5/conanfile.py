#!/usr/bin/env python3
"""Conan recipe — bcal 2.5 (Makefile)

Byte CALculator — storage expression calculator supporting byte unit
conversion, radix conversion, and bitwise operations.

Build system: plain Makefile (no configure script).
The Makefile uses CC, CPPFLAGS, CFLAGS, LDFLAGS, PREFIX, DESTDIR variables.
Links against system prebuilt readline (headers bundled in res/, dynamic .so).
License: GPLv3
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class BcalConan(ConanFile):
    name = "bcal"
    version = "2.5"
    description = "Byte CALculator — storage expression calculator with byte unit conversion, radix conversion, and bitwise operations"
    license = "GPL-3.0"
    homepage = "https://github.com/jarun/bcal"
    url = "https://github.com/jarun/bcal"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)
        # Export bundled readline headers for CI workers without system readline-devel
        res_src = os.path.join(self.recipe_folder, "res")
        if os.path.isdir(res_src):
            res_dst = os.path.join(self.export_folder, "res")
            if os.path.exists(res_dst):
                shutil.rmtree(res_dst)
            shutil.copytree(res_src, res_dst)

    # System prebuilt readline is NOT in requires() (not a conan package).
    # Headers are bundled in res/headers/ for CI workers.
    # Dynamic libreadline.so.8 is installed by cmd-pkgs to ~/usr/local/lib/external/.

    def _get_sysroot(self):
        """Determine sysroot path via Conan conf, avoiding os.environ (R33)."""
        sysroot = self.conf.get("user.build:default_prefix", default=None, check_type=str)
        if not sysroot:
            sysroot = os.path.expanduser("~/usr/local")
        return sysroot

    def _install_readline(self, sysroot):
        """Install readline via cmd-pkgs using Python urllib (CI workers may lack network tools)."""
        import urllib.request
        import tarfile

        tmpdir = os.environ.get("TMPDIR", os.path.expanduser("~/tmp"))
        os.makedirs(tmpdir, exist_ok=True)
        os.makedirs(sysroot, exist_ok=True)

        pkg_url = "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/readline-8.2-ohos-aarch64.tar.gz"
        tarball = os.path.join(tmpdir, "readline-8.2.tar.gz")
        try:
            urllib.request.urlretrieve(pkg_url, tarball)
            with tarfile.open(tarball) as tar:
                tar.extractall(sysroot)
            self.output.info(f"readline 8.2 installed to {sysroot}")
        except Exception as e:
            self.output.warn(f"readline installation failed: {e}")

    def validate(self):
        # R32: Use `in ("Linux", "OHOS")` for settings.os check
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"bcal supports Linux/OHOS only, got {self.settings.os}"
            )

    def layout(self):
        self.folders.build = "."
        self.folders.generators = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Copy bundled readline headers from export folder to source folder
        export_dir = os.path.join(os.path.dirname(self.source_folder), "e")
        res_src = os.path.join(export_dir, "res")
        if os.path.isdir(res_src):
            res_dst = os.path.join(self.source_folder, "res")
            if os.path.exists(res_dst):
                shutil.rmtree(res_dst)
            shutil.copytree(res_src, res_dst)

    def build(self):
        apply_conandata_patches(self)
        # R33: Get compiler from Conan conf, NEVER from shell env vars.
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = comp_execs.get("c") or "clang"

        # Set up readline include path.
        # Use system headers if available, otherwise bundled res/headers/.
        # R33: sysroot via Conan conf, not os.environ.
        sysroot = self._get_sysroot()
        sys_inc = os.path.join(sysroot, "include")

        cppflags = []
        ldflags = []

        if os.path.exists(os.path.join(sys_inc, "readline", "readline.h")):
            cppflags.append(f"-I{sys_inc}")
        else:
            bundled_inc = os.path.join(self.source_folder, "res", "headers")
            if os.path.isdir(bundled_inc):
                cppflags.append(f"-I{bundled_inc}")

        # Find system libreadline for dynamic linking.
        # OHOS cmd-pkgs installs to ~/usr/local/lib/external/libreadline.so.8
        lib_search_dirs = [
            os.path.join(sysroot, "lib"),
            os.path.join(sysroot, "lib", "external"),
            "/lib",
            "/usr/lib",
        ]
        readline_so = None
        for lib_dir in lib_search_dirs:
            for name in ("libreadline.so", "libreadline.so.8"):
                path = os.path.join(lib_dir, name)
                if os.path.exists(path):
                    readline_so = path
                    ldflags.append(f"-L{lib_dir}")
                    break
            if readline_so:
                break

        # If readline not found, install via cmd-pkgs (network tools may be missing on CI)
        if not readline_so:
            self._install_readline(sysroot)
            for lib_dir in lib_search_dirs:
                for name in ("libreadline.so", "libreadline.so.8"):
                    path = os.path.join(lib_dir, name)
                    if os.path.exists(path):
                        readline_so = path
                        ldflags.append(f"-L{lib_dir}")
                        break
                if readline_so:
                    break

        if not readline_so:
            raise ConanInvalidConfiguration(
                "readline not found and auto-install failed. "
                "Pre-install readline 8.2 via cmd-pkgs to ~/usr/local/"
            )

        # Determine readline link flag
        if readline_so and readline_so.endswith(".so.8") and not os.path.exists(
            os.path.join(os.path.dirname(readline_so), "libreadline.so")
        ):
            # No libreadline.so symlink, use -l: to link exact filename
            readline_libs = "-l:libreadline.so.8"
        else:
            readline_libs = "-lreadline"

        # R9: Always use -j1, never -j$(nproc)
        cppflags_str = " ".join(cppflags) if cppflags else ""
        ldflags_str = " ".join(ldflags) if ldflags else ""
        self.run(
            f'make CC="{cc}" CPPFLAGS="{cppflags_str}" LDFLAGS="{ldflags_str}" '
            f'LDLIBS_READLINE="{readline_libs}" -j1'
        )

    def package(self):
        # Copy the binary to bin/
        copy(self, "bcal", src=self.build_folder, dst=os.path.join(self.package_folder, "bin"))
        # Copy man page
        copy(self, "bcal.1", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        # bcal is a command-line tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        # Add system readline library path to runtime environment
        # libreadline.so.8 is installed by cmd-pkgs to ~/usr/local/lib/external/
        # R33: sysroot via Conan conf, not os.environ.
        sysroot = self._get_sysroot()
        lib_external = os.path.join(sysroot, "lib", "external")
        if os.path.isdir(lib_external):
            self.runenv_info.append_path("LD_LIBRARY_PATH", lib_external)
