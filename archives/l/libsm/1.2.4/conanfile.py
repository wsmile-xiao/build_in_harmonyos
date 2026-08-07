#!/usr/bin/env python3
"""Conan recipe for X.Org libSM 1.2.4."""

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
)
from conan.tools.gnu import (
    Autotools,
    AutotoolsDeps,
    AutotoolsToolchain,
    PkgConfigDeps,
)
from conan.tools.layout import basic_layout


class LibsmConan(ConanFile):
    name = "libsm"
    version = "1.2.4"
    description = "X.Org Session Management protocol library"
    license = "MIT"
    homepage = "https://gitlab.freedesktop.org/xorg/lib/libsm"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libice/1.1.2", transitive_headers=True)
        self.requires("xorgproto/2025.1", transitive_headers=True)
        self.requires("xtrans/1.6.0", visible=False)

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libsm supports Linux and OHOS, not {self.settings.os}"
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

    def build(self):
        environment = self._build_environment()
        with environment.vars(self).apply():
            if str(self.settings.os) == "OHOS":
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
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = ["SM"]
        self.cpp_info.requires = ["libice::libice", "xorgproto::xorgproto"]
        self.cpp_info.set_property("cmake_file_name", "libsm")
        self.cpp_info.set_property("cmake_target_name", "libsm::libsm")
        self.cpp_info.set_property("pkg_config_name", "sm")
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
            lib_paths = []
            for dep in self.dependencies.values():
                for libdir in dep.cpp_info.aggregated_components().libdirs:
                    lib_paths.append(str(libdir))
            for lib_path in lib_paths:
                environment.append_path("LD_LIBRARY_PATH", lib_path)
        return environment

    def _autotools_toolchain(self):
        toolchain = AutotoolsToolchain(self)
        toolchain.configure_args.extend(
            [
                "--disable-docs",
                "--without-xmlto",
                "--without-fop",
                "--without-xsltproc",
                "--without-libuuid",
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
        pc_path = Path(self.package_folder, "lib", "pkgconfig", "sm.pc")
        if not pc_path.is_file():
            raise ConanException("installed sm.pc is missing")
        pc_content = pc_path.read_text(encoding="utf-8")
        pc_content, count = re.subn(
            r"^prefix=.*$",
            "prefix=${pcfiledir}/../..",
            pc_content,
            count=1,
            flags=re.MULTILINE,
        )
        if count != 1:
            raise ConanException("sm.pc has no unique prefix field")
        pc_path.write_text(pc_content, encoding="utf-8")

        la_path = Path(self.package_folder, "lib", "libSM.la")
        if la_path.is_file():
            la_path.unlink()
