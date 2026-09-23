#!/usr/bin/env python3
"""Conan recipe for the cloop user-space utilities on OHOS."""

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class CloopConan(ConanFile):
    name = "cloop"
    version = "3.14.1.3-nmu1"
    description = "Compressed loopback filesystem utilities"
    license = "GPL-2.0-only"
    homepage = "https://github.com/KlausKnopper/cloop"
    url = "https://github.com/Code7R/cloop"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        source = self.conan_data["sources"]
        get(
            self,
            source["url"],
            sha256=source["sha256"],
            filename="cloop-source.tar.gz",
            strip_root=True,
        )

    def build(self):
        apply_conandata_patches(self)
        compiler_executables = self.conf.get("tools.build:compiler_executables", {}, check_type=dict)
        cc = compiler_executables.get("c", "clang")
        cxx = compiler_executables.get("cpp", "clang++")
        cflags = "-Wall -O2 -fno-strict-aliasing -fno-common"
        zlib_info = self.dependencies["zlib"].cpp_info
        zlib_include = zlib_info.includedirs[0]
        zlib_lib = zlib_info.libdirs[0]
        zlib_flags = f"-I{zlib_include} -L{zlib_lib}"
        source = self.source_folder
        advancecomp = f"{source}/advancecomp-1.15"
        self.run(
            f"cd {advancecomp} && ./configure "
            "--build=aarch64-unknown-linux-gnu "
            "--host=aarch64-unknown-linux-gnu",
            env=[
                f"CC={cc}",
                f"CXX={cxx}",
                f"CFLAGS={cflags}",
                f"CXXFLAGS={cflags}",
                f"CPPFLAGS={zlib_flags}",
                f"LDFLAGS=-L{zlib_lib}",
            ],
        )
        self.run(
            f"make -C {advancecomp} advfs -j1",
            env=[
                f"CC={cc}",
                f"CXX={cxx}",
                f"CFLAGS={cflags}",
                f"CXXFLAGS={cflags}",
                f"CPPFLAGS={zlib_flags}",
                f"LDFLAGS=-L{zlib_lib}",
            ],
        )
        self.run(
            f"{cc} {cflags} {zlib_flags} "
            f"{source}/extract_compressed_fs.c -o {source}/extract_compressed_fs -lz"
        )

    def package(self):
        import os
        import shutil

        bin_dir = self.package_folder + "/bin"
        copy(self, "advfs", self.source_folder + "/advancecomp-1.15", bin_dir, keep_path=False)
        shutil.copyfile(bin_dir + "/advfs", bin_dir + "/create_compressed_fs")
        copy(self, "extract_compressed_fs", self.source_folder, bin_dir, keep_path=False)
        for executable in ("advfs", "create_compressed_fs", "extract_compressed_fs"):
            os.chmod(bin_dir + "/" + executable, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", self.package_folder + "/bin")
