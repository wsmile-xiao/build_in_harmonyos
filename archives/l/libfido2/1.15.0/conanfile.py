#!/usr/bin/env python3
"""Conan recipe — libfido2 1.15.0 (CMake).

libfido2 provides library functionality and command-line tools to
communicate with a FIDO device over USB or NFC, and to verify attestation
and assertion signatures.

HarmonyOS adaptation notes:
- libudev is not available on OHOS: patches 0001/0002/0004 add a
  static-inline libudev stub and route the HID backend to hid_linux.c.
- ppoll(2): see patch 0003 (hid_unix.c) — upstream uses ppoll unguarded;
  on OHOS musl the declaration needs _GNU_SOURCE (patch 0001 keeps the
  GNU source flags path unreachable for non-Linux, so we re-add it via
  toolchain cflags).
- Dependencies are discovered via pkg-config (PkgConfigDeps).
- upstream pkg_search_module(CRYPTO libcrypto) needs a libcrypto.pc,
  which PkgConfigDeps does not generate (openssl recipe only provides
  openssl.pc); we synthesize one in generate().
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps


class Libfido2Conan(ConanFile):
    name = "libfido2"
    version = "1.15.0"
    description = "Library for FIDO2, WebAuthn and FIDO Client to Authenticator Protocol"
    license = "BSD-2-Clause"
    homepage = "https://github.com/Yubico/libfido2"
    url = "https://developers.yubico.com/libfido2/"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "build_tools": [True, False],
    }
    default_options = {
        "shared": True,
        "build_tools": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libcbor/0.10.2")
        # fido.h 公开头 include <openssl/ec.h> 等，openssl 是头文件级公开依赖
        self.requires("openssl/3.5.6", transitive_headers=True)
        self.requires("zlib/1.3.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_STATIC_LIBS"] = "OFF" if self.options.shared else "ON"
        tc.variables["BUILD_TESTS"] = "ON"
        tc.variables["BUILD_EXAMPLES"] = "OFF"
        tc.variables["BUILD_MANPAGES"] = "OFF"
        tc.variables["BUILD_TOOLS"] = "ON" if self.options.build_tools else "OFF"
        # 上游 cmake_minimum_required(VERSION 3.7)：CMake 4.x 移除了 <3.5 兼容，
        # 需显式声明最低策略版本（同 libcbor 0.10.2 先例）
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # 上游仅对 Linux 加 -D_GNU_SOURCE/-D_DEFAULT_SOURCE（CMakeLists.txt L68-70）；
        # HarmonyOS 分支未走到该路径，但 musl 的 ppoll/arc4random_buf 等声明依赖
        # _GNU_SOURCE/_DEFAULT_SOURCE，这里补上（patch 0001 保持其余逻辑不变）
        if self.settings.os == "OHOS":
            tc.variables["CMAKE_C_FLAGS"] = "-D_GNU_SOURCE -D_DEFAULT_SOURCE"
        # 上游为 fido2_shared 设了 SOVERSION=1，但 CMake 4.x 无 Platform/HarmonyOS.cmake
        # 模块（E383），CMAKE_SHARED_LIBRARY_SONAME_C_FLAG 为空 → 链接器收不到
        # -Wl,-soname → .so 无 SONAME → tools 的 NEEDED 记录为构建目录相对路径
        # ../src/libfido2.so（安装后不可运行）。按 E383+E330 标准方案修复：
        # 补 SONAME flag + 禁用版本化 symlink（HMDFS 兼容，包内单文件布局），
        # soname 取不带版本的 libfido2.so。已实测：fido2-token -V 输出 1.15.0。
        if self.options.shared:
            tc.cache_variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
            tc.cache_variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "ON"
        tc.generate()

        pc = PkgConfigDeps(self)
        pc.generate()
        env = VirtualBuildEnv(self)
        env.generate()

        # 上游 CMakeLists 用 pkg_search_module(CRYPTO libcrypto) 找加密库，
        # 而 PkgConfigDeps 只按 openssl 配方的 pkg_config_names 生成 openssl.pc。
        # 这里补一个 libcrypto.pc（指向同一包目录），保持 conan 标准依赖管理。
        openssl = self.dependencies["openssl"]
        pc_dir = os.path.join(self.generators_folder)
        libdir = ";".join(
            os.path.join(str(openssl.package_folder), str(d)) for d in openssl.cpp_info.libdirs
        ) or os.path.join(str(openssl.package_folder), "lib")
        includedir = ";".join(
            os.path.join(str(openssl.package_folder), str(d)) for d in openssl.cpp_info.includedirs
        ) or os.path.join(str(openssl.package_folder), "include")
        libs = " ".join("-l%s" % l for l in openssl.cpp_info.libs) or "-lcrypto"
        with open(os.path.join(pc_dir, "libcrypto.pc"), "w") as f:
            f.write(
                f"prefix={openssl.package_folder}\n"
                f"libdir={libdir}\n"
                f"includedir={includedir}\n\n"
                f"Name: libcrypto\n"
                f"Description: OpenSSL cryptography library (conan openssl/{openssl.ref.version})\n"
                f"Version: {openssl.ref.version}\n"
                f"Libs: -L\"${{libdir}}\" {libs}\n"
                f"Cflags: -I\"${{includedir}}\"\n"
            )

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["fido2"]
        # 上游安装的 CMake pkg-config 名是 fido2（libfido2.pc / fido2 目标），
        # 保持下游 find_package(fido2) / pkg-config fido2 与上游一致
        self.cpp_info.set_property("cmake_file_name", "fido2")
        self.cpp_info.set_property("cmake_target_name", "fido2::fido2")
        self.cpp_info.set_property("pkg_config_name", "libfido2")
        if self.options.build_tools:
            self.cpp_info.bindirs = ["bin"]
