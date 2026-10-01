#!/usr/bin/env python3
"""Conan test_package — 消费者视角验证 srpc（R34 实质调用）。

模拟业务上层应用：用 protoc + srpc_generator 由 .proto 生成 RPC 桩代码，
再用 srpc 公开 API（SRPCServer / SRPCClient）跑一次真实的本机 RPC 往返
（同步 + 异步两路），验证「库被别人拿过去能否编译、链接、调用跑通」。
"""

import glob
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class SrpcTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        include_dirs, library_dirs, defines = [], [], []
        for dep in self.dependencies.values():
            package_folder = getattr(dep, "package_folder", None)
            if not package_folder:
                continue
            for inc in dep.cpp_info.includedirs:
                include_dirs.append(os.path.join(package_folder, inc).replace("\\", "/"))
            for lib in dep.cpp_info.libdirs:
                library_dirs.append(os.path.join(package_folder, lib).replace("\\", "/"))
            # 依赖导出的编译宏（workflow 在 OHOS 上需要
            # WORKFLOW_USE_THREAD_IOSERVICE 选择 IOService 头/类布局）。
            # 消费者用裸库名链接，不经过 CMakeDeps 目标，故显式转达。
            defines.extend(dep.cpp_info.defines)

        protobuf = self.dependencies["protobuf"]
        srpc = self.dependencies["srpc"]
        protoc = os.path.join(protobuf.package_folder, "bin", "protoc").replace("\\", "/")
        generator = os.path.join(
            srpc.package_folder, "bin", "srpc_generator").replace("\\", "/")

        tc = CMakeToolchain(self)
        # 被测包安装的 srpc-config.cmake 提供 SRPC_INCLUDE_DIR/LIB_DIR/BIN_DIR
        # （上游 configure_package_config_file 生成），显式指向它，避免与
        # CMakeDeps 生成物同名冲突。
        tc.variables["srpc_DIR"] = os.path.join(
            srpc.package_folder, "lib", "cmake", "srpc").replace("\\", "/")
        tc.variables["PROTOC_EXECUTABLE"] = protoc
        tc.variables["SRPC_GENERATOR"] = generator
        tc.variables["DEP_INCLUDE_DIRS"] = ";".join(include_dirs)
        tc.variables["DEP_LIBRARY_DIRS"] = ";".join(library_dirs)
        tc.variables["DEP_DEFINES"] = ";".join(defines)
        tc.generate()

        # 运行期搜索路径：libsrpc.so / libworkflow.so / libssl+libcrypto /
        # libsnappy.so / liblz4.so / 工具链 libc++_shared.so
        env = Environment()
        for dep in self.dependencies.values():
            package_folder = getattr(dep, "package_folder", None)
            if not package_folder:
                continue
            for lib in dep.cpp_info.libdirs:
                libdir = os.path.join(package_folder, lib)
                if os.path.isdir(libdir):
                    env.prepend_path("LD_LIBRARY_PATH", libdir)
        cxx = str((self.conf.get("tools.build:compiler_executables", {}) or {}).get("cpp", ""))
        if cxx:
            real = os.path.realpath(cxx)
            for cand in [os.path.join(os.path.dirname(os.path.dirname(real)),
                                      "lib", "aarch64-linux-ohos")] + glob.glob(
                    "/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib/aarch64-linux-ohos"):
                if os.path.isfile(os.path.join(cand, "libc++_shared.so")):
                    env.prepend_path("LD_LIBRARY_PATH", cand)
                    break
        env.vars(self, scope="build").save_script("test_srpc_env")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        def find(name):
            hits = glob.glob(os.path.join(self.build_folder, "**", name), recursive=True)
            if not hits:
                raise RuntimeError(f"{name} not built")
            return hits[0]

        server = find("echo_server")
        client = find("echo_client")
        runner = os.path.join(self.source_folder, "run_consumer_test.sh")
        self.run(f'sh "{runner}" "{server}" "{client}"', env="conanbuild")
