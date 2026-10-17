#!/usr/bin/env python3
"""Conan recipe for brpc 1.17.0 (CMake).

Apache brpc (bRPC) 是百度开源的工业级 RPC 框架。适配 HarmonyOS PC
(aarch64, musl, clang 15.0.4)。

适配要点：
- 依赖全部来自制品仓：protobuf/33.6 + abseil-cpp/20260107.1（二者 ABI
  必须一致，protobuf > 4.21 走 absl）、gflags/2.2.2、leveldb/1.23、
  openssl/3.5.6、zlib/1.3.1、snappy/1.2.2（可选）。
- brpc 的 CMakeLists 用 `find_package(Protobuf)`（配置模式，protobuf 制品仓
  导出 cmake_find_mode=none），需显式注入 Protobuf_DIR / utf8_range_DIR /
  absl_DIR（与 grpc 配方同源）。
- bthread 协程的 aarch64 上下文切换汇编内嵌在 src/bthread/context.cpp
  （`__asm`），在 OHOS (musl, linux-ohos triplet) 上 `__linux__` 判定成立，
  走 `BTHREAD_CONTEXT_PLATFORM_linux_arm64` 路径，无需补丁。
- OHOS 缺少 gperftools（tcmalloc），但 CMake 构建路径已内置 `-DNO_TCMALLOC`，
  不依赖 gperftools；thrift 不在制品仓，`WITH_THRIFT=OFF`。
- 共享库在 OHOS 上需补 SONAME 并签名（同 gflags 配方，见 package()）。
"""

import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class BrpcConan(ConanFile):
    name = "brpc"
    version = "1.17.0"
    description = "Apache bRPC - an industrial-grade RPC framework"
    license = "Apache-2.0"
    homepage = "https://github.com/apache/brpc"
    url = "https://github.com/apache/brpc"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "with_snappy": [True, False],
    }
    default_options = {
        "shared": True,
        "with_snappy": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("brpc supports Linux and OHOS targets")

    def validate(self):
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("brpc supports OHOS armv8 only")

    def requirements(self):
        # absl ABI 必须与 protobuf/33.6 的 (lts_20260107) 一致。
        self.requires("abseil-cpp/20260107.1", transitive_headers=True)
        self.requires("protobuf/33.6")
        self.requires("gflags/2.2.2")
        self.requires("leveldb/1.23")
        self.requires("openssl/3.5.6")
        self.requires("zlib/1.3.1")
        if self.options.with_snappy:
            self.requires("snappy/1.2.2")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        CMakeDeps(self).generate()

        # protoc 是制品仓 protobuf 的 OHOS 目标二进制，本机为原生 OHOS arm64
        # 可直接执行，但其依赖的 libc++_shared.so 不在默认搜索路径，需把
        # 工具链 SDK 的 libc++ 目录前置到 LD_LIBRARY_PATH（见 notes.md）。
        env = Environment()
        env.prepend_path("LD_LIBRARY_PATH", self._toolchain_libcpp_dir())
        env.vars(self, scope="build").save_script("brpc_protoc_libcpp_env")

        tc = CMakeToolchain(self)
        # 构建系统选项：CI 只验证库 + 工具，不下载 googletest 跑上游单测。
        # 上游单测（test/*.cpp）在本地以 BUILD_UNIT_TESTS=ON 单独构建并统计。
        tc.variables["BUILD_UNIT_TESTS"] = False
        # R8 合规：补丁不使用平台宏（__OHOS__），由配方注入 musl 语义特性宏。
        # 注意：不能写 tc.variables["CMAKE_CXX_FLAGS"]（会覆盖 conan 默认的
        # -stdlib/include flags，第 29 轮实测覆盖导致 absl 头丢失）——改用
        # build env 的 CXXFLAGS 追加（VirtualBuildEnv 传导给 cmake，与 profile
        # flags 叠加而非替换）。对任何 musl 环境（alpine/musl Linux）同样适用。
        env2 = Environment()
        env2.append("CXXFLAGS", "-DBRPC_MUSL_COMPAT")
        env2.append("CFLAGS", "-DBRPC_MUSL_COMPAT")
        env2.vars(self, scope="build").save_script("brpc_musl_compat_defines")
        tc.variables["BUILD_FUZZ_TESTS"] = False
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["WITH_SNAPPY"] = bool(self.options.with_snappy)
        tc.variables["WITH_THRIFT"] = False
        tc.variables["WITH_GLOG"] = False
        tc.variables["WITH_BTHREAD_TRACER"] = False
        tc.variables["WITH_RDMA"] = False
        tc.variables["DOWNLOAD_GTEST"] = False

        # protobuf 制品仓导出 cmake_find_mode=none，显式指向其安装的 config 文件
        #（镜像 grpc 配方的接线方式）。
        protobuf = self.dependencies["protobuf"]
        tc.variables["Protobuf_DIR"] = os.path.join(
            protobuf.package_folder, "lib", "cmake", "protobuf"
        ).replace("\\", "/")
        tc.variables["utf8_range_DIR"] = os.path.join(
            protobuf.package_folder, "lib", "cmake", "utf8_range"
        ).replace("\\", "/")

        abseil = self.dependencies["abseil-cpp"]
        tc.variables["absl_DIR"] = os.path.join(
            abseil.package_folder, "lib", "cmake", "absl"
        ).replace("\\", "/")

        # brpc 用内置 FindOpenSSL 模块定位 OpenSSL，需指定制品仓包根目录。
        tc.variables["OPENSSL_ROOT_DIR"] = self.dependencies["openssl"].package_folder.replace(
            "\\", "/"
        )

        # leveldb / protoc / snappy 走 brpc 的 find_path/find_library，
        # CMAKE_PREFIX_PATH 已由 CMakeToolchain 注入依赖包目录，可自动命中。
        # E092: CMake 无 HarmonyOS 平台模块，强制走 Linux 分支，让 brpc 的
        # if(CMAKE_SYSTEM_NAME STREQUAL "Linux") 选中 Linux 平台源文件与 -lrt。
        if str(self.settings.os) == "OHOS":
            tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"

        # gflags/protobuf 制品仓导出 cmake_find_mode=none，find_package 走 CONFIG
        # 模式只声明 gflags::gflags / protobuf::* 目标，不填充 brpc 期望的
        # 旧式 MODULE 变量（GFLAGS_INCLUDE_PATH / PROTOBUF_INCLUDE_DIRS 等），
        # 这里显式补齐（与 grpc 配方同源，见 notes.md）。
        gflags_pkg = self.dependencies["gflags"].package_folder.replace("\\", "/")
        tc.variables["GFLAGS_INCLUDE_PATH"] = os.path.join(gflags_pkg, "include")
        tc.variables["GFLAGS_LIBRARY"] = os.path.join(gflags_pkg, "lib", "libgflags.so")

        # brpc 顶层 CMakeLists 的 include_directories(${PROTOBUF_INCLUDE_DIRS}) 是
        # 单变量传递（空格分隔的两个路径会被引号包裹成单个 -I），因此只用 protobuf
        # 自身 include；abseil 头（absl/...，protobuf 头所依赖）通过 CXXFLAGS 追加。
        protobuf_pkg = self.dependencies["protobuf"].package_folder.replace("\\", "/")
        abseil_include = os.path.join(abseil.package_folder.replace("\\", "/"), "include")
        tc.variables["PROTOBUF_INCLUDE_DIRS"] = os.path.join(protobuf_pkg, "include")
        tc.variables["PROTOBUF_INCLUDE_DIR"] = os.path.join(protobuf_pkg, "include")
        tc.variables["PROTOBUF_LIBRARIES"] = ";".join([
            os.path.join(protobuf_pkg, "lib", "libprotobuf.a"),
            os.path.join(protobuf_pkg, "lib", "libutf8_range.a"),
            os.path.join(protobuf_pkg, "lib", "libutf8_validity.a"),
        ])
        tc.variables["PROTOBUF_PROTOC_EXECUTABLE"] = os.path.join(protobuf_pkg, "bin", "protoc")
        # protobuf 33.x 头文件依赖 absl（transitive_headers），编译期需同时可见
        tc.extra_cxxflags = [
            "-I{}".format(abseil_include),
            "-I{}".format(os.path.join(protobuf_pkg, "include")),
        ]

        # FindOpenSSL 在 CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON 下走 CMakeDeps config，
        # 只声明 openssl::openssl 目标，不设置 brpc 期望的模块变量
        # （include_directories(${OPENSSL_INCLUDE_DIR}) 为空 → ssl_compat.h 找不到头）。
        openssl_pkg = self.dependencies["openssl"].package_folder.replace("\\", "/")
        tc.variables["OPENSSL_INCLUDE_DIR"] = os.path.join(openssl_pkg, "include")
        tc.variables["OPENSSL_INCLUDE_DIRS"] = os.path.join(openssl_pkg, "include")
        tc.variables["OPENSSL_SSL_LIBRARY"] = os.path.join(openssl_pkg, "lib", "libssl.a")
        tc.variables["OPENSSL_CRYPTO_LIBRARY"] = os.path.join(openssl_pkg, "lib", "libcrypto.a")

        tc.generate()

    def _toolchain_libcpp_dir(self):
        """返回工具链 libc++_shared.so 所在目录（用于运行 OHOS 目标 protoc）。"""
        from conan.tools.build import build_jobs  # noqa: F401  (import guard)
        cc = str(self.conf.get("tools.build:compiler_executables", {}).get(
            "cpp", "")) if self.conf.get("tools.build:compiler_executables") else ""
        if not cc:
            return ""
        cc_real = os.path.realpath(cc)
        cand = os.path.join(
            os.path.dirname(os.path.dirname(cc_real)),
            "lib", "aarch64-linux-ohos", "c++",
        )
        return cand if os.path.isdir(cand) else ""

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # brpc 的 CMakeLists 声明 cmake_minimum_required(VERSION 2.8.12)，
        # CMake 4.x 已移除 <3.5 的兼容，需显式放宽（同 gflags 配方）。
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build()

    def package(self):
        CMake(self).install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        if self.options.shared and str(self.settings.os) == "OHOS":
            self._sign_shared_libraries()

    def _sign_shared_libraries(self):
        """OHOS 上给共享库补 SONAME 并签名（同 gflags 配方）。

        brpc 的 brpc-shared 目标未设置 VERSION/SOVERSION，产出的 libbrpc.so
        无 DT_SONAME，下游按完整路径链接会把构建机 conan cache 绝对路径写进
        DT_NEEDED，换机器即无法加载；需 patchelf 补 SONAME 后重新签名。
        """
        patchelf = "/data/service/hnp/bin/patchelf"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        libraries = glob.glob(
            os.path.join(self.package_folder, "lib", "**", "*.so*"), recursive=True
        )
        for library in libraries:
            if os.path.islink(library):
                continue
            base = os.path.basename(library)
            if not base.startswith("lib"):
                continue
            # 剥离可能残留的旧签名段
            self.run(
                '{} --remove-section .codesign "{}" 2>/dev/null || true'.format(
                    objcopy, library
                )
            )
            # 无 SONAME 时补上（SONAME 设为文件名本身，与上游无版本名一致）
            if os.path.isfile(patchelf):
                self.run(
                    '{pe} --set-soname "{base}" "{lib}"'.format(
                        pe=patchelf, base=base, lib=library
                    )
                )
            if os.path.isfile(signer):
                self.run(
                    '{} sign -inFile "{}" -outFile "{}" -selfSign 1'.format(
                        signer, library, library
                    )
                )

    def package_info(self):
        # brpc 无自生成 CMake config；由 CMakeDeps 生成 brpc-config.cmake。
        # 不设 cpp_info.requires（镜像 grpc 配方）：protobuf 制品仓
        # cmake_find_mode=none，CMakeDeps 不为其生成 config，若 requires 引用
        # protobuf 会让 brpc-config.cmake 生成 find_dependency(protobuf) 而失败。
        # 消费者需自行 find_package 传递依赖（见 test_package）。
        self.cpp_info.libs = ["brpc"]
        self.cpp_info.system_libs = ["pthread", "dl"]
