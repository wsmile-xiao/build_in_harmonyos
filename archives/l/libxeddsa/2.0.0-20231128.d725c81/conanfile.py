#!/usr/bin/env python3
"""Conan recipe — libxeddsa 2.0.0-20231128.d725c81 (Syndace).

libxeddsa is a toolkit around Curve25519 and Ed25519 key pairs: key
conversion between both curves (RFC 7748 §4.1 birational maps), Ed25519
signing with a raw private key (XEdDSA, Signal spec) or with a seed
(RFC 8032 via libsodium), signature verification and X25519 key
agreement. Upstream: https://github.com/Syndace/libxeddsa, commit
d725c816bb26483ac397ce0d19de5ad2972955f1 = tag v2.0.0 (2023-11-28).

Build system: CMake >= 3.5, pure C. Upstream always builds a static and
a dynamic variant plus test executables; patch 0001 gates the shared
targets on BUILD_SHARED_LIBS so the static-first default (R26) can skip
them, because a libxeddsa.so would have to absorb the non-PIC static
libsodium.a shipped by the ohpcd registry (libsodium recipe is
static-only, --disable-shared --enable-static).

Dependency: libsodium/1.0.22, published to ohpcd (recipe and OHOS
binary verified with conan download, --only-recipe, remote=ohpcd).
The shadow CI disables
conancenter (ci/conan/setup.sh), so the bare requires() resolves to the
ohpcd recipe and its OHOS binary; no on-device rebuild happens. All
symbols libxeddsa needs (sodium_init, sodium_memzero, sodium_stackzero,
randombytes_buf, crypto_hash_sha512_{init,update,final},
crypto_sign_{ed25519_detached,verify_detached,ed25519_sk_to_*},
crypto_scalarmult_curve25519) were verified present in the ohpcd
libsodium 1.0.22 package headers and archive.

How libsodium is wired into the build: upstream ships a bundled
module-mode FindSodium.cmake (find_package(Sodium REQUIRED)) that
unsets any sodium_LIBRARY*/sodium_INCLUDE_DIR CACHE entries on every
configure (its `sodium_USE_STATIC_LIBS EQUAL sodium_USE_STATIC_LIBS_LAST`
guard compares the non-numeric "NO" and always unsets), so -D cache
overrides are unreliable. Instead the recipe feeds the documented
find_path/find_library search variables CMAKE_INCLUDE_PATH and
CMAKE_LIBRARY_PATH (plus CMAKE_PREFIX_PATH) from the conan dependency
package folder, which FindSodium.cmake picks up after its (absent)
pkg-config hints.

CMAKE_SYSTEM_NAME: the OHOS-adapted CMakeToolchain maps os=OHOS to
CMAKE_SYSTEM_NAME=HarmonyOS, which vanilla CMake does not know; ref10's
`if (UNIX)` and FindSodium's `elseif (UNIX)` would both fall through to
"FATAL_ERROR: Unsupported operating system". The recipe declares Linux
instead (et/7.0.0 precedent) — the device compiler is native clang for
aarch64-linux-ohos, and ref10's CHECK_SYMBOL_EXISTS random-source probe
resolves to getentropy(2) from musl's unistd.h.

Upstream tests: ctest registers xeddsa_test_static (one binary running
three suites: test_signing 64x64 key/message matrix, test_conversion_
uniqueness 8192 keys, test_pub_derivation) and kernelrandombytes_test_
static. The CI runs the same profile for host and build, tests execute
natively on the device.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class LibxeddsaConan(ConanFile):
    name = "libxeddsa"
    version = "2.0.0-20231128.d725c81"
    description = "Toolkit around Curve25519 and Ed25519 key pairs: conversion, XEdDSA signing, verification and X25519"
    license = "MIT"
    homepage = "https://github.com/Syndace/libxeddsa"
    url = "https://github.com/Syndace/libxeddsa"
    topics = ("crypto", "ed25519", "curve25519", "xeddsa", "vxeddsa", "signing")

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libxeddsa recipe supports Linux/OHOS only, got {self.settings.os}"
            )

    def requirements(self):
        # ohpcd 制品仓为裸 ref（无 channel，address-standardizer 先例）；
        # CI setup.sh 禁用 conancenter，故解析到 ohpcd 的 OHOS 二进制。
        self.requires("libsodium/1.0.22")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: 静态优先；patch 0001 以 BUILD_SHARED_LIBS 门控动态目标。
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # OHOS 适配版 CMakeToolchain 默认写 CMAKE_SYSTEM_NAME=HarmonyOS
        # （vanilla CMake 无 Platform/HarmonyOS），ref10 的 if(UNIX) 会落到
        # FATAL_ERROR；声明 Linux（et/7.0.0 先例）。
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        # 喂 bundled FindSodium.cmake（module 模式 find_path/find_library）：
        # 其内部每次 configure 都 unset sodium_* CACHE（非数字 EQUAL 恒
        # false），-D 覆盖不可靠；CMAKE_INCLUDE_PATH/CMAKE_LIBRARY_PATH 是
        # find_path/find_library 的文档化搜索变量。
        sodium = self.dependencies["libsodium"]
        sodium_inc = os.path.join(sodium.package_folder, "include")
        sodium_lib = os.path.join(sodium.package_folder, "lib")
        tc.variables["CMAKE_INCLUDE_PATH"] = sodium_inc
        tc.variables["CMAKE_LIBRARY_PATH"] = sodium_lib
        tc.variables["CMAKE_PREFIX_PATH"] = sodium.package_folder
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        # 上游 ctest：xeddsa_test_static（3 套件合一二进制）+
        # kernelrandombytes_test_static。CI 同 profile 构建（native），
        # 测试直接在真机执行；交叉场景跳过（L1 证据见 reports/）。
        # 注意：不用 cmake.test(output_on_failure=True)——真机 conan 的
        # CMake.test() 无该形参（TypeError 实测）；libzmq 4.3.5 先例：
        # 显式 self.run ctest，各 conan 版本行为一致。
        if can_run(self):
            self.output.info("Running libxeddsa upstream ctest suite")
            self.run("ctest --output-on-failure",
                     cwd=self.build_folder, env="conanbuild")
        else:
            self.output.info("cross-building: upstream ctest binaries not runnable here")

    def package(self):
        cmake = CMake(self)
        # install(TARGETS xeddsa_static) -> lib/libxeddsa.a
        cmake.install()
        # 上游没有安装头文件的规则：公开头 xeddsa.h 及其依赖的
        # cross_platform.h（ref10/include，xeddsa.h 直接 #include）手工补装。
        copy(self, "xeddsa.h",
             src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "cross_platform.h",
             src=os.path.join(self.source_folder, "ref10", "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["xeddsa"]
        self.cpp_info.includedirs = ["include"]
        # libxeddsa.a 引用 libsodium 符号（sodium_init/randombytes/sha512/
        # stackzero 等），静态闭包需要消费者传递链接 libsodium。
        self.cpp_info.requires.append("libsodium::libsodium")
        self.cpp_info.set_property("pkg_config_name", "libxeddsa")
