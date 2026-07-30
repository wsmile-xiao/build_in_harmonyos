#!/usr/bin/env python3
"""Conan recipe for the standalone mt32emu 2.7.1 core library."""

import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
    rmdir,
    save,
)


class Mt32emuConan(ConanFile):
    name = "mt32emu"
    version = "2.7.1"
    description = "Munt MT-32 family synthesizer emulation library"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/munt/munt"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            platform_modules = os.path.join(self.build_folder, "_cmake_modules")
            save(
                self,
                os.path.join(platform_modules, "Platform", "HarmonyOS.cmake"),
                "include(Platform/Linux)\n",
            )
            tc.variables["CMAKE_MODULE_PATH"] = platform_modules

        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["libmt32emu_SHARED"] = bool(self.options.shared)
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = self.options.get_safe(
            "fPIC", True
        )
        tc.variables["libmt32emu_WITH_INTERNAL_RESAMPLER"] = True
        tc.variables["libmt32emu_C_INTERFACE"] = True
        tc.variables["libmt32emu_CPP_INTERFACE"] = True
        tc.variables["BUILD_SNAPSHOTS"] = False
        tc.generate()

    def build(self):
        build_source = os.path.join(self.build_folder, "_source")
        rmdir(self, build_source)
        copy(
            self,
            "*",
            src=os.path.join(self.source_folder, "mt32emu"),
            dst=build_source,
        )

        if self.settings.os == "OHOS" and self.options.shared:
            # HMDFS cannot reliably materialize CMake's VERSION/SOVERSION
            # symlink chain. Conan already versions the package, so use one
            # real libmt32emu.so with an unversioned SONAME on OHOS only.
            replace_in_file(
                self,
                os.path.join(build_source, "CMakeLists.txt"),
                "set_target_properties(mt32emu\n"
                "  PROPERTIES VERSION ${libmt32emu_VERSION}\n"
                "  SOVERSION ${libmt32emu_VERSION_MAJOR}\n"
                ")\n",
                "",
            )

        cmake = CMake(self)
        cmake.configure(
            build_script_folder=build_source,
            variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"},
        )
        cmake.build()

    def package(self):
        CMake(self).install()
        if self.settings.os == "OHOS" and self.options.shared:
            self._sign_elf_for_ohos(
                os.path.join(self.package_folder, "lib", "libmt32emu.so")
            )
        copy(
            self,
            "COPYING.LESSER.txt",
            src=os.path.join(self.source_folder, "mt32emu"),
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def _sign_elf_for_ohos(self, path):
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(path):
            raise ConanInvalidConfiguration(
                f"installed shared library is missing: {path}"
            )
        if not os.path.isfile(objcopy) or not os.path.isfile(signer):
            raise ConanInvalidConfiguration(
                "HarmonyOS ELF signing tools are required for target execution"
            )

        clean_path = f"{path}.codesign-clean"
        signed_path = f"{path}.signed"
        for temporary in (clean_path, signed_path):
            if os.path.exists(temporary):
                os.remove(temporary)
        try:
            self.run(
                f"{shlex.quote(objcopy)} --remove-section .codesign "
                f"{shlex.quote(path)} {shlex.quote(clean_path)}"
            )
            self.run(
                f"{shlex.quote(signer)} sign -inFile {shlex.quote(clean_path)} "
                f"-outFile {shlex.quote(signed_path)} -selfSign 1"
            )
            os.replace(signed_path, path)
            os.chmod(path, 0o755)
        finally:
            for temporary in (clean_path, signed_path):
                if os.path.exists(temporary):
                    os.remove(temporary)

    def package_info(self):
        self.cpp_info.libs = ["mt32emu"]
        self.cpp_info.set_property("cmake_file_name", "MT32Emu")
        self.cpp_info.set_property("cmake_target_name", "MT32Emu::mt32emu")
        self.cpp_info.set_property("pkg_config_name", "mt32emu")
