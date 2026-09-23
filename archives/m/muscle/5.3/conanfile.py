#!/usr/bin/env python3
"""Conan recipe — MUSCLE 5.3 (vcxproj_make.py build system).

MUSCLE uses a non-standard build system: a Python script (vcxproj_make.py)
parses the Visual Studio .vcxproj file to extract the source file list,
generates a Makefile, and runs make. The script is downloaded from the
upstream vcxproj_make repository at build time.

Upstream CI (aarch64) uses g++; OHOS uses clang++ via --cppcompiler flag.
"""
import os
import subprocess

from conan import ConanFile
from conan.tools.files import get, download, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout

# vcxproj_make.py is a build tool (not a conan dependency), downloaded at build time
VCXPROJ_MAKE_URL = "https://raw.githubusercontent.com/rcedgar/vcxproj_make/806d016/vcxproj_make.py"


class MuscleConan(ConanFile):
    name = "muscle"
    version = "5.3"
    description = "MUSCLE: Multiple Sequence Comparison by Log-Expectation"
    license = "GPL-3.0"
    homepage = "https://github.com/rcedgar/muscle"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass  # No toolchain needed; vcxproj_make.py manages compiler flags

    def build(self):
        apply_conandata_patches(self)
        src_dir = os.path.join(self.source_folder, "src")

        # 1. Download vcxproj_make.py (build tool, not a conan dependency)
        vcxproj_make_path = os.path.join(src_dir, "vcxproj_make.py")
        download(self, VCXPROJ_MAKE_URL, vcxproj_make_path)

        # 2. Initialize git repo in src/ — vcxproj_make.py calls
        #    `git log` to generate gitver.txt (build version stamp).
        #    The tarball is not a git repo, so we init one.
        try:
            subprocess.run(["git", "init"], cwd=src_dir, check=True,
                           capture_output=True, timeout=30)
            subprocess.run(["git", "add", "-A"], cwd=src_dir, check=True,
                           capture_output=True, timeout=60)
            subprocess.run(["git", "commit", "-m", "init"],
                           cwd=src_dir, check=True,
                           capture_output=True, timeout=60)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            # Fallback: create gitver.txt manually if git is unavailable
            gitver_path = os.path.join(src_dir, "gitver.txt")
            with open(gitver_path, "w") as f:
                f.write("v5.3\n")

        # 3. Run vcxproj_make.py to generate Makefile and compile
        #    Use OHOS clang++ instead of upstream g++
        #    The conan profile sets tools.build:compiler_executables which
        #    puts clang++ in PATH, so vcxproj_make.py can find it.
        self.run(
            "python3 vcxproj_make.py --cppcompiler clang++ --ccompiler clang --openmp",
            cwd=src_dir,
        )

    def package(self):
        # Binary is at <source>/bin/muscle (vcxproj_make outputs to ../bin/
        # relative to src/)
        copy(self, "muscle", src=os.path.join(self.source_folder, "bin"),
             dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
