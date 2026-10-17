#!/usr/bin/env python3
"""Conan recipe for bamutil — Custom Makefile build system.

bamutil uses a custom Makefile system and requires libStatGen dependency.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy, save
from conan.tools.layout import basic_layout
import os


class BamutilConan(ConanFile):
    name = "bamutil"
    version = "1.0.15"
    description = "Utilities for working on SAM/BAM files"
    license = "GPL-3.0"
    homepage = "https://github.com/statgen/bamUtil"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        # Download bamutil source
        from conan.tools.files import download, unzip
        import tarfile
        url = self.conan_data["sources"]["url"]
        sha256 = self.conan_data["sources"]["sha256"]
        download(self, url, "bamutil.tar.gz", sha256=sha256)
        with tarfile.open("bamutil.tar.gz", "r:gz") as tar:
            # Strip root directory
            members = tar.getmembers()
            root = members[0].name.split('/')[0]
            for member in members:
                member.name = '/'.join(member.name.split('/')[1:])
                if member.name:
                    tar.extract(member, self.source_folder)
        
        # Download libStatGen dependency
        download(self, "https://github.com/statgen/libStatGen/archive/refs/tags/v1.0.15.tar.gz",
                 "libStatGen.tar.gz", sha256="075dcd891409c48d76c0c66186c0cc479bc3cd50bba093e7f318e1d1d19961ff")
        with tarfile.open("libStatGen.tar.gz", "r:gz") as tar:
            members = tar.getmembers()
            root = members[0].name.split('/')[0]
            libstat_dir = os.path.join(self.source_folder, "libStatGen")
            for member in members:
                member.name = '/'.join(member.name.split('/')[1:])
                if member.name:
                    tar.extract(member, libstat_dir)

    def generate(self):
        # Patch Makefile.toolchain to use clang++
        toolchain_path = os.path.join(self.source_folder, "libStatGen", "Makefiles", "Makefile.toolchain")
        content = open(toolchain_path).read()
        content = content.replace("CXX=clang", "CXX=clang++")
        save(self, toolchain_path, content)

    def build(self):
        apply_conandata_patches(self)
        # Build with TARGET=clang
        self.run(f"make TARGET=clang LIB_PATH_GENERAL=libStatGen -j{os.cpu_count() or 1}", cwd=self.source_folder)
        # Run each upstream test independently; this avoids state leakage from the
        # legacy Makefile's single shell command while preserving all 19 tests.
        test_dir = os.path.join(self.source_folder, "test")
        self.run("mkdir -p results && ln -sfn ../libStatGen/bam/test/testFiles testFilesLibBam", cwd=test_dir)
        upstream_tests = [
            "samTests.sh", "testFilter.sh", "testSeq.sh", "testRevert.sh",
            "testDiff.sh", "splitChromosome.sh", "writeRegion.sh", "testSqueeze.sh",
            "testCigars.sh", "testStats.sh", "testClipOverlap.sh", "testSplitBam.sh",
            "testTrimBam.sh", "testPolishBam.sh", "testMergeBam.sh", "testGapInfo.sh",
            "testBam2FastQ.sh", "testDedup.sh", "testRecab.sh",
        ]
        for test_name in upstream_tests:
            self.run(f"bash {test_name}", cwd=test_dir)

    def package(self):
        copy(self, "bin/bam", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "copyrights/*", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"), keep_path=True)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
