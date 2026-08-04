#!/usr/bin/env python3
"""Conan recipe for VirtualPG 2.0.1."""

import glob
import os
import shutil
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import load_toolchain_args
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rm,
    save,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class VirtualpgConan(ConanFile):
    name = "virtualpg"
    version = "2.0.1"
    description = "SQLite virtual table extension for accessing PostgreSQL tables"
    license = "MPL-1.1 OR GPL-2.0-or-later OR LGPL-2.1-or-later"
    homepage = "https://www.gaia-gis.it/fossil/virtualpg/index"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"VirtualPG supports Linux and OHOS, not {self.settings.os}"
            )
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires(
            "sqlite3/3.49.1",
            transitive_headers=True,
            transitive_libs=True,
        )
        self.requires(
            "libpq/18.1",
            transitive_headers=True,
            transitive_libs=True,
        )

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(
            self,
            **self.conan_data["sources"],
            filename="virtualpg-2.0.1.tar.gz",
            strip_root=True,
        )

    def generate(self):
        VirtualBuildEnv(self).generate()
        AutotoolsDeps(self).generate()

        tmpdir = os.path.join(self.build_folder, ".tmp")
        os.makedirs(tmpdir, exist_ok=True)
        shell = self._build_shell()
        environment = Environment()
        environment.define_path("TMPDIR", tmpdir)
        environment.define_path("CONFIG_SHELL", shell)
        environment.define_path("SHELL", shell)
        # Upstream replaces LDFLAGS with pg_config's libdir while probing libpq.
        environment.define("LIBS", "")
        if str(self.settings.os) == "OHOS":
            environment.define("MKDIR_P", "/system/bin/mkdir -p")
        environment.vars(self).save_script("virtualpg_build_env")

        tc = AutotoolsToolchain(self)
        tc.configure_args.append(f"--with-pgconfig={self._pg_config_path()}")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        self._build_pg_config_query()

        autotools = Autotools(self)
        configure_args = load_toolchain_args(self.generators_folder).get(
            "configure_args", ""
        )
        configure = os.path.join(self.source_folder, "configure")
        self.run(f'"{self._build_shell()}" "{configure}" {configure_args}')
        autotools.make(args=self._make_args())
        autotools.make(target="check", args=self._make_args())

    def package(self):
        Autotools(self).install(args=self._make_args())
        libdir = os.path.join(self.package_folder, "lib")
        rm(self, "*.la", libdir)
        if not self.options.shared:
            rm(self, "mod_virtualpg.a", libdir)
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        self._make_pkg_config_relocatable()
        self._validate_package_artifacts()

    def package_info(self):
        self.cpp_info.libs = ["virtualpg"]
        self.cpp_info.requires = ["sqlite3::sqlite3", "libpq::libpq"]
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.set_property("cmake_file_name", "virtualpg")
        self.cpp_info.set_property("cmake_target_name", "virtualpg::virtualpg")
        self.cpp_info.set_property("pkg_config_name", "virtualpg")

    def _build_shell(self):
        if str(self.settings.os) == "OHOS":
            return "/system/bin/sh"
        shell = os.environ.get("CONFIG_SHELL") or shutil.which("sh")
        if not shell:
            raise ConanException("no POSIX shell is available to run configure")
        return shell

    def _pg_config_path(self):
        return os.path.join(self.build_folder, "pg_config_conan")

    def _build_pg_config_query(self):
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        compiler = compiler_executables.get("c")
        if not compiler:
            raise ConanException(
                "tools.build:compiler_executables must define the C compiler"
            )

        dependency = self.dependencies["libpq"]
        include_dir = dependency.cpp_info.includedirs[0]
        library_dir = dependency.cpp_info.libdirs[0]
        source = os.path.join(self.build_folder, "pg_config_conan.c")
        program = """#include <stdio.h>
#include <string.h>

int main(int argc, char **argv)
{
    if (argc != 2) {
        return 2;
    }
    if (strcmp(argv[1], "--includedir") == 0) {
        puts("%s");
        return 0;
    }
    if (strcmp(argv[1], "--libdir") == 0) {
        puts("%s");
        return 0;
    }
    if (strcmp(argv[1], "--version") == 0) {
        puts("18.1");
        return 0;
    }
    return 1;
}
""" % (self._c_string(include_dir), self._c_string(library_dir))
        save(self, source, program)
        self.run(
            f'"{compiler}" -std=c11 -O2 "{source}" '
            f'-o "{self._pg_config_path()}"'
        )

    @staticmethod
    def _c_string(value):
        return value.replace("\\", "\\\\").replace('"', '\\"')

    def _make_args(self):
        args = ["-j1"]
        if str(self.settings.os) == "OHOS" and self.options.shared:
            args.extend(
                (
                    'libvirtualpg_la_LDFLAGS="-avoid-version -no-undefined"',
                    "mod_virtualpg_la_LDFLAGS='-module -avoid-version "
                    "-no-undefined $(PG_LDFLAGS) $(PG_LIB)'",
                )
            )
        return args

    def _make_pkg_config_relocatable(self):
        pc_file = Path(self.package_folder, "lib", "pkgconfig", "virtualpg.pc")
        if not pc_file.is_file():
            raise ConanException("upstream install did not produce virtualpg.pc")

        lines = pc_file.read_text(encoding="utf-8").splitlines()
        prefix_lines = [
            index for index, line in enumerate(lines) if line.startswith("prefix=")
        ]
        if len(prefix_lines) != 1:
            raise ConanException(
                "virtualpg.pc must contain exactly one prefix assignment"
            )
        lines[prefix_lines[0]] = "prefix=${pcfiledir}/../.."
        libs_index = next(
            (index for index, line in enumerate(lines) if line.startswith("Libs:")),
            None,
        )
        if libs_index is None:
            raise ConanException("virtualpg.pc does not declare Libs")
        lines.insert(libs_index, "Requires: sqlite3 libpq")
        pc_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _validate_package_artifacts(self):
        include = os.path.join(self.package_folder, "include", "virtualpg.h")
        if not os.path.isfile(include):
            raise ConanException("package is missing include/virtualpg.h")

        libdir = os.path.join(self.package_folder, "lib")
        if glob.glob(os.path.join(libdir, "*.la")):
            raise ConanException("package contains non-relocatable Libtool archives")
        if self.options.shared:
            if glob.glob(os.path.join(libdir, "*.a")):
                raise ConanException("shared package unexpectedly contains archives")
            for stem in ("libvirtualpg", "mod_virtualpg"):
                expected = f"{stem}.so"
                path = os.path.join(libdir, expected)
                if not os.path.isfile(path):
                    raise ConanException(f"package is missing lib/{expected}")
                if str(self.settings.os) == "OHOS":
                    matches = glob.glob(os.path.join(libdir, f"{stem}.so*"))
                    if [os.path.basename(item) for item in matches] != [expected]:
                        raise ConanException(
                            f"OHOS shared package must contain only {expected}: {matches}"
                        )
        else:
            static_library = os.path.join(libdir, "libvirtualpg.a")
            if not os.path.isfile(static_library):
                raise ConanException("static package is missing lib/libvirtualpg.a")
            archives = sorted(
                os.path.basename(path)
                for path in glob.glob(os.path.join(libdir, "*.a"))
            )
            if archives != ["libvirtualpg.a"]:
                raise ConanException(
                    f"static package must contain only libvirtualpg.a: {archives}"
                )
            if glob.glob(os.path.join(libdir, "*.so*")):
                raise ConanException("static package unexpectedly contains shared objects")
