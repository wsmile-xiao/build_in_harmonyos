#!/usr/bin/env python3
"""Conan recipe for the official XaoS 4.3.4 CMake/Qt desktop application."""

import os
import shutil
import stat
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class XaosConan(ConanFile):
    name = "xaos"
    version = "4.3.4"
    description = "Interactive Qt desktop fractal zoomer and renderer"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/xaos-project/XaoS"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Qt Widgets/PrintSupport come from qtbase; Qt6LinguistTools and lrelease
        # are needed by upstream CMake to compile the translation catalogs.
        # qttools/6.11.1.1 still pins qtbase/6.11.1. Harmonize the graph
        # with the PrintSupport-enabled HarmonyOS Qt build used by this app.
        self.requires("qtbase/6.11.1.3", override=True)
        self.requires("qttools/6.11.1.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()

        qtbase = self.dependencies["qtbase"].package_folder
        qttools = self.dependencies["qttools"].package_folder

        toolchain = CMakeToolchain(self)
        toolchain.cache_variables["CMAKE_FIND_PACKAGE_PREFER_CONFIG"] = "ON"
        toolchain.cache_variables["CMAKE_PREFIX_PATH"] = ";".join(
            (qtbase, qttools)
        )
        # Qt6Config searches its additional module prefixes for Widgets,
        # PrintSupport and LinguistTools when the modules are Conan packages.
        toolchain.cache_variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = ";".join(
            (qtbase, qttools)
        )
        toolchain.cache_variables["Qt6_DIR"] = os.path.join(
            qtbase, "lib", "cmake", "Qt6"
        )
        toolchain.cache_variables["Qt6LinguistTools_DIR"] = os.path.join(
            qttools, "lib", "cmake", "Qt6LinguistTools"
        )
        toolchain.cache_variables["DEEPZOOM"] = "OFF"
        toolchain.cache_variables["OPENGL"] = "OFF"
        if str(self.settings.os) == "OHOS":
            toolchain.cache_variables["XAOS_SIGNED_LRELEASE"] = os.path.join(
                self.build_folder, "host-tools", "lrelease"
            )
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        if str(self.settings.os) == "OHOS":
            signed_lrelease = self._prepare_signed_lrelease()

        cmake = CMake(self)

        # lrelease is a Qt executable and needs Qt shared libraries while CMake
        # builds the generated translations. Include transitive Qt libraries
        # such as QtQml, which qttools' lrelease also loads at runtime.
        env = Environment()
        for package in self.dependencies.host.values():
            libdir = os.path.join(package.package_folder, "lib")
            if os.path.isdir(libdir):
                env.append_path("LD_LIBRARY_PATH", libdir)
        env.prepend_path(
            "PATH", os.path.join(self.dependencies["qttools"].package_folder, "bin")
        )
        with env.vars(self).apply():
            if str(self.settings.os) == "OHOS":
                subprocess.run([signed_lrelease, "-version"], check=True, timeout=30)
            cmake.configure()
            cmake.build()

    def _prepare_signed_lrelease(self):
        """Create a private, runnable lrelease copy without changing Conan cache."""
        source = os.path.join(
            self.dependencies["qttools"].package_folder, "bin", "lrelease"
        )
        tool_dir = os.path.join(self.build_folder, "host-tools")
        os.makedirs(tool_dir, exist_ok=True)
        unsigned = os.path.join(tool_dir, "lrelease.unsigned")
        signed = os.path.join(tool_dir, "lrelease.signed")
        destination = os.path.join(tool_dir, "lrelease")

        objcopy = (
            shutil.which("llvm-objcopy")
            or "/data/service/hnp/bin/llvm-objcopy"
        )
        signer = (
            shutil.which("binary-sign-tool")
            or "/data/service/hnp/bin/binary-sign-tool"
        )
        if not os.path.isfile(source):
            raise ConanInvalidConfiguration("QtTools lrelease is missing: %s" % source)
        if not os.path.isfile(objcopy) or not os.path.isfile(signer):
            raise ConanInvalidConfiguration(
                "HarmonyOS lrelease repair requires llvm-objcopy and binary-sign-tool"
            )

        shutil.copy2(source, unsigned)
        try:
            stripped = subprocess.run(
                [objcopy, "--remove-section", ".codesign", unsigned],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if stripped.returncode != 0:
                raise ConanException(
                    "Could not remove the stale lrelease .codesign section: %s"
                    % (stripped.stderr.strip() or stripped.stdout.strip())
                )

            result = subprocess.run(
                [
                    signer,
                    "sign",
                    "-inFile",
                    unsigned,
                    "-outFile",
                    signed,
                    "-selfSign",
                    "1",
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0 or not os.path.isfile(signed):
                raise ConanException(
                    "Could not self-sign the build-local lrelease copy: %s"
                    % (result.stderr.strip() or result.stdout.strip())
                )

            shutil.copymode(source, signed)
            os.chmod(
                signed,
                stat.S_IMODE(os.stat(signed).st_mode)
                | stat.S_IXUSR
                | stat.S_IXGRP
                | stat.S_IXOTH,
            )
            os.replace(signed, destination)
        finally:
            for path in (unsigned, signed):
                if os.path.exists(path):
                    os.unlink(path)

        self.output.info("Prepared build-local signed Qt lrelease: %s" % destination)
        return destination

    def package(self):
        cmake = CMake(self)
        cmake.install()
        if str(self.settings.os) == "OHOS":
            self._resign_installed_executable(
                os.path.join(self.package_folder, "bin", "XaoS")
            )
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def _resign_installed_executable(self, path):
        """Re-sign the installed ELF after CMake has finalized its RPATH."""
        if not os.path.isfile(path):
            raise ConanException("Installed XaoS executable is missing: %s" % path)

        objcopy = (
            shutil.which("llvm-objcopy")
            or "/data/service/hnp/bin/llvm-objcopy"
        )
        signer = (
            shutil.which("binary-sign-tool")
            or "/data/service/hnp/bin/binary-sign-tool"
        )
        if not os.path.isfile(objcopy) or not os.path.isfile(signer):
            raise ConanInvalidConfiguration(
                "HarmonyOS XaoS packaging requires llvm-objcopy and binary-sign-tool"
            )

        signed = path + ".signed"
        mode = stat.S_IMODE(os.stat(path).st_mode)
        try:
            stripped = subprocess.run(
                [objcopy, "--remove-section", ".codesign", path],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if stripped.returncode != 0:
                raise ConanException(
                    "Could not remove the stale XaoS .codesign section: %s"
                    % (stripped.stderr.strip() or stripped.stdout.strip())
                )

            result = subprocess.run(
                [
                    signer,
                    "sign",
                    "-inFile",
                    path,
                    "-outFile",
                    signed,
                    "-selfSign",
                    "1",
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0 or not os.path.isfile(signed):
                raise ConanException(
                    "Could not self-sign the installed XaoS executable: %s"
                    % (result.stderr.strip() or result.stdout.strip())
                )

            os.chmod(signed, mode | stat.S_IXUSR)
            os.replace(signed, path)
        finally:
            if os.path.exists(signed):
                os.unlink(signed)

        self.output.info("Re-signed installed HarmonyOS executable: %s" % path)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
