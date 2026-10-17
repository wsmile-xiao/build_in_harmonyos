#!/usr/bin/env python3
"""Conan test_package — 消费者视角验证 brpc RPC 往返（R34 实质调用）。"""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class BrpcTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # protobuf 制品仓 cmake_find_mode=none，test_package 的 protoc
        # 生成步骤直接用制品仓二进制路径；本机为原生 OHOS arm64，可执行，
        # 需把工具链 libc++ 目录前置到 LD_LIBRARY_PATH（与主配方同因）。
        from conan.tools.env import Environment

        protobuf = self.dependencies["protobuf"]
        protoc = os.path.join(protobuf.package_folder, "bin", "protoc")

        cc = str(self.conf.get("tools.build:compiler_executables", {}).get(
            "cpp", "")) if self.conf.get("tools.build:compiler_executables") else ""
        libcpp_dir = ""
        if cc:
            cc_real = os.path.realpath(cc)
            cand = os.path.join(
                os.path.dirname(os.path.dirname(cc_real)),
                "lib", "aarch64-linux-ohos", "c++",
            )
            if os.path.isdir(cand):
                libcpp_dir = cand

        env = Environment()
        if libcpp_dir:
            env.prepend_path("LD_LIBRARY_PATH", libcpp_dir)
        # test_brpc 运行期依赖：libbrpc.so（conan 包 lib 目录）→ libgflags.so/
        # libleveldb.so（依赖包 lib 目录）。conanbuild 聚合 env 不含动态库搜索
        # 路径（依赖多为静态），这里显式补齐。
        for dep_name in ("brpc", "gflags", "leveldb"):
            dep = self.dependencies.get(dep_name)
            if dep is None or not getattr(dep, "package_folder", None):
                continue
            libdir = os.path.join(dep.package_folder, "lib")
            if os.path.isdir(libdir):
                env.prepend_path("LD_LIBRARY_PATH", libdir)
        env.vars(self, scope="build").save_script("test_brpc_protoc_env")

        tc = CMakeToolchain(self)
        # protobuf 制品仓 cmake_find_mode=none，CMakeDeps 不为它生成 config；
        # brpc-config.cmake 的 find_dependency(protobuf) 需指向 protobuf 包内
        # 安装的上游 config（镜像 grpc 配方 test_package 的接线方式）。
        protobuf = self.dependencies["protobuf"]
        abseil = self.dependencies["abseil-cpp"]
        tc.variables["Protobuf_DIR"] = os.path.join(
            protobuf.package_folder, "lib", "cmake", "protobuf"
        ).replace("\\", "/")
        # CMakeDeps 生成 brpc_FIND_DEPENDENCY_NAMES 里的包名是小写 "protobuf"，
        # find_dependency(protobuf) 查找的缓存变量是 protobuf_DIR（大小写敏感）
        tc.variables["protobuf_DIR"] = os.path.join(
            protobuf.package_folder, "lib", "cmake", "protobuf"
        ).replace("\\", "/")
        tc.variables["utf8_range_DIR"] = os.path.join(
            protobuf.package_folder, "lib", "cmake", "utf8_range"
        ).replace("\\", "/")
        # protobuf-config.cmake 内部 find_package(absl) —— absl_DIR 同样注入
        tc.variables["absl_DIR"] = os.path.join(
            abseil.package_folder, "lib", "cmake", "absl"
        ).replace("\\", "/")
        tc.variables["PROTOBUF_PREFIX"] = protobuf.package_folder.replace("\\", "/")
        # CMakeDeps 在 test_package graph 中对部分传递依赖（gflags/leveldb 等）
        # 生成的 *_INCLUDE_DIRS_RELEASE 为空（单独 conan install 正常，conan 2.29
        # 传递依赖聚合的边角问题），这里把所有直接依赖的 include 显式加入编译
        # flags 兜底，保证 brpc 公共头（butil/logging.h 等）可解析。
        tc.extra_cxxflags = []
        for dep_name in ("protobuf", "abseil-cpp", "gflags", "leveldb", "snappy"):
            dep = self.dependencies.get(dep_name)
            if dep is None or not getattr(dep, "package_folder", None):
                continue
            inc = os.path.join(dep.package_folder, "include")
            if os.path.isdir(inc):
                tc.extra_cxxflags.append("-I{}".format(inc.replace("\\", "/")))
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # L0d/R34: 显式执行测试二进制并校验退出码。
        # 环境：test_brpc 依赖工具链 libc++_shared.so 与制品仓各动态库
        # （libabsl_*.so/libgflags.so/libleveldb.so），conanbuild 作用域已含
        # 依赖 lib 目录（conanbuild 聚合）与我们在 generate() 里前置的
        # 工具链 libc++ 目录（test_brpc_protoc_env 脚本，scope=build）。
        cmd = os.path.join(self.cpp.build.bindirs[0], "test_brpc").replace("\\", "/")
        self.run(cmd, env="conanbuild")
        self.output.info("brpc RPC roundtrip test passed")
