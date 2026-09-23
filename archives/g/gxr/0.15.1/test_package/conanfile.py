#!/usr/bin/env python3
"""CMake consumer test for gxr 0.15.1."""

import os
import shutil
import subprocess
import tempfile

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake
from conan.tools.env import Environment, VirtualRunEnv
from conan.tools.layout import basic_layout


class GxrTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info(
                "Cross-built consumer compile/link passed; runtime behavior "
                "is covered by the matching native integration suite"
            )
            return
        executable = self.cpp.build.bindir.replace("\\", "/")
        executable = f"{executable}/gxr_test"
        with VirtualRunEnv(self).vars().apply():
            if str(self.settings.os) == "OHOS":
                runtime = Environment()
                runtime_dir = self._prepare_ohos_runtime()
                if runtime_dir:
                    runtime.prepend_path("LD_LIBRARY_PATH", runtime_dir)
                with runtime.vars(self).apply():
                    self.run(f'"{executable}"')
            else:
                self.run(f'"{executable}"')

    def _prepare_ohos_runtime(self):
        """Copy and re-sign JSON-GLib without modifying Conan's cache."""
        dependency = self.dependencies["json-glib"]
        shared = dependency.options.get_safe("shared")
        if shared is not None and not bool(shared):
            return None
        packaged = os.path.join(
            dependency.package_folder, "lib", "libjson-glib-1.0.so.0"
        )
        if not os.path.lexists(packaged):
            raise RuntimeError(f"JSON-GLib runtime library missing: {packaged}")

        source = os.path.realpath(packaged)
        package_root = os.path.realpath(dependency.package_folder)
        if (
            not os.path.isfile(source)
            or os.path.commonpath((source, package_root)) != package_root
        ):
            raise RuntimeError(f"Unsafe JSON-GLib runtime library: {packaged}")

        runtime_dir = tempfile.mkdtemp(
            prefix="gxr-native-runtime-", dir=self.build_folder
        )
        staged = os.path.join(runtime_dir, "libjson-glib-1.0.so.0")
        if os.path.lexists(staged):
            os.remove(staged)
        shutil.copyfile(source, staged)
        os.chmod(staged, 0o755)
        self._resign_ohos_elf(staged)
        return runtime_dir

    def _resign_ohos_elf(self, path):
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = (
            compiler_executables.get("c")
            or compiler_executables.get("cpp")
            or ""
        )
        compiler_dir = os.path.dirname(compiler) if os.sep in compiler else ""
        objcopy_candidates = (
            os.path.join(compiler_dir, "llvm-objcopy") if compiler_dir else "",
            "/data/service/hnp/bin/llvm-objcopy",
            shutil.which("llvm-objcopy") or "",
        )
        objcopy = next(
            (item for item in objcopy_candidates if os.path.isfile(item)), None
        )
        objcopy_dir = os.path.dirname(os.path.realpath(objcopy)) if objcopy else ""
        readelf_candidates = (
            os.path.join(compiler_dir, "llvm-readelf") if compiler_dir else "",
            os.path.join(objcopy_dir, "llvm-readelf") if objcopy_dir else "",
            "/data/service/hnp/bin/llvm-readelf",
            shutil.which("llvm-readelf") or "",
            shutil.which("readelf") or "",
        )
        readelf = next(
            (item for item in readelf_candidates if os.path.isfile(item)), None
        )
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not objcopy or not readelf or not os.path.isfile(signer):
            raise RuntimeError("OHOS ELF signing tools are required")

        temporary = path + ".unsigned"
        if os.path.lexists(temporary):
            raise RuntimeError(f"Stale ELF signing output beside: {path}")
        try:
            shutil.copyfile(path, temporary)
            stripped = subprocess.run(
                [objcopy, "--remove-section", ".codesign", temporary],
                capture_output=True,
                timeout=60,
                check=False,
            )
            if stripped.returncode != 0:
                raise RuntimeError(f"Failed to strip old ELF signature: {path}")
            result = subprocess.run(
                [
                    signer,
                    "sign",
                    "-inFile",
                    temporary,
                    "-outFile",
                    temporary,
                    "-selfSign",
                    "1",
                ],
                capture_output=True,
                timeout=60,
                check=False,
            )
            if result.returncode != 0 or not os.path.isfile(temporary):
                raise RuntimeError(f"Failed to self-sign OHOS ELF: {path}")
            sections = subprocess.run(
                [readelf, "-SW", temporary],
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
            if sections.returncode != 0 or sections.stdout.count(".codesign") != 1:
                raise RuntimeError(f"Invalid signed OHOS ELF: {path}")
            os.chmod(temporary, 0o755)
            os.replace(temporary, path)
        finally:
            if os.path.lexists(temporary):
                os.remove(temporary)
