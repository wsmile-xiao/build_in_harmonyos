#!/usr/bin/env python3
"""Conan recipe — mmkv 2.4.2 (Tencent MMKV key-value storage framework).

Upstream: https://github.com/Tencent/MMKV (tag v2.4.2)

Build strategy:
  * The C++ core lives in Core/ with its own CMakeLists.txt (target `core`,
    always STATIC — same delivery form as the official Android/iOS SDKs).
  * On OHOS the toolchain predefines __OHOS__, which selects the
    MMKV_OHOS code path (hilog logging, no ashmem, musl-compatible mmap).
    Upstream supports this natively; zero patches required.
  * zlib for CRC32 is embedded (MMKV_EMBED_ZLIB=1, upstream default when
    find_library(z) is not resolvable in the cross sysroot) → the archive
    is fully self-contained.
  * AES (openssl-derived crypto subset with armv8+crypto asm) is embedded.
  * The upstream POSIX/src SHARED wrapper would produce an empty
    libmmkv.so (libmmkv.cpp is an empty TU and unreferenced archive
    members get dropped by the linker), therefore this package delivers
    the real static library as libmmkv.a.

Consumers need: -lmmkv + system libs hilog_ndk.z + pthread (OHOS) or
pthread only (Linux).

Enforced rules:
  R32: settings.os in ("Linux", "OHOS")
  R33: flags come from Conan Toolchain, no bare shell variables
  R34: test_package calls the real MMKV C bridge + C++ API
  R39: official GitHub source URL
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class MmkvConan(ConanFile):
    name = "mmkv"
    version = "2.4.2"
    description = (
        "Tencent MMKV — mmap-based key-value storage framework "
        "(the same store used by WeChat)"
    )
    license = "BSD-3-Clause"
    homepage = "https://github.com/Tencent/MMKV"
    url = "https://github.com/Tencent/MMKV"
    topics = ("mmkv", "key-value", "storage", "mmap", "tencent")

    # Upstream Core/CMakeLists.txt hardcodes add_library(core STATIC ...).
    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        # Standard patch pipeline hookup (no patches needed for mmkv —
        # upstream already ships the __OHOS__ code path).
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def validate(self):
        # R32: platform whitelist
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "mmkv only supports Linux and OHOS, current: {}".format(
                    self.settings.os))

    def source(self):
        # Official tarball, top dir MMKV-2.4.2/.
        # filename 显式带 .tar.gz 后缀：codeload 直链 URL 的 basename 是
        # "v2.4.2"（无后缀），conan unzip() 按后缀判型会误走 zip 分支报
        # BadZipFile（CI build #45277 实测）。指定 filename 强制 tar 路径。
        get(self, **self.conan_data["sources"], filename="mmkv-2.4.2.tar.gz",
            strip_root=True)

        # Promote Core/ to the source root: Core/CMakeLists.txt is fully
        # self-contained (all paths use CMAKE_CURRENT_SOURCE_DIR), so a
        # plain lift keeps every include dir / copy_files() reference valid.
        core = os.path.join(self.source_folder, "Core")
        if not os.path.isdir(core):
            raise ConanInvalidConfiguration(
                "Core/ subdirectory missing in source tarball")
        for item in os.listdir(core):
            shutil.move(os.path.join(core, item),
                        os.path.join(self.source_folder, item))
        os.rmdir(core)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            # Activate the upstream OHOS branch in Core/CMakeLists.txt:
            # armv8+crypto ASM flags + -D__MUSL__ for aarch64.
            tc.variables["OHOS"] = True
            tc.variables["OHOS_ARCH"] = "arm64-v8a"
        tc.generate()

    def build(self):
        # Apply conandata patches if any (none for mmkv 2.4.2).
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        # Headers staged by the upstream copy_files() call during configure:
        #   include/MMKV/{MMKV.h,MMKVPredef.h,MMBuffer.h,MiniPBCoder.h,
        #                 MMKVHandler.h} (+ MemoryFile.h / MMKVLog.h on the
        #                 OHOS/ANDROID code path)
        include_src = os.path.join(self.source_folder, "include", "MMKV")
        copy(self, "*.h", src=include_src,
             dst=os.path.join(self.package_folder, "include", "MMKV"))
        # cbridge public header (C API) is installed by its own rule below.
        cbridge_src = os.path.join(self.source_folder, "cbridge")
        copy(self, "MMKVBridge.h", src=cbridge_src,
             dst=os.path.join(self.package_folder, "include", "MMKV"))
        # The static library: Core produces libcore.a, deliver as libmmkv.a
        build_lib = os.path.join(self.build_folder, "libcore.a")
        dst_lib = os.path.join(self.package_folder, "lib", "libmmkv.a")
        os.makedirs(os.path.dirname(dst_lib), exist_ok=True)
        shutil.copy(build_lib, dst_lib)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "mmkv")
        self.cpp_info.set_property("cmake_target_name", "mmkv::mmkv")
        self.cpp_info.set_property("pkg_config_name", "mmkv")
        self.cpp_info.libs = ["mmkv"]
        self.cpp_info.includedirs = ["include"]
        if self.settings.os == "OHOS":
            # MMKV_OHOS log path calls OH_LOG_Print (libhilog_ndk.z.so)
            # and the mmap store needs pthread.
            self.cpp_info.system_libs = ["hilog_ndk.z", "pthread"]
        else:
            self.cpp_info.system_libs = ["pthread"]
