#!/usr/bin/env python3
"""Conan recipe — srpc 0.10.4 (CMake).

srpc（搜狗 RPC 框架）是基于 Sogou C++ Workflow 的高性能 RPC 框架，支持
SRPC / 百度 bRPC / 腾讯 tRPC / thrift 四种协议以及 HTTP 服务。
本配方适配 HarmonyOS PC（aarch64, musl, clang 15, libc++）。

适配要点：
- 依赖全部来自制品仓：workflow/1.1.0（C++ 异步引擎，本仓已适配）、
  protobuf/3.17.3（protoc + libprotobuf）、openssl/3.5.6、snappy/1.2.2、
  lz4/1.10.0、zlib/1.3.1（gzip/zlib 压缩器）。protobuf 选 3.17.3 而非
  33.x：上游 src/CMakeLists.txt 硬编码 `-std=c++14`（追加在 conan 注入的
  -std=c++17 之后，优先生效），protobuf ≥ 4.22 生成的 .pb.cc 依赖 abseil，
  需要 C++17 才能编译，二者不兼容。
- 上游 CMakeLists.txt 用 check_include_file/check_include_file_cxx/
  find_library/find_path 做依赖探测（workflow/Workflow.h、snappy.h、lz4.h、
  protoc），并把结果存进缓存变量决定编译分支；这些探测不吃 conan 的
  CMakeDeps config，因此配方显式注入 CMAKE_REQUIRED_INCLUDES /
  CMAKE_REQUIRED_FLAGS / CMAKE_INCLUDE_PATH / CMAKE_LIBRARY_PATH /
  CMAKE_*_FLAGS_INIT（-I/-L）以及 WORKFLOW_INCLUDE_DIR、PROTOC，
  避免改动上游构建文件。
- E092：CMake 无 HarmonyOS 平台模块，OHOS 内核为 Linux，强制
  CMAKE_SYSTEM_NAME=Linux，使上游 `__linux__` 分支（epoll/eventfd 由
  workflow 提供）与 -std=gnu90 的 C 代码路径生效。
- 上游构建产出 libsrpc.a（静态）+ libsrpc.so（共享，带 SONAME
  libsrpc.so.0）以及 protoc 插件 srpc_generator；共享库在 OHOS 上需
  签名后分发（同 workflow/brpc 配方）。
- 上游测试（test/，ctest 注册 unittest/var_unittest 两套 gtest 套件）
  在 build() 中全量构建并运行：unittest 走 127.0.0.1 回环 RPC、压缩
  （gzip/zlib/snappy/lz4）、thrift/brpc/trpc 协议编解码，无需外网。
"""

import glob
import json
import os
import re
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class SrpcConan(ConanFile):
    name = "srpc"
    version = "0.10.4"
    description = (
        "Sogou RPC framework based on C++ Workflow "
        "(SRPC / bRPC / tRPC / thrift protocols over an asynchronous network engine)"
    )
    license = "Apache-2.0"
    homepage = "https://github.com/sogou/srpc"
    url = "https://github.com/sogou/srpc"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    # 上游 src/CMakeLists.txt 恒定同时产出 libsrpc.a（-static）与
    # libsrpc.so（-shared，带 SONAME），`shared` 仅用于 conan 包标识与
    # package_type 语义，不影响上游构建分支。
    options = {"shared": [True, False], "run_upstream_tests": [True, False]}
    default_options = {"shared": True, "run_upstream_tests": True}

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("srpc supports Linux and OHOS targets")

    def validate(self):
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("srpc supports OHOS armv8 only")

    def requirements(self):
        # srpc 公共头直接 include workflow / protobuf / openssl / snappy /
        # lz4 / zlib 头文件（rpc_define.h、rpc_compress_lz4.h 等），消费者
        # 编译期必须可见 → transitive_headers。
        self.requires("workflow/1.1.0", transitive_headers=True)
        self.requires("protobuf/3.17.3", transitive_headers=True)
        self.requires("openssl/3.5.6", transitive_headers=True)
        self.requires("snappy/1.2.2", transitive_headers=True)
        self.requires("lz4/1.10.0", transitive_headers=True)
        self.requires("zlib/1.3.1", transitive_headers=True)

    def build_requirements(self):
        if self.options.run_upstream_tests:
            self.test_requires("gtest/1.17.0")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Bazel 的 BUILD/WORKSPACE 与 conan cmake_layout 的 build/ 目录在
        # 大小写不敏感文件系统（HMDFS/APFS）上同名冲突
        # （NotADirectoryError: b/build/Release）。本配方与 CI 都走 CMake，
        # 不使用 Bazel，删除这两个文件（同 workflow 配方）。
        for name in ("BUILD", "WORKSPACE"):
            path = os.path.join(self.source_folder, name)
            if os.path.isfile(path):
                os.remove(path)

    # ── helpers ──────────────────────────────────────────────────────────

    def _dep_dirs(self):
        """返回 (include_dirs, lib_dirs, prefixes) —— 全部依赖的绝对目录。"""
        inc_dirs, lib_dirs, prefixes = [], [], []
        for dep in self.dependencies.values():
            package_folder = dep.package_folder
            if not package_folder:
                continue
            prefixes.append(package_folder.replace("\\", "/"))
            for inc in dep.cpp_info.includedirs:
                inc_dirs.append(os.path.join(package_folder, inc).replace("\\", "/"))
            for lib in dep.cpp_info.libdirs:
                lib_dirs.append(os.path.join(package_folder, lib).replace("\\", "/"))
        return inc_dirs, lib_dirs, prefixes

    def _dep_dir(self, name, attr, index=0):
        dep = self.dependencies[name]
        values = getattr(dep.cpp_info, attr)
        return os.path.join(dep.package_folder, values[index]).replace("\\", "/")

    def _cc(self):
        compilers = self.conf.get("tools.build:compiler_executables", {}) or {}
        return compilers.get("c", "clang")

    def _cxx(self):
        compilers = self.conf.get("tools.build:compiler_executables", {}) or {}
        return compilers.get("cpp", "clang++")

    def _toolchain_libcpp_dir(self):
        """工具链 libc++_shared.so 目录（测试二进制运行期需要）。"""
        cxx = self._cxx()
        if not cxx:
            return ""
        real = os.path.realpath(cxx)
        candidates = [
            os.path.join(os.path.dirname(os.path.dirname(real)), "lib", "aarch64-linux-ohos"),
        ]
        candidates += glob.glob(
            "/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib/aarch64-linux-ohos"
        )
        for cand in candidates:
            if os.path.isfile(os.path.join(cand, "libc++_shared.so")):
                return cand
        return ""

    # ── generate ─────────────────────────────────────────────────────────

    def generate(self):
        inc_dirs, lib_dirs, prefixes = self._dep_dirs()
        # 依赖导出的编译宏必须显式带入：srpc 不用 conan 的 CMakeDeps 目标，
        # 直接编译源码，因此 workflow 导出的 WORKFLOW_USE_THREAD_IOSERVICE
        # （OHOS 上 IOService 头文件/类布局选择，见 workflow 配方）不会自动
        # 生效，缺它 Communicator.h 会去 include 不存在的 IOService_linux.h。
        dep_defines = []
        for dep in self.dependencies.values():
            dep_defines.extend(dep.cpp_info.defines)
        define_flags = " ".join("-D" + d for d in dep_defines)
        lib_flags = " ".join("-L" + d for d in lib_dirs)

        inc_flags = " ".join("-I" + d for d in inc_dirs)
        if define_flags:
            inc_flags = inc_flags + " " + define_flags
        lib_flags = " ".join("-L" + d for d in lib_dirs)

        tc = CMakeToolchain(self)
        # E092: OHOS 内核为 Linux，强制走上游 __linux__ 分支。
        if str(self.settings.os) == "OHOS":
            tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"

        # 上游用 module 模式探测（check_include_file*/find_path/find_library）
        # 与源码内裸 include（lz4.h/snappy.h/zlib.h），两处都要可见。
        tc.variables["CMAKE_REQUIRED_INCLUDES"] = ";".join(inc_dirs)
        tc.variables["CMAKE_REQUIRED_FLAGS"] = inc_flags
        tc.variables["CMAKE_INCLUDE_PATH"] = ";".join(inc_dirs)
        tc.variables["CMAKE_LIBRARY_PATH"] = ";".join(lib_dirs)
        tc.variables["CMAKE_C_FLAGS_INIT"] = inc_flags
        tc.variables["CMAKE_CXX_FLAGS_INIT"] = inc_flags
        for var in (
            "CMAKE_EXE_LINKER_FLAGS_INIT",
            "CMAKE_SHARED_LINKER_FLAGS_INIT",
            "CMAKE_MODULE_LINKER_FLAGS_INIT",
        ):
            tc.variables[var] = lib_flags
        tc.variables["CMAKE_PREFIX_PATH"] = ";".join(prefixes)

        # 上游 CMakeLists.txt 在“workflow 已安装”分支不会设置
        # WORKFLOW_INCLUDE_DIR（只有 third_party 分支设置），而 src/CMakeLists.txt
        # 依赖它做 include_directories；这里显式补齐。
        tc.variables["WORKFLOW_INCLUDE_DIR"] = self._dep_dir("workflow", "includedirs")
        # find_program(PROTOC "protoc") + 上游 message 提示：直接给绝对路径。
        protoc = os.path.join(
            self.dependencies["protobuf"].package_folder, "bin", "protoc"
        ).replace("\\", "/")
        tc.variables["PROTOC"] = protoc
        tc.variables["Protobuf_PROTOC_EXECUTABLE"] = protoc
        tc.generate()

        CMakeDeps(self).generate()

    # ── build ────────────────────────────────────────────────────────────

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if self.options.run_upstream_tests:
            self._run_upstream_tests()

    def _run_upstream_tests(self):
        """构建并运行上游 test/（ctest 注册 2 套 gtest 套件）。

        上游 test/CMakeLists.txt 是独立 project（find_package(srpc CONFIG
        HINTS ..)），不在主 build 树内，需单独配置一个 test build 树指向已
        安装的 srpc 包；依赖（workflow/protobuf/gtest/openssl）通过
        CMAKE_PREFIX_PATH 暴露。
        """
        CMake(self).install()

        install_prefix = self.package_folder.replace("\\", "/")
        _, _, prefixes = self._dep_dirs()
        prefix_path = ";".join([install_prefix] + prefixes)
        inc_dirs, lib_dirs, _ = self._dep_dirs()

        protobuf = self.dependencies["protobuf"]
        gtest = self.dependencies["gtest"]
        protoc = os.path.join(
            protobuf.package_folder, "bin", "protoc").replace("\\", "/")
        gtest_dir = os.path.join(
            gtest.package_folder, "lib", "cmake", "GTest").replace("\\", "/")
        inc_path = ";".join(inc_dirs)
        lib_path = ";".join(lib_dirs)
        workflow_lib_dir = self._dep_dir("workflow", "libdirs")
        workflow_inc_dir = self._dep_dir("workflow", "includedirs")
        # 上游 test/ 用裸库名链接，依赖导出的编译宏（workflow 在 OHOS 上
        # 需要 WORKFLOW_USE_THREAD_IOSERVICE 选择 IOService 头/类布局）
        # 必须显式带上，否则 Communicator.h 会 include 不存在的
        # IOService_linux.h。
        dep_defines = []
        for dep in self.dependencies.values():
            dep_defines.extend(dep.cpp_info.defines)
        define_flags = " ".join("-D" + d for d in dep_defines)
        lib_flags = " ".join("-L" + d for d in lib_dirs)

        test_src = os.path.join(self.source_folder, "test")
        test_build = os.path.join(self.build_folder, "upstream-tests")
        os.makedirs(test_build, exist_ok=True)

        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        configure_cmd = (
            f'cmake -S "{test_src}" -B "{test_build}" '
            f'-DCMAKE_PREFIX_PATH="{prefix_path}" '
            f'-DCMAKE_INCLUDE_PATH="{inc_path}" '
            f'-DCMAKE_LIBRARY_PATH="{lib_path}" '
            f'-DCMAKE_C_COMPILER="{self._cc()}" '
            f'-DCMAKE_CXX_COMPILER="{self._cxx()}" '
            f'-DCMAKE_C_FLAGS="{define_flags}" '
            f'-DCMAKE_CXX_FLAGS="{define_flags}" '
            f'-DCMAKE_EXE_LINKER_FLAGS="{lib_flags}" '
            f'-DCMAKE_SHARED_LINKER_FLAGS="{lib_flags}" '
            f'-DCMAKE_BUILD_TYPE=RelWithDebInfo '
            f'-DSRPC_LIB_DIR="{install_prefix}/lib" '
            f'-DSRPC_BIN_DIR="{install_prefix}/bin" '
            f'-DWORKFLOW_LIB_DIR="{workflow_lib_dir}" '
            f'-DWORKFLOW_INCLUDE_DIR="{workflow_inc_dir}" '
            f'-DProtobuf_PROTOC_EXECUTABLE="{protoc}" '
            f'-DGTest_DIR="{gtest_dir}"'
        )
        proc = subprocess.run(
            [bash, "-c", configure_cmd], stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, timeout=900)
        if proc.returncode != 0:
            self.output.error(proc.stdout[-4000:])
            raise RuntimeError("upstream test cmake configure failed")

        build_cmd = f'cmake --build "{test_build}" --target unittest var_unittest -- -j{os.cpu_count() or 2}'
        proc = subprocess.run(
            [bash, "-c", build_cmd], stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, timeout=3600)
        if proc.returncode != 0:
            self.output.error(proc.stdout[-4000:])
            raise RuntimeError("upstream test build failed")

        libcpp_dir = self._toolchain_libcpp_dir()
        runtime_dirs = [
            os.path.join(install_prefix, "lib"),
            self._dep_dir("workflow", "libdirs"),
            self._dep_dir("openssl", "libdirs"),
            libcpp_dir,
        ]
        env_prefix = "LD_LIBRARY_PATH=" + ":".join(d for d in runtime_dirs if d)

        declared = 0
        executed = passed = failed = 0
        for suite in ("unittest", "var_unittest"):
            exe = os.path.join(test_build, suite)
            if not os.path.isfile(exe):
                failed += 1
                self.output.error(f"{suite}: binary missing")
                continue
            run = subprocess.run(
                [bash, "-c", f'cd "{test_build}" && {env_prefix} ./{suite}'],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, timeout=1800)
            n_ok = len(re.findall(r"\[       OK \]", run.stdout))
            n_bad = len(re.findall(r"\[  FAILED  \] \w+\.", run.stdout))
            m = re.search(r"\[==========\] (\d+) tests? from", run.stdout)
            if m:
                declared += int(m.group(1))
            executed += n_ok + n_bad
            passed += n_ok
            failed += n_bad
            self.output.info(f"{suite}: exit={run.returncode} ok={n_ok} failed={n_bad}")
            if run.returncode != 0:
                self.output.error(f"=== {suite} tail ===\n{run.stdout[-2500:]}")
                failed += 1

        result = {
            "status": "passed" if failed == 0 and passed > 0 else "failed",
            "framework": "gtest",
            "command": "cmake --build upstream-tests --target unittest var_unittest && ./unittest && ./var_unittest",
            "discovered": declared,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": 0,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, ensure_ascii=False))
        if result["status"] != "passed":
            raise RuntimeError(
                f"upstream tests failed: passed={passed} failed={failed}")

    # ── package ──────────────────────────────────────────────────────────

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self, "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        if str(self.settings.os) == "OHOS":
            self._sign_shared_libraries()

    def _sign_shared_libraries(self):
        """OHOS 上给共享库签名（musl 加载器拒载未签名 ELF）。"""
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        libraries = glob.glob(
            os.path.join(self.package_folder, "lib", "**", "*.so*"), recursive=True
        )
        for library in libraries:
            if os.path.islink(library):
                continue
            if os.path.isfile(objcopy):
                self.run(
                    '{} --remove-section .codesign "{}" 2>/dev/null || true'.format(
                        objcopy, library)
                )
            if os.path.isfile(signer):
                self.run(
                    '{} sign -inFile "{}" -outFile "{}" -selfSign 1'.format(
                        signer, library, library)
                )

    def package_info(self):
        self.cpp_info.libs = ["srpc"]
        self.cpp_info.set_property("cmake_file_name", "srpc")
        self.cpp_info.set_property("cmake_target_name", "srpc::srpc")
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
