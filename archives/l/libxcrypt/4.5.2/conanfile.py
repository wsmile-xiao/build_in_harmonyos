#!/usr/bin/env python3
"""Conan recipe - libxcrypt 4.5.2 (Autotools)."""
import os
import shlex
import shutil

from conan import ConanFile
from conan.tools.build import load_toolchain_args
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rm,
    save,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibxcryptConan(ConanFile):
    name = "libxcrypt"
    version = "4.5.2"
    description = "Extended password hashing library for modern Unix systems"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/besser82/libxcrypt"
    url = "https://github.com/besser82/libxcrypt"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Keep upstream -Werror coverage and demote only Clang's GNU asm warning.
        tc.extra_cflags.append("-Wno-error=language-extension-token")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        self._configure_with_shell()

        autotools = Autotools(self)
        shell = self._config_shell()
        autotools.make(args=["-j1", f"SHELL={shell}"])

        launcher = os.path.join(self.build_folder, "ohos-test-launcher.sh")
        save(
            self,
            launcher,
            f"#!{shell}\n"
            "set -u\n"
            "test \"$#\" -ge 1 || exit 125\n"
            "candidate=\"${1%/*}/.libs/${1##*/}\"\n"
            "if test -f \"$candidate\"; then\n"
            f"    exec {shlex.quote(shell)} \"$@\"\n"
            "fi\n"
            "exec \"$@\"\n",
        )
        log_compiler = f'{shell} {shlex.quote(launcher)}'
        autotools.make(
            target="check",
            args=[
                "-j1",
                f"SHELL={shell}",
                f'LOG_COMPILER="{log_compiler}"',
            ],
        )

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["-j1", f"SHELL={self._config_shell()}"])
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        copy(
            self,
            "COPYING.LIB",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        copy(
            self,
            "LICENSING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["crypt"]
        self.cpp_info.set_property("cmake_file_name", "libxcrypt")
        self.cpp_info.set_property("cmake_target_name", "libxcrypt::crypt")
        self.cpp_info.set_property("pkg_config_name", "libxcrypt")

    def _config_shell(self):
        if self.settings.os == "OHOS":
            return "/system/bin/sh"
        return os.environ.get("CONFIG_SHELL") or shutil.which("sh") or "/bin/sh"

    def _configure_with_shell(self):
        toolchain = load_toolchain_args(self.generators_folder)
        configure_args = toolchain.get("configure_args", "")
        shell = self._config_shell()
        configure = os.path.join(self.source_folder, "configure")
        command = " ".join(
            part
            for part in (
                f"CONFIG_SHELL={shlex.quote(shell)}",
                f"SHELL={shlex.quote(shell)}",
                shlex.quote(shell),
                shlex.quote(configure),
                configure_args,
            )
            if part
        )
        self.run(command, cwd=self.build_folder, env="conanbuild")
