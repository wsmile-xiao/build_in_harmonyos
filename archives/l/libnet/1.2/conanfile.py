#!/usr/bin/env python3
"""Conan recipe — libnet 1.2 (Autotools: configure + make).

libnet is a C library for constructing and injecting network packets.

OHOS adaptations:
  0006-include-libnet-libnet-structures.h.patch - Fix __int64_t type for musl libc
  E007 config.guess bypass (inline in generate()) - Pass --build/--host triplet to skip config.guess probe
  E114 umask 077 fix (inline in build())       - Remove umask 077 for HMDFS compatibility
  E232 configure shell fix (inline in build()) - Prefix configure with /system/bin/sh

R26: Static linking by default (system-name library).
R32: settings.os check in ("Linux", "OHOS").
R33: No shell environment variables in build().
R34: test_package calls libnet API.
"""
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, load, save, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


def _fix_config_status(conanfile, path):
    """E114: HMDFS forces setgid on directories; `umask 077 && mktemp -d`
    creates a drwx--S--- temp dir that is not writable even by its owner.
    Remove `umask 077` so config.status can create its temp dir."""
    if not os.path.exists(path):
        return
    content = load(conanfile, path)
    content = content.replace("umask 077 && mktemp", "mktemp")
    content = content.replace("umask 077 && mkdir", "mkdir")
    save(conanfile, path, content)


class LibnetConan(ConanFile):
    name = "libnet"
    version = "1.2"
    description = "Network packet construction library"
    license = "LGPL-2.1"
    homepage = "https://github.com/libnet/libnet"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libnet is only supported on Linux/OHOS, not " + str(self.settings.os)
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.configure_args.append(f"--prefix={self.package_folder}")
        # E007: Old config.guess (2018) doesn't recognize HarmonyOS.
        # Pass GNU triplet to bypass config.guess probe entirely.
        if str(self.settings_build.os) == "OHOS":
            tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
            tc.configure_args.append("--host=aarch64-unknown-linux-gnu")
        tc.generate()

    def build(self):
        autotools = Autotools(self)
        if str(self.settings_build.os) == "OHOS":
            # E232: native OHOS build executor — configure script cannot be
            # executed directly (Permission denied).  Prefix with /system/bin/sh.
            configure = os.path.join(self.source_folder, "configure")
            args = autotools._configure_args
            if isinstance(args, list):
                args_str = " ".join(shlex.quote(a) for a in args)
            else:
                args_str = str(args)
            shell = "/system/bin/sh"
            command = f"CONFIG_SHELL={shell} {shell} {configure} {args_str}"
            # E114: configure generates config.status with umask 077 which
            # fails on HMDFS.  Run configure (may fail at config.status),
            # fix config.status, then re-run it.
            self.run(command, cwd=self.build_folder, ignore_errors=True)
            cs_path = os.path.join(self.build_folder, "config.status")
            mk_path = os.path.join(self.build_folder, "Makefile")
            if os.path.exists(cs_path) and not os.path.exists(mk_path):
                _fix_config_status(self, cs_path)
                self.run(f"{shell} {cs_path}", cwd=self.build_folder)
        else:
            autotools.configure()
        # E074: parallel make hits HMDFS jobserver fifo EPERM
        autotools.make(args=["-j1"])

    def package(self):
        if str(self.settings_build.os) == "OHOS":
            # E232: install-sh can't be executed on HMDFS.
            # Manually copy built artifacts to the package folder.
            prefix = self.package_folder
            bld = self.build_folder
            src = self.source_folder

            # Copy library files (built in build_folder/src/.libs)
            lib_src = os.path.join(bld, "src", ".libs")
            lib_dst = os.path.join(prefix, "lib")
            os.makedirs(lib_dst, exist_ok=True)
            if os.path.isdir(lib_src):
                for f in os.listdir(lib_src):
                    if f.startswith("libnet"):
                        shutil.copy2(os.path.join(lib_src, f),
                                     os.path.join(lib_dst, f))

            # Copy header files (from source folder)
            inc_src = os.path.join(src, "include")
            inc_dst = os.path.join(prefix, "include")
            os.makedirs(inc_dst, exist_ok=True)
            top_h = os.path.join(inc_src, "libnet.h")
            if os.path.isfile(top_h):
                shutil.copy2(top_h, os.path.join(inc_dst, "libnet.h"))
            sub_src = os.path.join(inc_src, "libnet")
            sub_dst = os.path.join(inc_dst, "libnet")
            if os.path.isdir(sub_src):
                os.makedirs(sub_dst, exist_ok=True)
                for f in os.listdir(sub_src):
                    if f.endswith(".h"):
                        shutil.copy2(os.path.join(sub_src, f),
                                     os.path.join(sub_dst, f))

            # Copy libnet-config (generated in build folder)
            for folder in [bld, src]:
                config_src = os.path.join(folder, "libnet-config")
                if os.path.isfile(config_src):
                    bin_dst = os.path.join(prefix, "bin")
                    os.makedirs(bin_dst, exist_ok=True)
                    shutil.copy2(config_src,
                                 os.path.join(bin_dst, "libnet-config"))
                    break

            # Copy pkgconfig file (generated in build folder)
            for folder in [bld, src]:
                pc_src = os.path.join(folder, "libnet.pc")
                if os.path.isfile(pc_src):
                    pc_dst = os.path.join(prefix, "lib", "pkgconfig")
                    os.makedirs(pc_dst, exist_ok=True)
                    shutil.copy2(pc_src, os.path.join(pc_dst, "libnet.pc"))
                    break
        else:
            autotools = Autotools(self)
            autotools.install(args=["-j1"])

    def package_info(self):
        self.cpp_info.libs = ["net"]
