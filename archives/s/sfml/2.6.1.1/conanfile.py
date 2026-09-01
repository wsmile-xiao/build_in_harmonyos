#!/usr/bin/env python3
"""Conan recipe for SFML 2.6.1.1 on OpenHarmony PC.

This baseline package enables the System and Network modules. Window,
Graphics, and Audio are intentionally disabled because they need platform
windowing/OpenAL support that is not available in the current OHOS CI image.
"""
import glob
import os
import shlex
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, rmdir, rm


class SfmlConan(ConanFile):
    name = "sfml"
    version = "2.6.1.1"
    description = "Simple and Fast Multimedia Library, packaged for OHOS System and Network modules"
    license = "Zlib"
    homepage = "https://www.sfml-dev.org/"
    url = "https://github.com/SFML/SFML"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        self._set_sfml_options(tc.variables)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        if self._is_ohos():
            self._build_ohos()
            return
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_enabled_upstream_tests()

    def package(self):
        if self._is_ohos():
            bdir = os.path.join(self.build_folder, "build-ohos")
            self.run("cmake --install {} --prefix {}".format(
                shlex.quote(bdir), shlex.quote(self.package_folder)))
            self._prune_disabled_modules()
            if self.options.shared:
                self._sign_shared_libs()
            return
        cmake = CMake(self)
        cmake.install()
        self._prune_disabled_modules()

    def _prune_disabled_modules(self):
        for module in ("Audio", "Graphics", "Window"):
            rmdir(self, os.path.join(self.package_folder, "include", "SFML", module))
            rm(self, f"{module}.hpp", os.path.join(self.package_folder, "include", "SFML"))
        for pc_name in ("sfml-all.pc", "sfml-audio.pc", "sfml-graphics.pc", "sfml-window.pc"):
            rm(self, pc_name, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def _sfml_options(self):
        return {
            "BUILD_SHARED_LIBS": "ON" if self.options.shared else "OFF",
            "SFML_BUILD_AUDIO": "OFF",
            "SFML_BUILD_WINDOW": "OFF",
            "SFML_BUILD_GRAPHICS": "OFF",
            "SFML_BUILD_EXAMPLES": "OFF",
            "SFML_BUILD_DOC": "OFF",
            "SFML_BUILD_TEST_SUITE": "ON",
        }

    def _is_ohos(self):
        return str(self.settings.os) in ("OHOS", "HarmonyOS")

    def _set_sfml_options(self, variables):
        variables.update(self._sfml_options())

    def _ohos_arch(self):
        return {
            "armv8": "arm64-v8a",
            "armv7": "armeabi-v7a",
            "x86_64": "x86_64",
        }.get(str(self.settings.arch), str(self.settings.arch))

    def _build_ohos(self):
        bdir = os.path.join(self.build_folder, "build-ohos")
        defs = [
            "-DCMAKE_TOOLCHAIN_FILE={}".format(shlex.quote(self._ohos_toolchain())),
            "-DOHOS_ARCH={}".format(self._ohos_arch()),
            "-DCMAKE_BUILD_TYPE={}".format(self.settings.build_type),
            "-DCMAKE_INSTALL_PREFIX={}".format(shlex.quote(self.package_folder)),
            "-DCMAKE_INSTALL_LIBDIR=lib",
        ]
        defs.extend("-D{}={}".format(name, value) for name, value in self._sfml_options().items())
        self.run("cmake -B {} -S {} {}".format(
            shlex.quote(bdir), shlex.quote(self.source_folder), " ".join(defs)))
        self.run("cmake --build {}".format(shlex.quote(bdir)))
        self._run_enabled_upstream_tests(bdir)

    def _run_enabled_upstream_tests(self, build_dir=None):
        if not can_run(self):
            self.output.warning("SFML upstream tests were built but not run because target binaries cannot execute on this host")
            return
        test_dir = build_dir or self.build_folder
        self.run(
            "ctest --test-dir {} -R {} --output-on-failure".format(
                shlex.quote(test_dir), shlex.quote("test-sfml-(system|network)")))

    def _ohos_toolchain(self):
        user_toolchains = self.conf.get(
            "tools.cmake.cmaketoolchain:user_toolchain", default=[], check_type=list)
        ndk = os.environ.get("OHOS_NDK_HOME", "")
        candidates = list(user_toolchains)
        if ndk:
            candidates.append(os.path.join(ndk, "build", "cmake", "ohos.toolchain.cmake"))
        candidates.extend(sorted(glob.glob(
            "/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake")))
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        raise ConanInvalidConfiguration(
            "Cannot find ohos.toolchain.cmake; set OHOS_NDK_HOME or "
            "tools.cmake.cmaketoolchain:user_toolchain")

    def _sign_shared_libs(self):
        libdir = os.path.join(self.package_folder, "lib")
        shared_objects = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        shared_objects += glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not shared_objects:
            return
        objcopy = os.environ.get("OHOS_OBJCOPY", "/data/service/hnp/bin/llvm-objcopy")
        signer = os.environ.get("OHOS_SIGN_TOOL", "/data/service/hnp/bin/binary-sign-tool")
        if not os.path.isfile(objcopy):
            raise ConanInvalidConfiguration(f"llvm-objcopy not found: {objcopy}")
        if not os.path.isfile(signer):
            raise ConanInvalidConfiguration(f"binary-sign-tool not found: {signer}")
        for shared_object in shared_objects:
            if os.path.islink(shared_object):
                continue
            self._remove_codesign_section(objcopy, shared_object)
            self.run("{} sign -inFile {} -outFile {} -selfSign 1".format(
                shlex.quote(signer), shlex.quote(shared_object), shlex.quote(shared_object)))

    def _remove_codesign_section(self, objcopy, shared_object):
        if not self._has_codesign_section(objcopy, shared_object):
            return
        result = subprocess.run(
            [objcopy, "--remove-section", ".codesign", shared_object],
            text=True,
            capture_output=True,
            check=False)
        if result.returncode == 0:
            return
        output = (result.stderr or "") + (result.stdout or "")
        raise ConanInvalidConfiguration(
            "Failed to remove .codesign from {}: {}".format(shared_object, output.strip()))

    def _has_codesign_section(self, objcopy, shared_object):
        result = subprocess.run(
            [objcopy, "--dump-section", ".codesign=/dev/null", shared_object],
            text=True,
            capture_output=True,
            check=False)
        if result.returncode == 0:
            return True
        output = ((result.stderr or "") + (result.stdout or "")).lower()
        if "does not exist" in output or "not found" in output or "no such section" in output:
            return False
        raise ConanInvalidConfiguration(
            "Failed to inspect sections for {}: {}".format(shared_object, output.strip()))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "SFML")

        system = self.cpp_info.components["system"]
        system.set_property("cmake_target_name", "SFML::System")
        system.libs = ["sfml-system"]
        if str(self.settings.os) in ("Linux", "OHOS", "HarmonyOS"):
            system.system_libs = ["pthread"]

        network = self.cpp_info.components["network"]
        network.set_property("cmake_target_name", "SFML::Network")
        network.libs = ["sfml-network"]
        network.requires = ["system"]
