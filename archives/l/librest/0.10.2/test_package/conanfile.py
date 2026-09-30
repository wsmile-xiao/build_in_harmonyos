#!/usr/bin/env python3
"""Conan consumer test for librest 0.10.2."""

import filecmp
import os
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class LibrestTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv", "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._stage_runtime_closure()

    def _runtime_libdirs(self):
        """Return the tested package and its host runtime closure in order."""
        host_dependencies = getattr(self.dependencies, "host", self.dependencies)
        dependencies = list(host_dependencies.values())
        tested = self.dependencies.get("librest")
        if tested is not None:
            dependencies = [tested] + [dep for dep in dependencies if dep is not tested]

        result = []
        seen = set()
        for dependency in dependencies:
            package_folder = getattr(dependency, "package_folder", None)
            if not package_folder:
                continue
            cpp_info = dependency.cpp_info
            try:
                cpp_info = cpp_info.aggregated_components()
            except (AttributeError, TypeError):
                pass
            for libdir in cpp_info.libdirs or ["lib"]:
                path = libdir if os.path.isabs(libdir) else os.path.join(package_folder, libdir)
                path = os.path.abspath(path)
                key = os.path.normcase(path)
                if os.path.isdir(path) and key not in seen:
                    seen.add(key)
                    result.append(path)
        return result

    def _stage_runtime_closure(self):
        """Materialize every dependency SONAME in one loader-first directory."""
        stage = os.path.join(self.build_folder, "runtime-libs")
        if os.path.isdir(stage):
            shutil.rmtree(stage)
        os.makedirs(stage)
        copied = 0
        for libdir in self._runtime_libdirs():
            for filename in sorted(os.listdir(libdir)):
                if not (filename.endswith(".so") or ".so." in filename):
                    continue
                source = os.path.join(libdir, filename)
                resolved = os.path.realpath(source)
                try:
                    inside = os.path.commonpath([os.path.abspath(libdir), resolved]) == os.path.abspath(libdir)
                except ValueError:
                    inside = False
                if not inside or not os.path.isfile(resolved):
                    raise RuntimeError(f"invalid runtime shared-library alias: {source}")
                destination = os.path.join(stage, filename)
                if os.path.exists(destination):
                    if not os.path.isfile(destination) or not filecmp.cmp(
                        resolved, destination, shallow=False
                    ):
                        raise RuntimeError(f"conflicting runtime SONAME: {filename}")
                    continue
                shutil.copy2(resolved, destination)
                copied += 1
        required = ("libjson-glib-1.0.so.0", "libintl.so.8")
        missing = [name for name in required if not os.path.isfile(os.path.join(stage, name))]
        if copied == 0 or missing:
            raise RuntimeError(
                "test_package runtime stage is incomplete: " + ", ".join(missing)
            )
        self.output.info(f"test_package runtime stage: {stage} ({copied} files)")
        return stage

    def _sign_runtime_roots(self, stage):
        """Self-sign copied critical roots at their final native OHOS path."""
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        readelf = "/data/service/hnp/bin/llvm-readelf"
        for tool in (objcopy, sign_tool, readelf):
            if not os.path.isfile(tool):
                raise RuntimeError(f"native OHOS runtime signing tool is missing: {tool}")
        for filename in ("libintl.so.8", "libjson-glib-1.0.so.0"):
            path = os.path.join(stage, filename)
            cleanup = subprocess.run(
                [objcopy, "--remove-section", ".codesign", path],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if cleanup.returncode != 0:
                raise RuntimeError(
                    f"failed to remove stale codesign from {path}: "
                    f"{(cleanup.stdout + cleanup.stderr).strip()}"
                )
            signed = path + ".signed.tmp"
            last_error = ""
            for _attempt in range(3):
                if os.path.exists(signed):
                    os.unlink(signed)
                result = subprocess.run(
                    [sign_tool, "sign", "-inFile", path, "-outFile", signed,
                     "-selfSign", "1"],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                if result.returncode == 0 and os.path.isfile(signed):
                    os.replace(signed, path)
                    os.chmod(path, 0o755)
                    break
                last_error = (result.stdout + result.stderr).strip()
            else:
                raise RuntimeError(f"failed to self-sign {path}: {last_error}")
            verify = subprocess.run(
                [readelf, "-S", path], capture_output=True, text=True, timeout=30
            )
            if verify.returncode != 0 or ".codesign" not in verify.stdout:
                raise RuntimeError(f"self-signed runtime root lacks .codesign: {path}")
            self.output.info(f"Self-signed test_package runtime root: {path}")

    def test(self):
        if can_run(self):
            executable = os.path.join(self.build_folder, "test_librest")
            runtime_stage = os.path.join(self.build_folder, "runtime-libs")
            if not os.path.isdir(runtime_stage):
                raise RuntimeError("test_package runtime stage is missing")
            self._sign_runtime_roots(runtime_stage)
            ld_library_path = os.pathsep.join(
                [runtime_stage] + self._runtime_libdirs()
            )
            self.output.info("test_package LD_LIBRARY_PATH: " + ld_library_path)
            shell = os.environ.get("CONFIG_SHELL") or shutil.which("bash")
            if not shell:
                raise RuntimeError("bash is required to bind the OHOS runtime closure")
            script = (
                f"export LD_LIBRARY_PATH={shlex.quote(ld_library_path)}"
                "${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}; "
                f"exec {shlex.quote(executable)}"
            )
            self.run(
                f"{shlex.quote(shell)} -c {shlex.quote(script)}",
                env="conanrun",
            )
