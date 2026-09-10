#!/usr/bin/env python3
"""Conan recipe for MPFRCX 0.6.3."""
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


class MpfrcxConan(ConanFile):
    name = "mpfrcx"
    version = "0.6.3"
    description = (
        "Library for the arithmetic of univariate polynomials over arbitrary "
        "precision real (MPFR) or complex (MPC) numbers"
    )
    license = "LGPL-3.0-or-later"
    homepage = "https://gitlab.inria.fr/mpfrcx/mpfrcx"
    url = "https://gforge.inria.fr/projects/mpfrcx/"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("gmp/6.3.0")
        self.requires("mpfr/4.2.2")
        self.requires("mpc/1.3.1")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"mpfrcx supports Linux and OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def _ohos_tool(self, name, llvm_names):
        """Resolve a binutils-style tool for OHOS.

        Looks next to the C compiler first (CI SDK layout uses llvm-*
        prefixed tools), then on PATH. Tries the llvm-prefixed names and
        the plain GNU name, since both the OHOS SDK (llvm-ar, llvm-ranlib)
        and self-hosted OHOS toolchains (ar, ranlib) exist in the wild.
        """
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        c_compiler = compiler_executables.get("c")
        search_dirs = []
        if c_compiler and os.path.isabs(c_compiler):
            search_dirs.append(os.path.dirname(c_compiler))
        for candidate in list(llvm_names) + [name]:
            for directory in search_dirs:
                path = os.path.join(directory, candidate)
                if os.path.isfile(path) and os.access(path, os.X_OK):
                    return path
            found = shutil.which(candidate)
            if found:
                return found
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
        mpc = self._dependency_prefix("mpc")
        tc.configure_args.extend([
            f"--with-gmp={gmp}",
            f"--with-mpfr={mpfr}",
            f"--with-mpc={mpc}",
        ])
        if self.settings.os == "OHOS":
            tc.configure_args.extend([
                f"AR={self._ohos_tool('ar', ['llvm-ar'])}",
                f"LD={self._ohos_tool('ld', ['ld.lld'])}",
                f"RANLIB={self._ohos_tool('ranlib', ['llvm-ranlib'])}",
                f"NM={self._ohos_tool('nm', ['llvm-nm'])}",
                f"OBJDUMP={self._ohos_tool('objdump', ['llvm-objdump'])}",
                f"STRIP={self._ohos_tool('strip', ['llvm-strip'])}",
            ])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        if self.settings.os == "OHOS":
            tmpdir = os.path.join(os.path.expanduser("~"), "tmp", f"mpfrcx-{os.getpid()}")
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
        self.cpp_info.libs = ["mpfrcx"]
        self.cpp_info.requires = ["mpc::mpc", "mpfr::mpfr", "gmp::gmp"]
        self.cpp_info.set_property("cmake_file_name", "mpfrcx")
        self.cpp_info.set_property("cmake_target_name", "mpfrcx::mpfrcx")
        self.cpp_info.set_property("pkg_config_name", "mpfrcx")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
