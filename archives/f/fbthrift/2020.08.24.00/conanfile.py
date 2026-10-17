#!/usr/bin/env python3
"""Conan recipe for fbthrift 2020.08.24.00 on HarmonyOS PC.

Facebook Thrift compiler (thrift1). Only the thrift compiler is built
(compiler_only=ON); the full runtime library requires folly, wangle, etc.

cmake 4.1.2 removed the FindBoost module; patches use find_package(Boost
CONFIG REQUIRED) which works with Conan's CMakeDeps-generated config files.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class FbthriftConan(ConanFile):
    name = "fbthrift"
    version = "2020.08.24.00"
    description = "Facebook Thrift compiler — high-performance cross-language RPC framework (thrift1 CLI tool)"
    license = "Apache-2.0"
    homepage = "https://github.com/facebook/fbthrift"
    url = ""

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"fbthrift supports Linux and OHOS, got {self.settings.os}"
            )

    def requirements(self):
        # boost 1.87.0 is not available in the registry; 1.84.0 provides
        # libboost_filesystem.a and headers needed by the thrift compiler.
        self.requires("boost/1.84.0")
        self.requires("openssl/1.1.1w")

    def build_requirements(self):
        self.tool_requires("flex/2.6.4")
        self.tool_requires("bison/3.8.2")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        CMakeDeps(self).generate()

        # bison (conan tool_requires) is built with --prefix= so its
        # compiled-in pkgdatadir is /share/bison; CMake's BISON_TARGET
        # invocations need BISON_PKGDATADIR pointed at the real data dir.
        bison = self.dependencies.build["bison"]
        env = Environment()
        env.define(
            "BISON_PKGDATADIR",
            os.path.join(bison.package_folder, "share", "bison"),
        )
        env.vars(self, "build").save_script("fbthrift_bison_env")

        tc = CMakeToolchain(self)
        tc.variables["compiler_only"] = "ON"
        tc.variables["BUILD_TESTS"] = "OFF"
        # 2020-era project declares cmake_minimum_required < 3.5; CMake 4.x
        # dropped that compatibility (E187) — force the policy floor.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"

        # OpenSSL: explicit paths for fbthrift's CMakeLists.txt which uses
        # ${OPENSSL_INCLUDE_DIR} in include_directories. CMakeDeps generates
        # OpenSSLConfig.cmake, but the variable name may not match the
        # uppercase form the source expects.
        openssl = self.dependencies["openssl"]
        tc.cache_variables["OPENSSL_INCLUDE_DIR"] = os.path.join(
            openssl.package_folder, "include"
        )
        tc.cache_variables["OPENSSL_ROOT_DIR"] = openssl.package_folder

        # Pass all dependency package folders via CMAKE_PREFIX_PATH so
        # find_package(BISON)/find_package(FLEX) can locate the tools.
        prefix_paths = []
        for dep_name in ("boost", "openssl"):
            dep = self.dependencies[dep_name]
            prefix_paths.append(dep.package_folder)
        # Tool requires (flex, bison) — add their package folders too
        for dep_name in ("flex", "bison"):
            if dep_name in self.dependencies.build:
                prefix_paths.append(
                    self.dependencies.build[dep_name].package_folder
                )
        tc.cache_variables["CMAKE_PREFIX_PATH"] = ";".join(prefix_paths)

        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
