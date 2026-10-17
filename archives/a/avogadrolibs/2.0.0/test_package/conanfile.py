#!/usr/bin/env python3
"""Conan test_package for avogadrolibs 2.0.0."""
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout


class AvogadroLibsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _llvm_runtime_library_dir(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        compiler = (executables.get("cpp") or executables.get("c") or
                    os.getenv("CXX") or os.getenv("CC"))
        if not compiler:
            raise ConanException("Cannot derive LLVM runtime directory: no configured clang")
        resource_dir = subprocess.check_output(
            [os.path.abspath(str(compiler)), "-print-resource-dir"], text=True
        ).strip()
        if not resource_dir:
            raise ConanException("clang -print-resource-dir returned an empty path")
        runtime_dir = os.path.abspath(os.path.join(resource_dir, os.pardir, os.pardir))
        if not os.path.isdir(runtime_dir) or not os.path.isfile(
                os.path.join(runtime_dir, "libxml2.so.16")):
            raise ConanException(
                "Derived LLVM runtime directory is invalid or lacks libxml2.so.16: "
                f"{runtime_dir}"
            )
        self.output.info(f"clang resource directory: {resource_dir}")
        self.output.info(f"LLVM runtime loader directory: {runtime_dir}")
        return runtime_dir

    def _with_llvm_runtime_loader_path(self):
        runtime_dir = self._llvm_runtime_library_dir()
        old_path = os.environ.get("LD_LIBRARY_PATH")
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
            [runtime_dir] + ([old_path] if old_path else [])
        )
        return old_path

    @staticmethod
    def _restore_llvm_runtime_loader_path(old_path):
        if old_path is None:
            os.environ.pop("LD_LIBRARY_PATH", None)
        else:
            os.environ["LD_LIBRARY_PATH"] = old_path

    def build(self):
        old_path = self._with_llvm_runtime_loader_path()
        try:
            cmake = CMake(self)
            cmake.configure()
            cmake.build()
        finally:
            self._restore_llvm_runtime_loader_path(old_path)

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: skip target runtime test")
            return
        old_path = self._with_llvm_runtime_loader_path()
        try:
            self.run(os.path.join(self.cpp.build.bindirs[0], "test_avogadrolibs"), env="conanrun")
        finally:
            self._restore_llvm_runtime_loader_path(old_path)
