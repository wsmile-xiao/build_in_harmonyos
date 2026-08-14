#!/usr/bin/env python3
"""Conan recipe for ncmdump 1.5.1 on HarmonyOS.

ncmdump is a NetEase Cloud Music .ncm file decryption CLI tool
(https://github.com/taurusxin/ncmdump).

OHOS-specific adaptations:
  - The upstream CMakeLists.txt calls find_package(TagLib REQUIRED) and
    links "TagLib::tag", while the taglib Conan package exposes the target
    "taglib::taglib"; the target name is remapped in generate() via
    CMakeDeps so no upstream patch is needed.
  - The resulting ELF binary is signed for HarmonyOS execution.
"""
import os
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import get


class NcmdumpConan(ConanFile):
    name = "ncmdump"
    version = "1.5.1"
    package_type = "application"
    description = "NetEase Cloud Music .ncm file decryption tool"
    license = "MIT"
    homepage = "https://github.com/taurusxin/ncmdump"

    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires("taglib/2.3")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        # Upstream links "TagLib::tag"; remap the taglib package so that
        # find_package(TagLib) + TagLib::tag resolve to the Conan package.
        deps.set_property("taglib", "cmake_file_name", "TagLib")
        deps.set_property("taglib", "cmake_target_name", "TagLib::tag")
        deps.generate()
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_FIND_PACKAGE_PREFER_CONFIG"] = True
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        CMake(self).install()
        self._sign_elf(os.path.join(self.package_folder, "bin", "ncmdump"))

    def _sign_elf(self, path):
        # ELF signing is mandatory to execute on HarmonyOS. The signing
        # tools only exist on the real CI/release worker; when absent
        # (local build) skip gracefully and let the worker sign.
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if not (os.path.isfile(sign_tool) and os.path.isfile(objcopy)):
            self.output.warning(
                "ELF signing tools not found; skipping (CI/release worker will sign)."
            )
            return
        try:
            r = subprocess.run(
                [objcopy, "--remove-section", ".codesign", path],
                capture_output=True, timeout=10,
            )
            if r.returncode != 0:
                self.output.warning(
                    f"ELF signature cleanup failed for {os.path.basename(path)} "
                    f"(rc={r.returncode}); keeping original binary"
                )
                return
        except (subprocess.TimeoutExpired, OSError) as exc:
            self.output.warning(
                f"ELF signature cleanup failed for {os.path.basename(path)}; "
                f"keeping original binary: {exc}"
            )
            return
        tmp = path + ".signed.tmp"
        try:
            r = subprocess.run(
                [sign_tool, "sign", "-inFile", path, "-outFile", tmp, "-selfSign", "1"],
                capture_output=True, text=True, timeout=30,
            )
            if r.returncode == 0 and os.path.exists(tmp):
                os.replace(tmp, path)
                os.chmod(path, 0o755)
                return
            details = "\n".join(
                o.strip() for o in (r.stdout, r.stderr) if o and o.strip()
            ) or "no output"
            self.output.warning(
                f"ELF signing failed for {os.path.basename(path)} "
                f"(rc={r.returncode}); keeping unsigned binary:\n{details}"
            )
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout.decode(errors="replace") if isinstance(exc.stdout, bytes) else exc.stdout or ""
            stderr = exc.stderr.decode(errors="replace") if isinstance(exc.stderr, bytes) else exc.stderr or ""
            details = "\n".join(
                o.strip() for o in (stdout, stderr) if o and o.strip()
            ) or "no output"
            self.output.warning(
                f"ELF signing timed out for {os.path.basename(path)}; "
                f"keeping unsigned binary:\n{details}"
            )
        except OSError as exc:
            self.output.warning(
                f"ELF signing could not start for {os.path.basename(path)}; "
                f"keeping unsigned binary: {exc}"
            )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
