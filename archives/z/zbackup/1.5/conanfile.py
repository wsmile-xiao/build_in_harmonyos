#!/usr/bin/env python3
"""Conan recipe for zbackup 1.5 on HarmonyOS PC."""

import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class ZbackupConan(ConanFile):
    name = "zbackup"
    version = "1.5"
    description = "Globally deduplicating backup tool with encryption and compression"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/davidbartonau/zbackup"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("backup", "deduplication", "encryption", "compression")
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"with_lzo": [True, False]}
    default_options = {"with_lzo": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/3.0.16")
        self.requires("protobuf/3.17.3")
        # protobuf/3.17.3 brings zlib/1.3.1; use the HarmonyOS-published
        # 1.3.2 recipe consistently for both protobuf and zbackup.
        self.requires("zlib/1.3.2", override=True)
        self.requires("xz/5.8.3")
        if self.options.with_lzo:
            self.requires("lzo/2.10")

    def build_requirements(self):
        # protoc must run on the build machine while generating C++ from .proto.
        self.tool_requires("protobuf/3.17.3")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        CMakeDeps(self).generate()
        VirtualBuildEnv(self).generate()

        tool_protobuf = self.dependencies.build["protobuf"]
        protoc = None
        for bindir in tool_protobuf.cpp_info.bindirs:
            candidate = os.path.join(tool_protobuf.package_folder, bindir, "protoc")
            if os.path.isfile(candidate):
                protoc = candidate
                break
        if not protoc:
            raise ConanException("protobuf build-context package does not contain bin/protoc")

        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_SHARED_LIBS"] = False
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.cache_variables["CMAKE_FIND_PACKAGE_PREFER_CONFIG"] = True
        # zbackup 1.5 uses the legacy PROTOBUF_GENERATE_CPP macro. Conan's
        # Protobuf config disables it unless this compatibility hint is set.
        tc.cache_variables["protobuf_MODULE_COMPATIBLE"] = True
        tc.cache_variables["CMAKE_DISABLE_FIND_PACKAGE_LibUnwind"] = True
        tc.cache_variables["CMAKE_DISABLE_FIND_PACKAGE_LibLZO"] = not bool(self.options.with_lzo)
        tc.cache_variables["ZBACKUP_VERSION"] = self.version
        # Clang diagnoses the upstream throw(...) declarations as errors in
        # C++17; keep the CI profile standard and downgrade this legacy warning.
        tc.extra_cxxflags.append("-Wno-error=dynamic-exception-spec")
        # Both spellings are consumed by CMake's FindProtobuf and the upstream
        # PROTOBUF_GENERATE_CPP macro. Use the build-context compiler when
        # Conan is cross-building an OHOS package.
        tc.cache_variables["Protobuf_PROTOC_EXECUTABLE"] = protoc.replace("\\", "/")
        tc.cache_variables["PROTOBUF_PROTOC_EXECUTABLE"] = protoc.replace("\\", "/")
        tc.cache_variables["PROTOBUF_PROTOC_CHECK"] = protoc.replace("\\", "/")

        if str(self.settings.os) == "OHOS":
            # CMake has no HarmonyOS platform module in the current toolchain.
            # OHOS clang/sysroot flags remain from the profile; Linux here only
            # selects CMake's supported compiler-identification module.
            tc.generator = "Ninja"
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"

        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # HarmonyOS build workers require serial builds (R9).
        cmake.build(build_tool_args=["-j1"])

    def package(self):
        CMake(self).install()
        copy(self, "LICENSE*", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(
            self,
            "LICENSE*",
            src=os.path.join(self.source_folder, "licenses"),
            dst=os.path.join(self.package_folder, "licenses"),
        )
        if str(self.settings.os) == "OHOS":
            executable = os.path.join(self.package_folder, "bin", "zbackup")
            self._sign_ohos_executable(executable)

    def _find_ohos_tool(self, name):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler_dir = os.path.dirname(compilers.get("cpp", ""))
        ndk = os.environ.get("OHOS_NDK_HOME", "")
        sdk = os.path.dirname(ndk) if ndk else ""
        candidates = [
            os.path.join(compiler_dir, name) if compiler_dir else "",
            os.path.join("/data/service/hnp/bin", name),
            os.path.join(ndk, "llvm", "bin", name) if ndk else "",
            os.path.join(sdk, "toolchains", "lib", name) if sdk else "",
            shutil.which(name) or "",
        ]
        return next((path for path in candidates if path and os.path.isfile(path)), "")

    def _sign_ohos_executable(self, executable):
        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            raise ConanException(
                "OHOS CLI packaging requires llvm-objcopy and binary-sign-tool"
            )

        temporary = executable + ".signing"
        try:
            shutil.copy2(executable, temporary)
            # The section is absent on first signing and present on rebuilds.
            self.run(
                "{} --remove-section .codesign {} 2>/dev/null || true".format(
                    shlex.quote(objcopy), shlex.quote(temporary)
                ),
                env="conanbuild",
            )
            self.run(
                "{} sign -inFile {} -outFile {} -selfSign 1".format(
                    shlex.quote(signer),
                    shlex.quote(temporary),
                    shlex.quote(temporary),
                ),
                env="conanbuild",
            )
            os.chmod(temporary, os.stat(executable).st_mode)
            os.replace(temporary, executable)
        finally:
            if os.path.exists(temporary):
                os.remove(temporary)
        self.output.info("Signed OHOS CLI binary: %s" % executable)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
