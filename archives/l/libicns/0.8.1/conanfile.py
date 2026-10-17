#!/usr/bin/env python3
"""Conan recipe for libicns 0.8.1 (Apple icon format library)."""

import os
import re
import shlex
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rm,
)
from conan.tools.gnu import (
    Autotools,
    AutotoolsDeps,
    AutotoolsToolchain,
    PkgConfigDeps,
)
from conan.tools.layout import basic_layout


class LibicnsConan(ConanFile):
    name = "libicns"
    version = "0.8.1"
    description = "Library for manipulating Apple ICNS icon files"
    license = "LGPL-2.1-or-later"  # library; bundled icnsutils tools are GPL-2.0
    homepage = "https://sourceforge.net/projects/icns/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libpng/1.6.58.2", transitive_headers=True)

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libicns supports Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()
        self._autotools_toolchain().generate()
        # OHOS loader has no default search path for conan-cached shared libs;
        # configure's conftest runs compiled programs and would fail with
        # "Error loading shared library libpng16.so.16" otherwise.
        environment = Environment()
        for dependency in self.dependencies.values():
            for libdir in dependency.cpp_info.libdirs:
                environment.prepend_path("LD_LIBRARY_PATH", libdir)
        environment.vars(self, scope="build").save_script("conanbuild_runpath")

    def build(self):
        environment = self._build_environment()
        with environment.vars(self).apply():
            if str(self.settings.os) == "OHOS":
                self._prepare_ohos_configure()
                self._configure_ohos()
                self._run_ohos("make -j1")
                self._run_ohos("make -j1 check")
            else:
                autotools = Autotools(self)
                autotools.configure()
                autotools.make(args=["-j1"])
                autotools.make(target="check", args=["-j1"])

    def package(self):
        environment = self._build_environment()
        with environment.vars(self).apply():
            if str(self.settings.os) == "OHOS":
                destination = shlex.quote(self.package_folder)
                self._run_ohos(f"make -j1 install DESTDIR={destination}")
            else:
                Autotools(self).install(args=["-j1"])
        self._relocate_metadata()
        self._copy_licenses()

    def package_info(self):
        self.cpp_info.libs = ["icns"]
        self.cpp_info.requires = ["libpng::libpng"]
        self.cpp_info.set_property("cmake_file_name", "libicns")
        self.cpp_info.set_property("cmake_target_name", "libicns::libicns")
        self.cpp_info.set_property("pkg_config_name", "libicns")
        pc_dir = os.path.join(self.package_folder, "lib", "pkgconfig")
        self.buildenv_info.append_path("PKG_CONFIG_PATH", pc_dir)
        self.runenv_info.append_path("PKG_CONFIG_PATH", pc_dir)

    def _build_environment(self):
        temporary = Path(self.build_folder, ".tmp")
        temporary.mkdir(parents=True, exist_ok=True)
        environment = Environment()
        environment.define_path("TMPDIR", str(temporary))
        if str(self.settings.os) == "OHOS":
            environment.define("MKDIR_P", "/system/bin/mkdir -p")
        return environment

    def _autotools_toolchain(self):
        toolchain = AutotoolsToolchain(self)
        toolchain.configure_args.extend(
            [
                "--disable-jasper",
                "--disable-openjpeg",
            ]
        )
        return toolchain

    def _configure_ohos(self):
        shell = "/system/bin/sh"
        if not os.path.isfile(shell):
            raise ConanInvalidConfiguration(f"OHOS configure shell is missing: {shell}")
        configure = self._ohos_configure_path()
        arguments = " ".join(
            shlex.quote(argument)
            for argument in self._autotools_toolchain().configure_args
        )
        self._run_ohos(f'"{shell}" "{configure}" {arguments}')

    def _prepare_ohos_configure(self):
        configure = self._ohos_configure_path()
        content = configure.read_text(encoding="utf-8")
        needle = "umask 077"
        if content.count(needle) != 2:
            raise ConanException("configure umask contract changed")
        configure.write_text(
            content.replace(needle, "umask 022"),
            encoding="utf-8",
            newline="\n",
        )

    def _ohos_configure_path(self):
        configure = Path(self.source_folder, "configure")
        if not configure.is_file():
            raise ConanException(f"configure script is missing: {configure}")
        return configure

    def _run_ohos(self, command):
        shell = "/system/bin/sh"
        prefix = f"export SHELL={shell} CONFIG_SHELL={shell}; "
        self.run(prefix + command, cwd=self.build_folder, env="conanbuild")

    def _relocate_metadata(self):
        pc_path = Path(self.package_folder, "lib", "pkgconfig", "libicns.pc")
        if not pc_path.is_file():
            raise ConanException("installed libicns.pc is missing")
        pc_content = pc_path.read_text(encoding="utf-8")
        pc_content, count = re.subn(
            r"^prefix=.*$",
            "prefix=${pcfiledir}/../..",
            pc_content,
            count=1,
            flags=re.MULTILINE,
        )
        if count != 1:
            raise ConanException("libicns.pc has no unique prefix field")
        pc_path.write_text(pc_content, encoding="utf-8")

        la_path = Path(self.package_folder, "lib", "libicns.la")
        if la_path.is_file():
            la_path.unlink()

    def _copy_licenses(self):
        for name in ("COPYING.LGPL-2.1.txt", "COPYING.GPL-2.0.txt"):
            source = Path(self.source_folder, name)
            if source.is_file():
                copy(
                    self,
                    name,
                    src=self.source_folder,
                    dst=os.path.join(self.package_folder, "licenses"),
                    keep_path=False,
                )
