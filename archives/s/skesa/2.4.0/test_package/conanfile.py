#!/usr/bin/env python3
"""Conan test_package — SKESA 2.4.0.

Compiles and runs a C++ consumer test that drives the packaged `skesa`
executable end-to-end (real de novo assembly of a synthetic read set), then
executes the built test binary on the OHOS build host:
- LD_LIBRARY_PATH points at the SDK libc++_shared.so directory (located via
  `clang++ -print-file-name=libc++_shared.so`, no hardcoded SDK version);
- OHOS executables are signed (llvm-objcopy --remove-section .codesign +
  binary-sign-tool self-sign), same as the boost 1.84 component packages.
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class SkesaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"skesa test_package supports Linux and OHOS, not {self.settings.os}"
            )

    def _compilers(self):
        return self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.warning("Cross-built consumer cannot run on the build host.")
            return

        suffix = ".exe" if str(self.settings.os) == "Windows" else ""
        executable = os.path.join(
            self.cpp.build.bindirs[0], "test_skesa" + suffix
        )
        skesa_bin = os.path.join(
            self.dependencies["skesa"].cpp_info.bindirs[0], "skesa" + suffix
        )
        if self.settings.os == "OHOS":
            self._sign_executable(executable)
            libcxx_dir = self._find_libcxx_dir()
            # The packaged `skesa` runs as a subprocess; it dynamically links
            # the SDK libc++_shared.so and Conan zlib (libz.so).  Put both the
            # SDK libc++ directory and the dependency libdirs on LD_LIBRARY_PATH.
            lib_paths = []
            for dep in self.dependencies.values():
                for lib in dep.cpp_info.libdirs:
                    p = lib if os.path.isabs(lib) else os.path.join(
                        dep.package_folder or "", lib
                    )
                    if p not in lib_paths:
                        lib_paths.append(p)
            if libcxx_dir and libcxx_dir not in lib_paths:
                lib_paths.insert(0, libcxx_dir)
            ld_path = ":".join(lib_paths)
            command = (
                'LD_LIBRARY_PATH="{}:${{LD_LIBRARY_PATH:-}}" "{}" "{}"'.format(
                    ld_path, executable, skesa_bin
                )
            )
            self.run(command, cwd=self.build_folder)
            return

        self.run(f'"{executable}" "{skesa_bin}"', cwd=self.build_folder)

    def _find_libcxx_dir(self):
        """Locate the SDK libc++_shared.so directory via compiler introspection."""
        cxx = self._compilers().get("cpp", "clang++")
        try:
            out = subprocess.check_output(
                [cxx, "-print-file-name=libc++_shared.so"], text=True
            ).strip()
        except Exception as exc:  # noqa: BLE001
            raise ConanInvalidConfiguration(
                "failed to locate libc++_shared.so via {}: {}".format(cxx, exc)
            )
        if not out or out == "libc++_shared.so":
            raise ConanInvalidConfiguration(
                "clang could not locate libc++_shared.so"
            )
        return os.path.dirname(out)

    def _find_ohos_tool(self, name):
        compilers = self._compilers()
        compiler_dir = os.path.dirname(compilers.get("cpp", ""))
        candidates = [
            os.path.join(compiler_dir, name) if compiler_dir else "",
            os.path.join("/data/service/hnp/bin", name),
            shutil.which(name) or "",
        ]
        return next((path for path in candidates if os.path.isfile(path)), "")

    def _sign_executable(self, executable):
        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            raise ConanInvalidConfiguration(
                "OHOS consumer execution requires llvm-objcopy and binary-sign-tool"
            )
        self._sign_elf_atomically(executable, objcopy, signer)

    def _sign_elf_atomically(self, path, objcopy, signer):
        original_mode = os.stat(path).st_mode
        temporary = f"{path}.signing"
        try:
            shutil.copy2(path, temporary)
            # binary-sign-tool is an OHOS system tool linked against the system
            # libc++ (std::__h namespace).  If the build env LD_LIBRARY_PATH
            # (SDK llvm/lib libc++_shared.so, std::__1) reaches it, it dies with
            # "Error relocating ... _ZNSt3__h ... symbol not found" and exit 127.
            # Unset LD_LIBRARY_PATH for both signing steps (consistent with the
            # recipe build(), see knowledge
            # DRAFT-binary-sign-tool-buildenv-ldlibrarypath).
            self.run(f'env -u LD_LIBRARY_PATH "{objcopy}" --remove-section .codesign "{temporary}"')
            self.run(
                f'env -u LD_LIBRARY_PATH "{signer}" sign -inFile "{temporary}" '
                f'-outFile "{temporary}" -selfSign 1'
            )
            os.chmod(temporary, original_mode)
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.remove(temporary)
