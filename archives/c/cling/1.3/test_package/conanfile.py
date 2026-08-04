#!/usr/bin/env python3
"""Exercise the packaged Cling binary with independent C++ consumers."""

import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class ClingTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            return

        package = self.dependencies["cling"].package_folder
        cling = os.path.join(package, "bin", "cling")
        version_output = os.path.join(self.build_folder, "cling-version.txt")
        embedding_output = os.path.join(self.build_folder, "cling-embedding.txt")
        smoke_output = os.path.join(self.build_folder, "cling-smoke.txt")
        smoke_script = os.path.join(self.source_folder, "smoke.sh")
        embedding = os.path.join(self.cpp.build.bindirs[0], "cling_embedding")
        bash = shutil.which("bash")
        if not bash:
            raise RuntimeError("Bash is required by the Cling smoke matrix")

        self.run(f'"{cling}" --version > "{version_output}" 2>&1', env="conanrun")
        with open(version_output, encoding="utf-8", errors="replace") as stream:
            version = stream.read().strip()
        expected_version = str(self.dependencies["cling"].ref.version)
        if version != expected_version:
            raise AssertionError(
                f"cling version mismatch: expected={expected_version!r}, "
                f"actual={version!r}"
            )

        self.run(
            f'"{embedding}" "{cling}" "{package}" > "{embedding_output}" 2>&1',
            env="conanrun",
            cwd=self.build_folder,
        )
        with open(embedding_output, encoding="utf-8", errors="replace") as stream:
            embedding_result = stream.read().strip()
        if embedding_result != "CLING_EMBED_RESULT=42":
            raise AssertionError(
                f"libcling embedding consumer failed: {embedding_result!r}"
            )

        self.run(
            f'"{bash}" "{smoke_script}" "{cling}" > "{smoke_output}" 2>&1',
            env="conanrun",
            cwd=self.build_folder,
        )
        with open(smoke_output, encoding="utf-8", errors="replace") as stream:
            smoke = stream.read()
        if "CLING_MATRIX_RESULT=52/52" not in smoke.splitlines():
            raise AssertionError(
                f"cling did not pass all 52 independent consumers: {smoke!r}"
            )
