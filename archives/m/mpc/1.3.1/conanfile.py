#!/usr/bin/env python3
"""Conan recipe for GNU MPC 1.3.1."""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rm,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class MpcConan(ConanFile):
    name = "mpc"
    version = "1.3.1"
    description = "GNU Multiple Precision Complex Arithmetic Library"
    license = "LGPL-3.0-or-later"
    homepage = "https://www.multiprecision.org/mpc/"
    url = "https://ftp.gnu.org/gnu/mpc/"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("gmp/6.3.0")
        self.requires("mpfr/4.2.2")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"mpc supports Linux and OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def _ohos_tool(self, name):
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        c_compiler = compiler_executables.get("c")
        if c_compiler and os.path.isabs(c_compiler):
            return os.path.join(os.path.dirname(c_compiler), name)
        return name

    def _dependency_prefix(self, dep_name):
        package_folder = self.dependencies[dep_name].package_folder
        if self.settings.os != "OHOS":
            return package_folder

        staged = os.path.join(self.generators_folder, "ohos-deps", dep_name)
        for subdir in ("include", "lib"):
            src = os.path.join(package_folder, subdir)
            dst = os.path.join(staged, subdir)
            if not os.path.isdir(src):
                continue
            for root, _, filenames in os.walk(src):
                rel = os.path.relpath(root, src)
                target_root = dst if rel == "." else os.path.join(dst, rel)
                os.makedirs(target_root, exist_ok=True)
                for filename in filenames:
                    if filename.endswith(".la"):
                        continue
                    shutil.copy2(
                        os.path.join(root, filename),
                        os.path.join(target_root, filename),
                    )
        return staged

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--with-pic")
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--enable-static", "--disable-shared"])

        gmp = self._dependency_prefix("gmp")
        mpfr = self._dependency_prefix("mpfr")
        tc.configure_args.extend([
            f"--with-gmp-include={os.path.join(gmp, 'include')}",
            f"--with-gmp-lib={os.path.join(gmp, 'lib')}",
            f"--with-mpfr-include={os.path.join(mpfr, 'include')}",
            f"--with-mpfr-lib={os.path.join(mpfr, 'lib')}",
        ])
        if self.settings.os == "OHOS":
            tc.configure_args.extend([
                f"AR={self._ohos_tool('llvm-ar')}",
                f"LD={self._ohos_tool('ld.lld')}",
                f"RANLIB={self._ohos_tool('llvm-ranlib')}",
                f"NM={self._ohos_tool('llvm-nm')}",
                f"OBJDUMP={self._ohos_tool('llvm-objdump')}",
                f"STRIP={self._ohos_tool('llvm-strip')}",
            ])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        if self.settings.os == "OHOS":
            tmpdir = os.path.join(os.path.expanduser("~"), "tmp", f"mpc-{os.getpid()}")
        else:
            tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.chmod(tmpdir, 0o755)
        os.environ["TMPDIR"] = tmpdir

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        autotools.make(target="check", args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        copy(self, "COPYING*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["mpc"]
        self.cpp_info.requires = ["mpfr::mpfr", "gmp::gmp"]
        self.cpp_info.set_property("cmake_file_name", "mpc")
        self.cpp_info.set_property("cmake_target_name", "mpc::mpc")
        self.cpp_info.set_property("pkg_config_name", "mpc")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
