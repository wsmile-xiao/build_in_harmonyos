#!/usr/bin/env python3
"""Conan recipe for fastp 1.3.3 — a FASTQ preprocessor.

fastp uses a Makefile-based build system with dependencies:
  - isa-l (Intel ISA-L for gzip decompression, from cmd-pkgs)
  - libdeflate (compression, from ohpcd remote)
  - highway (SIMD, replaced with scalar fallback for OHOS)
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches, chdir, download
from conan.tools.layout import basic_layout


class FastpConan(ConanFile):
    name = "fastp"
    version = "1.3.3"
    description = "An ultra-fast all-in-one FASTQ preprocessor (QC/adapters/trimming/filtering/splitting/merging...)"
    license = "MIT"
    homepage = "https://github.com/OpenGene/fastp"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libdeflate/1.25")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # Download isa-l from cmd-pkgs (pre-built OHOS package)
        # The pre-installed isa-l at /storage/Users/currentUser/usr/local has
        # restrictive permissions (660) that block CI builds running as other users.
        isal_url = "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/isa-l-2.32.0-ohos-aarch64.tar.gz"
        isal_sha256 = "0385c7413fa501c2126f93207f721e88e079e97e3627e8d6c7d5c66fc0c2af0e"
        isal_tarball = os.path.join(self.source_folder, "isa-l-ohos.tar.gz")
        isal_dir = os.path.join(self.source_folder, "_deps", "isa-l")
        os.makedirs(os.path.dirname(isal_dir), exist_ok=True)

        # Verify isa-l tarball integrity — download() supports sha256 and the
        # cmd-pkgs release tarball must be checked so transport corruption or
        # tampering fails the build loudly instead of shipping a suspect binary.
        download(self, isal_url, isal_tarball, sha256=isal_sha256)
        # Extract isa-l tarball (no top-level dir, flat structure: include/ lib/ bin/)
        self.run(f"mkdir -p {isal_dir} && tar xzf {isal_tarball} -C {isal_dir}")
        os.unlink(isal_tarball)

        isal_prefix = isal_dir

        # Get libdeflate include/lib paths from Conan dependency (absolute paths)
        libdeflate_dep = self.dependencies["libdeflate"]
        libdeflate_include = " ".join([os.path.join(libdeflate_dep.package_folder, d)
                                       for d in libdeflate_dep.cpp_info.includedirs])
        libdeflate_lib = " ".join([os.path.join(libdeflate_dep.package_folder, d)
                                   for d in libdeflate_dep.cpp_info.libdirs])

        # Build from source folder (use space separator for Make foreach)
        with chdir(self, self.source_folder):
            # Remove hwy from Makefile's FIND_STATIC loop (not available on OHOS)
            self.run(r"sed -i 's/isal deflate hwy/isal deflate/' Makefile", cwd=self.source_folder)
            self.run(
                f"make CC=clang CXX=clang++ "
                f"INCLUDE_DIRS=\"{isal_prefix}/include {libdeflate_include}\" "
                f"LIBRARY_DIRS=\"{isal_prefix}/lib {libdeflate_lib}\" "
                f"LIBS='-lisal -ldeflate -lpthread' "
                f"-j1",
                env=["PATH=/system/bin:/usr/bin:/bin:/data/service/hnp/bin"])

    def package(self):
        chdir(self, self.source_folder)
        copy(self, "fastp", self.source_folder, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []