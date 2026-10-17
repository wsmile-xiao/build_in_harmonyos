#!/usr/bin/env python3
"""Corrected Conan recipe for librttopo 1.1.0.

This recipe replaces the initial OpenHarmony package for upstream librttopo
1.1.0. The library is static and PIC so that downstream shared libraries such
as libspatialite can link it safely.
"""

import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import load_toolchain_args
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibrttopoConan(ConanFile):
    name = "librttopo"
    version = "1.1.0"
    description = "RT Topology Library"
    license = "GPL-2.0-or-later"
    homepage = "https://gitea.osgeo.org/rttopo/librttopo"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires(
            "geos/3.13.1",
            transitive_headers=True,
            transitive_libs=True,
        )

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    @property
    def _geos_config_path(self):
        return os.path.join(self.build_folder, "geos-config-ohos")

    def generate(self):
        AutotoolsDeps(self).generate()
        toolchain = AutotoolsToolchain(self)
        if self.options.fPIC:
            toolchain.extra_cflags.append("-fPIC")
        toolchain.configure_args.extend(
            [
                "--disable-shared",
                "--enable-static",
                "--with-geosconfig={}".format(self._geos_config_path),
            ]
        )
        toolchain.generate()

    def _write_geos_config(self):
        geos = self.dependencies["geos"].cpp_info
        if not geos.includedirs or not geos.libdirs:
            raise ConanInvalidConfiguration(
                "geos package has no include/lib directories"
            )

        def c_string(value):
            return value.replace("\\", "\\\\").replace('"', '\\"')

        include_dir = c_string(geos.includedirs[0])
        lib_dir = c_string(geos.libdirs[0])
        source = os.path.join(self.build_folder, "geos-config-ohos.c")
        os.makedirs(self.build_folder, exist_ok=True)
        with open(source, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(
                "#include <stdio.h>\n"
                "#include <string.h>\n"
                "int main(int argc, char **argv) {\n"
                "  if (argc != 2) return 2;\n"
                '  if (!strcmp(argv[1], "--includes")) { puts("%s"); return 0; }\n'
                '  if (!strcmp(argv[1], "--ldflags")) { puts("-L%s"); return 0; }\n'
                '  if (!strcmp(argv[1], "--cflags")) { puts("-I%s"); return 0; }\n'
                '  if (!strcmp(argv[1], "--clibs")) { puts("-lgeos_c"); return 0; }\n'
                '  if (!strcmp(argv[1], "--version")) { puts("3.13.1"); return 0; }\n'
                "  return 2;\n"
                "}\n" % (include_dir, lib_dir, include_dir)
            )

        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = executables.get("c", "clang") if executables else "clang"
        self.run(
            '"{}" "{}" -O2 -o "{}"'.format(
                cc, source, self._geos_config_path
            )
        )
        self._sign_elf(self._geos_config_path, required=True)

    def _build_environment(self):
        environment = Environment()
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        environment.define("TMPDIR", tmpdir)
        environment.define("TMPPREFIX", os.path.join(tmpdir, "zsh-tmp-"))
        environment.define("CONFIG_SHELL", "/system/bin/sh")
        environment.define("SHELL", "/system/bin/sh")
        environment.define("MKDIR_P", "/system/bin/mkdir -p")
        environment.prepend_path("PATH", "/data/service/hnp/bin")
        for _ref, dependency in self.dependencies.items():
            for bindir in dependency.cpp_info.bindirs:
                environment.prepend_path("PATH", bindir)
            for libdir in dependency.cpp_info.libdirs:
                environment.prepend_path("LD_LIBRARY_PATH", libdir)
        return environment

    def _configure(self, autotools):
        if str(self.settings.os) != "OHOS":
            autotools.configure()
            return

        shell = "/system/bin/sh"
        configure = os.path.join(self.source_folder, "configure")
        configure_args = load_toolchain_args(self.generators_folder).get(
            "configure_args", ""
        )
        command = shlex.join([shell, configure])
        if configure_args:
            command = "{} {}".format(command, configure_args)
        command = "CONFIG_SHELL={} SHELL={} PWD={} {}".format(
            shell,
            shell,
            shlex.quote(self.build_folder),
            command,
        )
        self.run(command, cwd=self.build_folder)

    def build(self):
        apply_conandata_patches(self)
        environment = self._build_environment()
        old_umask = os.umask(0o022)
        try:
            with environment.vars(self).apply():
                self._write_geos_config()
                autotools = Autotools(self)
                self._configure(autotools)
                autotools.make(args=["-j1"])
                autotools.make(target="check", args=["-j1"])
        finally:
            os.umask(old_umask)

    def package(self):
        environment = self._build_environment()
        old_umask = os.umask(0o022)
        try:
            with environment.vars(self).apply():
                Autotools(self).install(args=["-j1"])
        finally:
            os.umask(old_umask)

        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        self._validate_package_layout()

    def _validate_package_layout(self):
        required = [
            os.path.join(self.package_folder, "lib", "librttopo.a"),
            os.path.join(self.package_folder, "include", "librttopo.h"),
            os.path.join(self.package_folder, "include", "librttopo_geom.h"),
        ]
        missing = [path for path in required if not os.path.isfile(path)]
        if missing:
            raise ConanInvalidConfiguration(
                "missing package artifacts: {}".format(", ".join(missing))
            )

    def _sign_elf(self, path, required=False):
        if str(self.settings.os) != "OHOS":
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(objcopy) or not os.path.isfile(signer):
            if required:
                raise ConanInvalidConfiguration(
                    "OHOS ELF signing tools are required for native tests"
                )
            return
        self.run(
            '"{}" --remove-section .codesign "{}" 2>/dev/null || true'.format(
                objcopy, path
            )
        )
        self.run(
            '"{}" sign -inFile "{}" -outFile "{}" -selfSign 1'.format(
                signer, path, path
            )
        )

    def package_info(self):
        self.cpp_info.libs = ["rttopo"]
        self.cpp_info.requires = ["geos::geos"]
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.set_property("cmake_file_name", "rttopo")
        self.cpp_info.set_property("cmake_target_name", "rttopo::rttopo")
        self.cpp_info.set_property("pkg_config_name", "rttopo")
