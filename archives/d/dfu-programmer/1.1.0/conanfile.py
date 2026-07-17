#!/usr/bin/env python3
"""Conan recipe - dfu-programmer 1.1.0."""
import os
import shlex
import shutil
import subprocess

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

    def export_sources(self):
        res_src = os.path.join(self.recipe_folder, "res")
        if os.path.isdir(res_src):
            res_dst = os.path.join(self.export_folder, "res")
            if os.path.exists(res_dst):
                shutil.rmtree(res_dst)
            shutil.copytree(res_src, res_dst)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        get(
            self,
            **self.conan_data["libusb_header"],
            destination=os.path.join(self.source_folder, "_libusb_header"),
            strip_root=True,
        )
        self._copy_exported_res()

    def generate(self):
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()
        libusb_prefix = self._libusb_prefix()
        libusb_header = os.path.join(self.source_folder, "_libusb_header", "libusb")
        include_flags = (
            f"-I{libusb_header} "
            f"-I{libusb_prefix}/include/libusb-1.0 "
            f"-I{libusb_prefix}/include "
            f"-I{self._sys_prefix}/include"
        )
        ld_flags = f"-L{libusb_prefix}/lib -L{self._sys_prefix}/lib"
        static_libusb = os.path.join(libusb_prefix, "lib", "libusb-1.0.a")
        lib_flags = "-l:libusb-1.0.a" if os.path.isfile(static_libusb) else "-lusb-1.0"
        pkgconfig_dir = self._write_libusb_pc(libusb_prefix)

        tc = AutotoolsToolchain(self)
        tc.extra_cflags.extend(include_flags.split())
        tc.extra_ldflags.extend([f"-L{libusb_prefix}/lib", f"-L{self._sys_prefix}/lib"])
        tc.configure_args.extend([
            "--build=aarch64-unknown-linux-gnu",
            "--host=aarch64-unknown-linux-gnu",
            f"PKG_CONFIG_PATH={pkgconfig_dir}:{libusb_prefix}/lib/pkgconfig:{self._sys_prefix}/lib/pkgconfig",
            f"CPPFLAGS={include_flags}",
            f"LDFLAGS={ld_flags}",
            f"LIBUSB_CFLAGS={include_flags}",
            f"LIBUSB_LIBS={lib_flags}",
            f"ac_cv_search_libusb_init={lib_flags}",
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

    def _copy_exported_res(self):
        export_dir = os.path.join(os.path.dirname(self.source_folder), "e")
        res_src = os.path.join(export_dir, "res")
        if os.path.isdir(res_src):
            res_dst = os.path.join(self.source_folder, "res")
            if os.path.exists(res_dst):
                shutil.rmtree(res_dst)
            shutil.copytree(res_src, res_dst)

    def _compiler_path(self):
        compilers = self.conf.get("tools.build:compiler_executables", default={}) or {}
        return compilers.get("c") or "cc"

    def _replace_in_existing(self, relpath, replacements):
        path = os.path.join(self.source_folder, relpath)
        if not os.path.isfile(path):
            return
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            content = handle.read()
        updated = content
        for old, new in replacements:
            updated = updated.replace(old, new)
        if updated != content:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(updated)

    def _refresh_config_helpers(self):
        helper_dir = os.path.join(self._sys_prefix, "share", "automake-1.17")
        for relpath in ("config.guess", "config.sub", "m4/config.guess", "m4/config.sub"):
            src = os.path.join(helper_dir, os.path.basename(relpath))
            dst = os.path.join(self.source_folder, relpath)
            if os.path.isfile(src) and os.path.isfile(dst):
                shutil.copy2(src, dst)
                os.chmod(dst, 0o755)

    def _prepare_autotools_helpers(self):
        self._refresh_config_helpers()
        for relpath in (
            "configure",
            "config.guess",
            "config.sub",
            "m4/config.guess",
            "m4/config.sub",
            "build-aux/config.guess",
            "build-aux/config.sub",
        ):
            self._replace_in_existing(relpath, [("umask 077", "umask 022")])

        for relpath in ("config.sub", "m4/config.sub", "build-aux/config.sub"):
            self._replace_in_existing(relpath, [
                ("| linux-gnu* | linux-android*", "| linux-gnu* | linux-android* | linux-ohos*"),
                ("| linux-musl* | linux-gnu*", "| linux-musl* | linux-gnu* | linux-ohos*"),
                ("| linux-android* | linux-dietlibc", "| linux-android* | linux-ohos* | linux-dietlibc"),
                ("| android* | linux-dietlibc", "| android* | ohos* | linux-dietlibc"),
            ])

    def _prepare_libusb_include(self):
        replacements = [("<libusb-1.0/libusb.h>", "<libusb.h>")]
        self._replace_in_existing("src/dfu-device.h", replacements)
        self._replace_in_existing("src/libdfu.c", replacements)

    def _stage_bash_completion_helper(self):
        helper = "update-bash-completion.sh"
        src = os.path.join(self.source_folder, helper)
        dst = os.path.join(self.build_folder, helper)
        os.makedirs(self.build_folder, exist_ok=True)
        if os.path.isfile(src):
            staged_src = dst + ".upstream"
            shutil.copy2(src, staged_src)
            os.chmod(staged_src, 0o755)
            bash = "/data/service/hnp/bin/bash"
            if not os.path.exists(bash):
                bash = shutil.which("bash") or "sh"
            with open(dst, "w", encoding="utf-8") as handle:
                handle.write("#!/bin/sh\n")
                handle.write(f"exec {shlex.quote(bash)} {shlex.quote(staged_src)} \"$@\"\n")
        else:
            with open(dst, "w", encoding="utf-8") as handle:
                handle.write("#!/bin/sh\nexit 0\n")
        os.chmod(dst, 0o755)

    def build(self):
        configure = os.path.join(self.source_folder, "configure")
        bootstrap = os.path.join(self.source_folder, "bootstrap.sh")
        if not os.path.exists(configure) and os.path.exists(bootstrap):
            self.run(f"sh {shlex.quote(bootstrap)}", env="conanbuild", cwd=self.source_folder)
        self._prepare_autotools_helpers()
        self._prepare_libusb_include()

        autotools = Autotools(self)
        autotools.configure()
        self._stage_bash_completion_helper()
        autotools.make(args=["-j1"])

    def package(self):
        Autotools(self).install()
        binary = os.path.join(self.package_folder, "bin", "dfu-programmer")
        if os.path.exists(binary):
            self._sign_binary(binary)

    def _sign_binary(self, path):
        os.chmod(path, 0o755)
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if str(self.settings.os) != "OHOS" or not (os.path.exists(sign_tool) and os.path.exists(objcopy)):
            return
        tmp_signed = path + ".signed"
        subprocess.run(
            [objcopy, "--remove-section", ".codesign", path],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        subprocess.run(
            [sign_tool, "sign", "-inFile", path, "-outFile", tmp_signed, "-selfSign", "1"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        os.replace(tmp_signed, path)
        os.chmod(path, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
