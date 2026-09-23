#!/usr/bin/env python3
"""Conan recipe — netcdf-c 4.9.3 (autotools).

netCDF-C: self-describing scientific data format library.
OHOS adaptation:
  - configure with --host=aarch64-linux-ohos and target flags for clang
  - deps injected through build-folder private prefix via AutotoolsDeps
  - DAP client enabled (libcurl), bundled XML parser used (--disable-libxml2)
  - remote/parallel test suites disabled for the offline worker
"""
import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches, export_conandata_patches, get,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class NetcdfCConan(ConanFile):
    name = "netcdf-c"
    version = "4.9.3"
    description = "C library for reading and writing netCDF self-describing data files"
    license = "BSD-3-Clause"
    homepage = "https://www.unidata.ucar.edu/software/netcdf/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("hdf5/1.14.6")
        self.requires("libcurl/8.5.0")
        self.requires("zlib/1.3.1.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _target(self):
        return (
            "x86_64-linux-ohos"
            if str(self.settings.arch) == "x86_64"
            else "aarch64-linux-ohos"
        )

    def generate(self):
        deps = AutotoolsDeps(self)
        deps.generate()
        tc = AutotoolsToolchain(self)
        if str(self.settings.os) == "OHOS":
            target = self._target()
            tc.configure_args.append(f"--host={target}")
            tc.cflags.extend([f"--target={target}"])
            tc.cxxflags.extend([f"--target={target}"])
            tc.ldflags.extend([f"--target={target}"])
        tc.configure_args.append("--disable-dap-remote-tests")
        tc.configure_args.append("--disable-parallel-tests")
        tc.configure_args.append("--disable-libxml2")
        tc.generate()
        env = Environment()
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                env.prepend_path("LD_LIBRARY_PATH", libdir)
        env.vars(self, scope="build").save_script("conanbuild_runpath")

    def build(self):
        apply_conandata_patches(self)
        # E490: HMDFS 不保留 POSIX 执行位，configure 前恢复 autotools 辅助脚本可执行位
        import stat as _stat
        for _p in ("configure", "config.guess", "config.sub", "install-sh", "missing"):
            _f = os.path.join(self.source_folder, _p)
            if os.path.isfile(_f):
                os.chmod(_f, os.stat(_f).st_mode | _stat.S_IXUSR | _stat.S_IXGRP | _stat.S_IXOTH)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j8"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["netcdf"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "netCDF")
        self.cpp_info.set_property("cmake_target_name", "netCDF::netcdf")
        self.cpp_info.set_property("pkg_config_name", "netcdf")
