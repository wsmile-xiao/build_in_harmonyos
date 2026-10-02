#!/usr/bin/env python3
"""Conan recipe for the header-only Relacy model checker."""

import os
import shlex
import shutil
from pathlib import Path

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.layout import basic_layout


class RelacyConan(ConanFile):
    name = "relacy"
    version = "0.0-git20191025.acc09bb"
    description = "Header-only C++ library for verifying synchronization algorithms under relaxed memory models"
    license = "BSD-3-Clause"
    homepage = "https://github.com/dvyukov/relacy"

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, filename="relacy-acc09bbe65a1837a08912774c7fed178547514e6.tar.gz", **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        compiler_executables = self.conf.get("tools.build:compiler_executables", default={}) or {}
        cxx = compiler_executables.get("cpp", "c++")
        compiler_path = shutil.which(cxx) or cxx
        sdk_shell = Path(compiler_path).expanduser().resolve().parent / "bash"
        shell_candidates = (
            os.environ.get("CONFIG_SHELL"),
            str(sdk_shell),
            shutil.which("bash"),
            "/bin/sh",
        )
        shell = next((candidate for candidate in shell_candidates
                      if candidate and os.path.isfile(candidate)), "/bin/sh")
        command = "make -j1 check CXX={} CXXFLAGS={} SHELL={}".format(
            shlex.quote(cxx),
            shlex.quote("-DRELACY_USE_PTHREAD_FIBERS"),
            shlex.quote(shell),
        )
        self.run(command, cwd=self.source_folder)

    def package(self):
        source_headers = os.path.join(self.source_folder, "relacy")
        include_dir = os.path.join(self.package_folder, "include", "relacy")
        copy(self, "*.h", src=source_headers, dst=include_dir, keep_path=True)
        copy(self, "*.hpp", src=source_headers, dst=include_dir, keep_path=True)
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.defines = ["RELACY_USE_PTHREAD_FIBERS"]
        self.cpp_info.set_property("cmake_file_name", "relacy")
        self.cpp_info.set_property("cmake_target_name", "relacy::relacy")
