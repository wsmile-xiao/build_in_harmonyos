#!/usr/bin/env python3
"""Conan recipe for fprobe-ulog 1.2 — ULOG/NFLOG NetFlow probe.

Builds fprobe-ulog with inline dependencies (libmnl, libnetfilter_log)
since they are not available as conan packages in the OHOS repository.
libnfnetlink is used from the conan repository.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, save, replace_in_file, apply_conandata_patches, export_conandata_patches
from conan.tools.env import Environment
from conan.errors import ConanInvalidConfiguration


class FprobeUlogConan(ConanFile):
    name = "fprobe-ulog"
    version = "1.2"
    description = "ULOG/NFLOG NetFlow probe for network traffic monitoring"
    license = "GPL-2.0"
    homepage = "https://github.com/opoplawski/fprobe-ulog"
    url = ""  # CI fills this

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"fprobe-ulog only supports Linux/OHOS, got {self.settings.os}"
            )

    def requirements(self):
        self.requires("libnfnetlink/1.0.2")

    def layout(self):
        self.folders.source = "."
        self.folders.build = "."
        self.folders.generators = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _create_compat_header(self, dest_dir):
        """Create compat_fixup.h to resolve header conflicts on OHOS."""
        save(self, os.path.join(dest_dir, "compat_fixup.h"),
             """/* compat_fixup.h - Fix header conflicts on HarmonyOS */
#ifndef _COMPAT_FIXUP_H
#define _COMPAT_FIXUP_H
#include <sys/socket.h>
#define _UAPI_LINUX_SOCKET_H
#ifndef __KERNEL_SA_FAMILY_T
#define __KERNEL_SA_FAMILY_T
typedef unsigned short __kernel_sa_family_t;
#endif
#endif
""")

    def _create_nfnl_wrapper(self, wrapper_dir, nfnl_include):
        """Create wrapper header for libnfnetlink to resolve conflicts with OHOS SDK.

        Instead of modifying the dependency's installed header, we create a
        wrapper in a separate directory that takes include priority.
        """
        wrapper_path = os.path.join(wrapper_dir, "libnfnetlink", "linux_nfnetlink.h")
        os.makedirs(os.path.dirname(wrapper_path), exist_ok=True)
        save(self, wrapper_path,
             """/* Wrapper: forward to system kernel header to avoid conflicts */
#ifndef _UAPI_NFNETLINK_H
#include <linux/netfilter/nfnetlink.h>
#endif
#include <libnfnetlink/linux_nfnetlink_compat.h>
""")

    def _create_config_guess_sub(self, dest_dir):
        """Create config.guess and config.sub for HarmonyOS (used for inline deps)."""
        save(self, os.path.join(dest_dir, "config.guess"),
             '#!/bin/sh\necho "aarch64-unknown-linux-gnu"\nexit 0\n')
        os.chmod(os.path.join(dest_dir, "config.guess"), 0o755)
        save(self, os.path.join(dest_dir, "config.sub"),
             '#!/bin/sh\necho "$1"\nexit 0\n')
        os.chmod(os.path.join(dest_dir, "config.sub"), 0o755)

    def _fix_umask(self, file_path):
        """Fix umask 077 -> 022 for HMDFS compatibility (used for inline deps)."""
        try:
            replace_in_file(self, file_path, "umask 077", "umask 022")
        except Exception as e:
            self.output.warning(f"Failed to fix umask in {file_path}: {e}")

    def generate(self):
        env = Environment()
        env.define("CC", "clang")
        env.define("CXX", "clang++")
        env.define("TMPDIR", os.path.join(self.build_folder, "tmp"))
        env.vars(self).save_script("fprobe_ulog_env")

    def build(self):
        # Apply patches (config.guess, config.sub, configure umask fix)
        apply_conandata_patches(self)

        tmp_dir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmp_dir, exist_ok=True)

        compat_h = os.path.join(self.build_folder, "compat_fixup.h")
        self._create_compat_header(self.build_folder)

        # Get libnfnetlink paths from conan dependency
        dep = self.dependencies["libnfnetlink"]
        nfnl_pkg = dep.package_folder
        nfnl_include = os.path.join(nfnl_pkg, "include")
        nfnl_libdir = os.path.join(nfnl_pkg, "lib")

        # Create wrapper header for libnfnetlink (avoids modifying dependency files)
        wrapper_dir = os.path.join(self.build_folder, "nfnl_wrapper")
        self._create_nfnl_wrapper(wrapper_dir, nfnl_include)

        cflags_base = f"-fPIC -O2 -include {compat_h} -I{wrapper_dir}"

        # --- Build libmnl (inline dependency) ---
        libmnl_src = os.path.join(self.build_folder, "libmnl-1.0.5")
        libmnl_prefix = os.path.join(self.build_folder, "deps", "libmnl")
        os.makedirs(libmnl_prefix, exist_ok=True)

        get(self, **self.conan_data["additional_sources"]["libmnl"],
            destination=self.build_folder, strip_root=False)
        self._create_config_guess_sub(libmnl_src)
        ba = os.path.join(libmnl_src, "build-aux")
        if os.path.isdir(ba):
            shutil.copy(os.path.join(libmnl_src, "config.guess"), ba)
            shutil.copy(os.path.join(libmnl_src, "config.sub"), ba)
        self._fix_umask(os.path.join(libmnl_src, "configure"))

        self.run(
            f'cd "{libmnl_src}" && '
            f'CC=clang CFLAGS="{cflags_base}" TMPDIR="{tmp_dir}" '
            f'./configure --prefix="{libmnl_prefix}" && '
            f'make -j1 && make install'
        )

        # --- Build libnetfilter_log (inline dependency) ---
        libnfl_src = os.path.join(self.build_folder, "libnetfilter_log-1.0.2")
        libnfl_prefix = os.path.join(self.build_folder, "deps", "libnetfilter_log")
        os.makedirs(libnfl_prefix, exist_ok=True)

        get(self, **self.conan_data["additional_sources"]["libnetfilter_log"],
            destination=self.build_folder, strip_root=False)
        self._create_config_guess_sub(libnfl_src)
        ba = os.path.join(libnfl_src, "build-aux")
        if os.path.isdir(ba):
            shutil.copy(os.path.join(libnfl_src, "config.guess"), ba)
            shutil.copy(os.path.join(libnfl_src, "config.sub"), ba)
        self._fix_umask(os.path.join(libnfl_src, "configure"))

        nfl_cflags = f"{cflags_base} -I{libmnl_prefix}/include -I{nfnl_include}"
        nfl_ldflags = f"-L{libmnl_prefix}/lib -L{nfnl_libdir}"

        self.run(
            f'cd "{libnfl_src}" && '
            f'CC=clang CFLAGS="{nfl_cflags}" LDFLAGS="{nfl_ldflags}" '
            f'LIBNFNETLINK_CFLAGS="-I{wrapper_dir} -I{nfnl_include}" '
            f'LIBNFNETLINK_LIBS="-L{nfnl_libdir} -lnfnetlink" '
            f'PKG_CONFIG_PATH="{libmnl_prefix}/lib/pkgconfig" '
            f'TMPDIR="{tmp_dir}" '
            f'./configure --prefix="{libnfl_prefix}" && '
            f'make -j1 && make install'
        )

        # --- Build fprobe-ulog ---
        # Patches declared in conandata.yml for CI; also apply directly here
        # as belt-and-suspenders (patches may not apply in all conan versions)
        src = self.source_folder
        self._create_config_guess_sub(src)
        self._fix_umask(os.path.join(src, "configure"))
        fp_cflags = f"{cflags_base} -I{libnfl_prefix}/include -I{nfnl_include}"
        fp_ldflags = f"-L{libnfl_prefix}/lib -L{libmnl_prefix}/lib -L{nfnl_libdir}"

        self.run(
            f'cd "{src}" && '
            f'CC=clang CFLAGS="{fp_cflags}" LDFLAGS="{fp_ldflags}" '
            f'TMPDIR="{tmp_dir}" '
            f'./configure --prefix= && '
            f'make -j1 && make install DESTDIR="{self.package_folder}"'
        )

    def package(self):
        for dep_name in ["libmnl", "libnetfilter_log"]:
            dep_dir = os.path.join(self.build_folder, "deps", dep_name)
            lib_dir = os.path.join(dep_dir, "lib")
            if os.path.isdir(lib_dir):
                copy(self, "*.so*", lib_dir, os.path.join(self.package_folder, "lib"))
            inc_dir = os.path.join(dep_dir, "include")
            if os.path.isdir(inc_dir):
                copy(self, "*", inc_dir, os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.bindirs = ["sbin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["netfilter_log_libipulog", "netfilter_log", "mnl"]
