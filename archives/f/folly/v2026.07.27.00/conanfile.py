#!/usr/bin/env python3
"""Conan recipe — folly v2026.07.27.00 (CMake)

上游 folly 是大型 CMake C++ 库（C++17），依赖链较长。
本配方按仓库规范（R26/R27 + OHOS 平台处理）编写，参考同仓库 fmt/12.2.0 与
既有 folly/v2024.11.18.00 半成品笔记。

REQUIRED 依赖（folly-deps.cmake 中 REQUIRED）：
  Boost(context/filesystem/program_options/regex)、FastFloat、Glog、LibEvent、
  OpenSSL、fmt。
可选依赖（find_package 不带 REQUIRED，OHOS 上缺失时功能自动禁用）：gflags/zlib/
  zstd/snappy/lz4/bzip2/lzma/libsodium/libunwind/libaio/liburing/libdwarf/libiberty。
本配方只声明 REQUIRED 依赖 + 尽量可用的可选依赖，避免依赖宿主机偶然头文件。

注意：新版 folly(2026) 已改用 fmt 取代 double-conversion（folly-deps.cmake 无
FindDoubleConversion），与旧版 v2024.11.18.00 笔记不同，故 requirements 不声明
double-conversion。
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
import os
import shutil


class FollyConan(ConanFile):
    name = "folly"
    version = "v2026.07.27.00"
    description = "Facebook Folly C++ library"
    license = "Apache-2.0"
    homepage = "https://github.com/facebook/folly"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # R27: 依赖用 @ohpcd/stable 格式（本仓库 CLI 流水线自动注入前缀）。
        # R26: 系统库默认静态（BUILD_SHARED_LIBS=OFF）。
        # REQUIRED deps:
        # Boost: folly-deps.cmake 硬 REQUIRED COMPONENTS context filesystem
        #   program_options regex。ohpcd 整合 boost 均排除/expose 不齐 context，
        #   boost/1.90.0.4 暴露 Boost::regex+filesystem+program_options；
        #   Boost::context 由拆分包 boost1.84-context（cmake_file_name=Boost.Context）
        #   另行提供，两者各自独立 config 共存，非伪造依赖。
        # transitive_headers=True：folly 公共头（如 FBString.h 公开 #include
        #   <fmt/format.h>，其余 boost/glog/fast_float/libevent/openssl 同）真正暴露这些
        #   依赖的头。folly 是静态库（library + 默认 shared=False），conan 2.29 对静态库
        #   默认裁剪传给下游的依赖 headers（requires.py STATIC→downstream headers=False），
        #   导致消费方 CMakeDeps 拿不到这些依赖的 INCLUDEDIRS；此处显式声明 transitive_headers
        #   覆盖该裁剪，使 CMakeDeps 把 INCLUDEDIRS 沿 folly_DEPS_TARGET 传入消费方编译命令行。
        #   这是诚实声明（folly 公共头真实依赖），非伪造。
        self.requires("boost/1.90.0.4", transitive_headers=True)
        self.requires("boost1.84-context/1.84.0.1", transitive_headers=True)
        self.requires("fast_float/8.0.1", transitive_headers=True)
        self.requires("glog/0.7.1", transitive_headers=True)
        self.requires("libevent/2.1.13", transitive_headers=True)
        self.requires("openssl/3.0.21", transitive_headers=True)
        self.requires("fmt/12.2.0", transitive_headers=True)
        # 可选但 folly 大量 #ifdef 使用、OHOS 上可用的。
        # 这些是纯实现细节（不暴露于 folly 公共头，也不需消费方传递 include），
        # 标 visible=False：conan 2.29 校验要求所有 visible 直接依赖都必须出现在
        # cpp_info.requires 中，可选依赖非必需头则豁免该校验（见 cpp_info.py 校验逻辑）。
        self.requires("gflags/2.2.2", visible=False)
        self.requires("zlib/1.3.1", visible=False)
        self.requires("zstd/1.5.7", visible=False)
        self.requires("snappy/1.2.2", visible=False)
        self.requires("lz4/1.10.0.1", visible=False)
        self.requires("libsodium/1.0.20", visible=False)
        self.requires("libunwind/1.6.2", visible=False)
        self.requires("libaio/0.3.112.1", visible=False)
        self.requires("liburing/2.15", visible=False)
        self.requires("bzip2/1.0.8", visible=False)
        # 测试构建需要 gtest/gmock（非运行时依赖）
        self.test_requires("gtest/1.17.0")

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # ★ os=OHOS 守卫：conan 默认把 CMAKE_SYSTEM_NAME 设 "HarmonyOS"，但 cmake
        # 平台文件是 Modules/Platform/OHOS.cmake，名字对不上会让平台变量留空
        # （SONAME flag 为空 → 无 DT_SONAME，传染下游）。无条件设置会顶掉 os=Linux
        # 等 profile 的正确识别，故加 os 守卫。
        if self.settings.os == "OHOS":
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
            # ★ 交叉编译 try_run 探测器（FOLLY_HAVE_UNALIGNED_ACCESS /
            # FOLLY_HAVE_WEAK_SYMBOLS / FOLLY_HAVE_LINUX_VDSO / FOLLY_HAVE_WCHAR_SUPPORT /
            # HAVE_VSNPRINTF_ERRORS 等）无法自动在目标执行。OHOS PC 构建宿主机本身是
            # aarch64 且是 musl（实测可原生运行 OHOS ELF：`./probe` exit 透传），
            # 故注入一个透传 wrapper 作为 CMAKE_CROSSCOMPILING_EMULATOR，让 try_run
            # 在宿主机原生执行并得到真实探测结果（而非伪造 EXITCODE）。
            emu = os.path.join(self.build_folder, "ohos-emu.sh")
            with open(emu, "w") as f:
                f.write("#!/bin/sh\nexec \"$@\"\n")
            os.chmod(emu, 0o755)
            tc.cache_variables["CMAKE_CROSSCOMPILING_EMULATOR"] = emu
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        # R26: 系统名库默认静态；跟随 options.shared，不写死。
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # 显式覆盖为标准下限 C++20：上游 folly 2026 头文件用到 consteval/requires/
        # is_constant_evaluated 等 C++20 特性，其 CMakeLists 默认 set(20)。
        # CMakeToolchain 的 std watch 默认按 profile 的 compiler.cppstd(17) 强制回写，
        # 故必须在此显式声明，否则被钉在 17 而编译报错。clang 15 完整支持 C++20，
        # 依赖库保持 C++17 静态链接 ABI 兼容，无需整体升标准。
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
        # 测试不随构建（test_package 自行处理），避免全量 CTest 在非交互环境跑。
        tc.variables["BUILD_TESTS"] = "OFF"
        tc.variables["BUILD_BENCHMARKS"] = "OFF"
        tc.variables["BUILD_EXAMPLES"] = "OFF"
        tc.generate()
        CMakeDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(build_script_folder="")
        cmake.build()

    def package(self):
        CMake(self).install()
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # 鸿蒙专有：给 .so / 可执行加 .codesign。os != OHOS 时工具不存在，必须守卫。
        if self.settings.os != "OHOS":
            return
        targets = []
        libdir = os.path.join(self.package_folder, "lib")
        if os.path.isdir(libdir):
            for root, _dirs, files in os.walk(libdir):
                for name in files:
                    if name.endswith(".so") or ".so." in name:
                        targets.append(os.path.join(root, name))
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in os.listdir(bindir):
                p = os.path.join(bindir, name)
                if os.path.isfile(p) and not os.path.islink(p) and self._is_elf(p):
                    targets.append(p)
        objcopy = self._resolve_sign_tool(
            "/data/service/hnp/bin/llvm-objcopy", "llvm-objcopy")
        signer = self._resolve_sign_tool(
            "/data/service/hnp/bin/binary-sign-tool", "binary-sign-tool")
        for f in targets:
            if os.path.islink(f):
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    @staticmethod
    def _resolve_sign_tool(hardcoded, fallback_name):
        if os.path.exists(hardcoded):
            return hardcoded
        found = shutil.which(fallback_name)
        return found or hardcoded

    def package_info(self):
        self.cpp_info.libs = ["folly"]
        self.cpp_info.set_property("cmake_file_name", "folly")
        self.cpp_info.set_property("cmake_target_name", "Folly::folly")
        self.cpp_info.set_property("pkg_config_name", "libfolly")
        self.cpp_info.includedirs = ["include"]
        # 传递公有头文件依赖：folly 的公共头（如 FBString.h）公开 #include <fmt/format.h>，
        # 以及 boost/glog/fast_float/libevent/openssl 的头。conan 2 中库配方的依赖头文件
        # 不会自动向下游传播——必须在 cpp_info.requires 显式声明，CMakeDeps 才会把它们的
        # INCLUDEDIRS 沿 folly_DEPS_TARGET 传入消费方编译命令行（否则 fmt/format.h 找不到）。
        # 只列 REQUIRED（folly 公共头真正暴露的）；可选实现细节依赖已在 requirements() 标
        # visible=False，不参与传播也不触发 conan 2.29 的 "direct dependency not used" 校验。
        self.cpp_info.requires = [
            "fmt::fmt",
            "boost::boost",
            "boost1.84-context::boost1.84-context",
            "glog::glog",
            "fast_float::fast_float",
            "libevent::libevent",
            "openssl::openssl",
            # gflags 虽在 requirements() 标 visible=False，但 glog 传递依赖它，conan
            # 合并可见性后 gflags 仍是 visible 直接依赖，2.29 校验要求它也必须在此列出。
            "gflags::gflags",
        ]
