#!/usr/bin/env python3
"""Conan recipe — llvm 15.0.4 (cmake, 鸿蒙 PC 真机原生编译, 静态组件版)

本 recipe 为 AdaptiveCpp 25.10.0 提供 LLVM 15.0.4 AArch64 OHOS 静态开发包：
完整 libLLVM*.a / libclang*.a + LLVMConfig/LLVMExports/ClangTargets CMake 导出。
未执行构建（本轮仅 scaffold），所有参数均基于 R4/R6/R7 只读证据与 llvm/20.1.0
共享方案差异整理，未经 conan create 验证。
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches
from conan.tools.cmake import cmake_layout


class LlvmConan(ConanFile):
    name = "llvm"
    version = "15.0.4"
    description = "LLVM 15.0.4 静态组件库（libLLVM*.a + libclang*.a + CMake 导出），AArch64，供 AdaptiveCpp 等消费方静态链接"
    license = "Apache-2.0 WITH LLVM-exception"
    homepage = "https://llvm.org"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def export_sources(self):
        # 本配方源码全部来自 conandata.yml 官方归档（source() 经 get() 下载并 strip_root），
        # conandata.yml 的 patches 段为空（无本地补丁文件），故无本地文件需导出。
        # 保留该方法以满足 conan-verify G1 配方完整性门禁。
        pass

    def source(self):
        # 归档为 llvm-project-15.0.4.src/{llvm,clang,...}；strip_root 后 source_folder 直含 llvm/ 子目录。
        get(self, **self.conan_data["sources"], strip_root=True)

    def layout(self):
        cmake_layout(self, src_folder=".")

    def build(self):
        # 鸿蒙 PC 真机原生编译（aarch64→aarch64）：不设 CMAKE_SYSTEM_NAME → CMAKE_CROSSCOMPILING=FALSE
        # → llvm-tblgen 原生编+跑，彻底绕开 host tablegen 缺口（R7 证据，同 20.1.0 方案）。
        # 静态组件目标：BUILD_SHARED_LIBS=OFF + LLVM_BUILD_LLVM_DYLIB=OFF + LLVM_LINK_LLVM_DYLIB=OFF
        # → 产出完整 libLLVM*.a/libclang*.a 与 LLVMConfig/LLVMExports/ClangTargets 导出。
        # 与 20.1.0 差异：20.1.0 为共享（LLVM_BUILD_LLVM_DYLIB=ON + LLVM_LINK_LLVM_DYLIB=ON）；本版静态化。
        apply_conandata_patches(self)
        src = os.path.join(self.source_folder, "llvm")   # CMakeLists 在 llvm/ 子目录
        bdir = os.path.join(self.build_folder, "build-ohos")
        # LLVM 的 config.guess 不认设备 `uname -s = HarmonyOS` → get_host_triple 跑 config.guess 非零退出
        # FATAL（config-ix.cmake 无条件调用它，-DLLVM_HOST_TRIPLE 挡不住）。用 stub 覆盖 config.guess
        # 直接输出 ohos 三元组（设备 clang 的 target 即 aarch64-unknown-linux-ohos）。
        _cg = os.path.join(src, "cmake", "config.guess")
        with open(_cg, "w", encoding="utf-8") as _f:
            _f.write("#!/bin/sh\necho aarch64-unknown-linux-ohos\n")
        # 设备 uname -s=HarmonyOS，cmake 无 Platform/HarmonyOS 模块 → UNIX 变量未置 → LLVM 判 UNIX 为假
        # → HandleLLVMOptions "Unable to determine platform" FATAL。提供 Platform/HarmonyOS.cmake（复用
        # Platform/Linux：置 UNIX=1 + Linux 链接/rpath 规则）挂到 CMAKE_MODULE_PATH。保持 native——不设
        # CMAKE_SYSTEM_NAME → 不触发 CMAKE_CROSSCOMPILING → llvm-tblgen 仍原生编+跑。
        _pm = os.path.join(self.build_folder, "_cmake_modules")
        os.makedirs(os.path.join(_pm, "Platform"), exist_ok=True)
        with open(os.path.join(_pm, "Platform", "HarmonyOS.cmake"), "w", encoding="utf-8") as _f:
            _f.write("include(Platform/Linux)\n")
        cc = "/data/service/hnp/bin/clang"
        cxx = "/data/service/hnp/bin/clang++"
        defs = " ".join([
            "-G Ninja",
            '-DCMAKE_MODULE_PATH="{}"'.format(_pm),   # 供 Platform/HarmonyOS.cmake（见上）
            '-DCMAKE_C_COMPILER="{}"'.format(cc),
            '-DCMAKE_CXX_COMPILER="{}"'.format(cxx),
            "-DCMAKE_BUILD_TYPE=Release",
            "-DCMAKE_INSTALL_LIBDIR=lib",
            # —— 静态组件目标（区别于 20.1.0 共享方案）——
            "-DBUILD_SHARED_LIBS=OFF",           # 全部静态组件库
            "-DLLVM_BUILD_LLVM_DYLIB=ON",        # mixed：出 libLLVM.so 聚合动态库（R35 已证 AdaptiveCpp full profile 硬性要求）
            "-DLLVM_LINK_LLVM_DYLIB=OFF",        # 工具静态链组件（R38 已证 LLVM_LINK_LLVM_DYLIB=ON 致工具 dylib 链接 20 个 undefined symbol）
            "-DLLVM_ENABLE_RTTI=ON",             # AdaptiveCpp/通用 RTTI 依赖
            "-DLLVM_ENABLE_PIC=ON",
            "-DLLVM_BUILD_TOOLS=ON",             # llvm-config 等工具（消费方必需）
            "-DLLVM_INSTALL_UTILS=ON",           # FileCheck/count/not 等（下游测试常用）
            # —— 目标架构与 triple ——
            "-DLLVM_TARGETS_TO_BUILD=AArch64",
            "-DLLVM_HOST_TRIPLE=aarch64-unknown-linux-ohos",
            "-DLLVM_DEFAULT_TARGET_TRIPLE=aarch64-unknown-linux-ohos",
            '-DLLVM_ENABLE_PROJECTS="clang"',    # AdaptiveCpp 需要 Clang 组件与 ClangTargets 导出
            '-DLLVM_ENABLE_RUNTIMES=""',
            "-DLLVM_ENABLE_ASSERTIONS=OFF",
            "-DLLVM_INCLUDE_EXAMPLES=OFF",
            "-DLLVM_INCLUDE_TESTS=OFF",
            "-DLLVM_INCLUDE_BENCHMARKS=OFF",
            "-DLLVM_INCLUDE_DOCS=OFF",
            # —— 自包含：关闭 LLVM 会自动探测的可选系统依赖（R4 已证 host 侧 zlib/zstd/libxml2/terminfo
            #    开发头缺失），避免链到设备上不存在的库；显式关闭不吞错 ——
            "-DLLVM_ENABLE_ZLIB=OFF",
            "-DLLVM_ENABLE_ZSTD=OFF",
            "-DLLVM_ENABLE_LIBXML2=OFF",
            "-DLLVM_ENABLE_TERMINFO=OFF",
            "-DLLVM_ENABLE_LIBEDIT=OFF",
            "-DLLVM_ENABLE_LIBPFM=OFF",
            # 静态链接/归档吃内存（R4 实测空闲仅约 2.3~3GB）→ 限并行链接任务数防 OOM，编译仍全并行。
            "-DLLVM_PARALLEL_LINK_JOBS=2",
        ])
        self.run('cmake -B "{}" -S "{}" {}'.format(bdir, src, defs))
        self.run('cmake --build "{}"'.format(bdir))

    def package(self):
        bdir = os.path.join(self.build_folder, "build-ohos")
        self.run('cmake --install "{}" --prefix "{}"'.format(bdir, self.package_folder))
        # 静态库 .a 无需 codesign（sign-elf 只针对可执行 ELF 与 dlopen 的 .so）；bin/ 下可执行工具
        # （llvm-config/FileCheck/count/not 等）若被后续测试 exec，需签名。仅保留逻辑，本轮未运行。
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # OHOS XPM 要求被 exec 的可执行文件代码签名（sign-elf，§3.3）。静态包以 .a 为主，但 bin/ 工具
        # 为 ELF 可执行，后续验收若执行须签名。本轮不执行，仅保留逻辑供授权构建轮使用。
        import glob
        targets = []
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in os.listdir(bindir):
                p = os.path.join(bindir, name)
                if os.path.isfile(p) and not os.path.islink(p) and self._is_elf(p):
                    targets.append(p)
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for f in targets:
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        # LLVM 自带完整的 lib/cmake/llvm/LLVMConfig.cmake（组件依赖图 + llvm_map_components_to_libnames）
        # 与 lib/cmake/clang/ClangTargets.cmake。让消费方走 LLVM/Clang 自己的 config
        # （cmake_find_mode=none），把 config 目录挂到 builddirs 供 CMAKE_PREFIX_PATH。
        self.cpp_info.set_property("cmake_file_name", "LLVM")
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = ["lib/cmake/llvm", "lib/cmake/clang"]
        # 静态包无聚合 libLLVM.so；组件解析由 LLVMConfig.cmake 的 llvm_map_components_to_libnames 主导，
        # 故 libs 留空并由消费方 CMake 经 find_package(LLVM CONFIG) 引用具体组件。
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "dl", "pthread"]
