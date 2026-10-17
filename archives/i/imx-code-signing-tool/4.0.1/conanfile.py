#!/usr/bin/env python3
"""Conan recipe for imx-code-signing-tool (NXP Code Signing Tool, CST) 4.0.1."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class ImxCodeSigningToolConan(ConanFile):
    name = "imx-code-signing-tool"
    version = "4.0.1"
    description = "NXP Code Signing Tool (CST) for HABv4 and AHAB secure boot image signing on i.MX SoCs"
    license = "BSD-3-Clause"
    homepage = "https://www.nxp.com/webapp/sps/download/license.jsp?colCode=IMX_CST_TOOL_NEW"
    # 官方托管例外（PF7 显式跳过）：上游官方归档 cst-4.0.1.tgz 仅能经 NXP
    # license 同意页取得（直连 404，无匿名下载端点）。本源声明使用 Debian
    # 官方 orig 重打包件（内容与官方包文件级等价，见 conandata.yml 注释）。
    url = "https://www.nxp.com/webapp/sps/download/license.jsp?colCode=IMX_CST_TOOL_NEW"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # CST 4.0.1 requires OpenSSL >= 3.0.0 (find_package(OpenSSL 3.0.0 REQUIRED)).
        self.requires("openssl/3.5.6")
        # tools/ahab_signed_message links libjson-c.a via find_cst_dependency_library().
        self.requires("json-c/0.18")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Upstream CMakeLists relies on find_package(OpenSSL) / OpenSSL::Crypto;
        # the conan-provided recipe only declares openssl::openssl, so remap the
        # components BEFORE CMakeDeps generates the config files (same wiring as
        # the i2pd recipe on this platform).
        openssl = self.dependencies["openssl"].cpp_info
        openssl.set_property("cmake_file_name", "OpenSSL")
        openssl.set_property("cmake_additional_variables_prefixes", ["OPENSSL"])
        package_folder = self.dependencies["openssl"].package_folder
        include_dirs = [os.path.join(package_folder, path) for path in openssl.includedirs]
        lib_dirs = [os.path.join(package_folder, path) for path in openssl.libdirs]
        system_libs = list(openssl.system_libs)
        openssl.libs = []
        openssl.system_libs = []

        crypto = openssl.components["Crypto"]
        crypto.libs = ["crypto"]
        crypto.system_libs = system_libs
        crypto.includedirs = include_dirs
        crypto.libdirs = lib_dirs
        crypto.bindirs = []
        crypto.resdirs = []
        crypto.frameworkdirs = []
        crypto.builddirs = []
        crypto.set_property("cmake_target_name", "OpenSSL::Crypto")

        ssl = openssl.components["SSL"]
        ssl.libs = ["ssl"]
        ssl.includedirs = include_dirs
        ssl.libdirs = lib_dirs
        ssl.bindirs = []
        ssl.resdirs = []
        ssl.frameworkdirs = []
        ssl.builddirs = []
        ssl.requires = ["Crypto"]
        ssl.set_property("cmake_target_name", "OpenSSL::SSL")

        deps = CMakeDeps(self)
        deps.generate()

        tc = CMakeToolchain(self)
        # find_cst_dependency_library() in ahab_signed_message/CMakeLists.txt
        # derives the include dir from json_c_DIR (<dir>/include), so point it
        # at the json-c package root (headers live at <root>/include/json-c/).
        tc.variables["json_c_DIR"] = self.dependencies["json-c"].package_folder
        # OSTYPE detection in upstream CMakeLists only knows Linux/Windows; on
        # OHOS CMAKE_SYSTEM_NAME is not "Linux", so pin the linux64 layout.
        tc.variables["OSTYPE"] = "linux64"
        # Keep optional back-ends disabled: PKCS#11 needs libp11, PQC needs
        # liboqs/oqsprovider; neither is part of the base tool.
        tc.variables["CST_WITH_PKCS11"] = "OFF"
        tc.variables["CST_WITH_PQC"] = "OFF"
        # hab_log_parser / ahab_signature_block_parser / hab_srktool_scripts
        # default to OFF upstream; keep defaults for the published tool set.
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # The orig tarball keeps the CMake project under src/.
        cmake.configure(build_script_folder="src")
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

        # The orig tarball keeps the project under src/; licenses live
        # alongside at the unpacked root.
        copy(self, "COPYING*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "src/licenses/*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "licenses/*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
