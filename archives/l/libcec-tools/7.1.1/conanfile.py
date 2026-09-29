from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.gnu import PkgConfigDeps
import os
import shutil
import subprocess

from conan.tools.files import (apply_conandata_patches, export_conandata_patches,
                               get)


class LibCecToolsConan(ConanFile):
    name = "libcec-tools"
    version = "7.1.1"
    description = "Pulse-Eight CEC library and command-line tools"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/Pulse-Eight/libcec"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("p8-platform/2.1.0")
        self.requires("eudev/3.2.14")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        PkgConfigDeps(self).generate()

        tc = CMakeToolchain(self)
        # libcec's POSIX implementation and its runtime loader expect Linux
        # SONAME conventions; the OHOS compiler/sysroot still target HarmonyOS.
        tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.cache_variables["HAVE_LIBUDEV"] = True
        tc.cache_variables["HAVE_RANDR"] = False
        tc.cache_variables["CMAKE_DISABLE_FIND_PACKAGE_Python3"] = True
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # libcec 7.1.1 lacks the later DISABLE_BUILDINFO option. Its upstream
        # SetBuildInfo.cmake honors SOURCE_DATE_EPOCH and skips whoami/hostname.
        os.environ["SOURCE_DATE_EPOCH"] = "0"
        # Keep installed shared objects readable to the HarmonyOS runtime loader.
        os.umask(0o022)
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"])

    def package(self):
        cmake = CMake(self)
        cmake.install()
        if str(self.settings.os) == "OHOS":
            for folder in ("bin", "lib"):
                directory = os.path.join(self.package_folder, folder)
                for name in os.listdir(directory):
                    path = os.path.join(directory, name)
                    if os.path.islink(path) or not os.path.isfile(path):
                        continue
                    with open(path, "rb") as elf:
                        if elf.read(4) == b"\x7fELF":
                            self._sign_ohos_elf(path)

    def _ohos_tool(self, name):
        path = shutil.which(name)
        if path:
            return path
        compiler = self.conf.get("tools.build:compiler_executables", default={},
                                 check_type=dict).get("cpp")
        if compiler:
            sdk_root = os.path.dirname(os.path.dirname(os.path.dirname(
                os.path.dirname(compiler))))
            candidate = os.path.join(sdk_root, "toolchains", "lib", name)
            if os.path.isfile(candidate):
                return candidate
        raise ConanException(f"Required OHOS tool is missing: {name}")

    def _sign_ohos_elf(self, path):
        readelf = self._ohos_tool("llvm-readelf")
        objcopy = self._ohos_tool("llvm-objcopy")
        signer = self._ohos_tool("binary-sign-tool")
        sections = subprocess.run([readelf, "-SW", path], check=True,
                                  capture_output=True, text=True).stdout
        if sections.count(".codesign") > 1:
            raise ConanException(f"ELF has multiple .codesign sections: {path}")
        clean = path + ".codesign-clean"
        signed = path + ".ohos-signed"
        for generated in (clean, signed):
            if os.path.exists(generated):
                os.remove(generated)
        try:
            subprocess.run([objcopy, "--remove-section", ".codesign", path, clean],
                           check=True)
            subprocess.run([signer, "sign", "-inFile", clean, "-outFile", signed,
                            "-selfSign", "1"], check=True, timeout=60)
            signed_sections = subprocess.run([readelf, "-SW", signed], check=True,
                                             capture_output=True, text=True).stdout
            if signed_sections.count(".codesign") != 1:
                raise ConanException(f"Signed ELF has invalid .codesign section: {path}")
            os.chmod(signed, (os.stat(path).st_mode & 0o777) | 0o055)
            os.replace(signed, path)
        finally:
            for generated in (clean, signed):
                if os.path.exists(generated):
                    os.remove(generated)

    def package_info(self):
        self.cpp_info.libs = ["cec"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "libcec")
        self.cpp_info.set_property("cmake_target_name", "libcec::libcec")
        self.cpp_info.requires = ["p8-platform::p8-platform", "eudev::eudev"]
