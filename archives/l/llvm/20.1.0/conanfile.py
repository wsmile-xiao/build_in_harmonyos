#!/usr/bin/env python3
"""Conan recipe — llvm 20.1.0 (cmake, 鸿蒙 PC 真机原生编译)"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches
from conan.tools.cmake import cmake_layout


class LlvmConan(ConanFile):
    name = "llvm"
    version = "20.1.0"
    description = "LLVM 编译器基础库（libLLVM.so + 组件库 + 工具 + cmake 导出），AArch64 后端，RTTI 开"
    license = "Apache-2.0 WITH LLVM-exception"
    homepage = "https://llvm.org"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def source(self):
        # 归档为 llvm-project-20.1.0.src/{llvm,clang,...}；strip_root 后 source_folder 直含 llvm/ 子目录。
        get(self, **self.conan_data["sources"], strip_root=True)

    def layout(self):
        cmake_layout(self, src_folder=".")

    def build(self):
        # 鸿蒙 PC 真机原生编译（aarch64→aarch64）：**不用任何 toolchain 文件**——裸 cmake 用设备 hnp clang 直编。
        # 关键：不设 CMAKE_SYSTEM_NAME → CMAKE_CROSSCOMPILING=FALSE → llvm-tblgen 原生编+跑，彻底绕开交叉
        # 编译的 tblgen 主机版难题（这正是选择真机原生而非交叉的核心收益）。用 Ninja（LLVM 官方推荐，比 make 快省内存）。
        apply_conandata_patches(self)
        src = os.path.join(self.source_folder, "llvm")   # CMakeLists 在 llvm/ 子目录
        bdir = os.path.join(self.build_folder, "build-ohos")
        # LLVM 的 config.guess 不认设备 `uname -s = HarmonyOS` → get_host_triple 跑 config.guess 非零退出
        # FATAL（config-ix.cmake 无条件调用它，-DLLVM_HOST_TRIPLE 挡不住）。用 stub 覆盖 config.guess 直接
        # 输出 ohos 三元组（设备 clang 的 target 即 aarch64-unknown-linux-ohos，LLVM 20 认 ohos 环境）。
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
            # —— 通用库该有的 ——
            "-DLLVM_BUILD_LLVM_DYLIB=ON",          # 出 libLLVM.so（聚合动态库）
            "-DLLVM_LINK_LLVM_DYLIB=ON",           # 工具/消费方链 libLLVM.so 而非静态组件库：90 个工具从各
                                                   # ~60MB 静态内嵌降到 ~MB 级（bin/ 892MB→~几十MB），制品体积大降，
                                                   # 绕过制品仓单文件上限（408MB conan_package.tgz 曾被 413 拒）。
            "-DLLVM_ENABLE_RTTI=ON",               # llvmlite 必需，通用也常用（默认 OFF）
            "-DLLVM_ENABLE_PIC=ON",
            "-DLLVM_BUILD_TOOLS=ON",               # llvm-config 等工具（下游必需）
            "-DLLVM_INSTALL_UTILS=ON",             # FileCheck/count/not 等（下游测试常用）
            # —— 瘦身：仅 AArch64、无附加 project、无 tests/examples/benchmarks/docs ——
            "-DLLVM_TARGETS_TO_BUILD=AArch64",
            "-DLLVM_HOST_TRIPLE=aarch64-unknown-linux-ohos",
            "-DLLVM_DEFAULT_TARGET_TRIPLE=aarch64-unknown-linux-ohos",
            '-DLLVM_ENABLE_PROJECTS=""',
            '-DLLVM_ENABLE_RUNTIMES=""',
            "-DLLVM_ENABLE_ASSERTIONS=OFF",
            "-DLLVM_INCLUDE_EXAMPLES=OFF",
            "-DLLVM_INCLUDE_TESTS=OFF",
            "-DLLVM_INCLUDE_BENCHMARKS=OFF",
            "-DLLVM_INCLUDE_DOCS=OFF",
            # —— 自包含：关掉 LLVM 会自动探测的可选系统依赖，避免链到设备上不存在的库 ——
            "-DLLVM_ENABLE_ZLIB=OFF",
            "-DLLVM_ENABLE_ZSTD=OFF",
            "-DLLVM_ENABLE_LIBXML2=OFF",
            "-DLLVM_ENABLE_TERMINFO=OFF",
            "-DLLVM_ENABLE_LIBEDIT=OFF",
            "-DLLVM_ENABLE_LIBPFM=OFF",
            # libLLVM.so 链接极吃内存 → 限制并行链接任务数防 OOM（32GB/20 核，编译仍全并行）。
            "-DLLVM_PARALLEL_LINK_JOBS=4",
        ])
        self.run('cmake -B "{}" -S "{}" {}'.format(bdir, src, defs))
        self.run('cmake --build "{}"'.format(bdir))

    def package(self):
        bdir = os.path.join(self.build_folder, "build-ohos")
        self.run('cmake --install "{}" --prefix "{}"'.format(bdir, self.package_folder))
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # OHOS XPM 要求 dlopen 的 .so 和被 exec 的可执行文件都要代码签名，否则报 Permission denied /
        # Operation not permitted。native hnp-clang 直链自签一般有效（ML-0043），但保险统一重签：
        #   ① lib/ 的 .so（libLLVM.so 等）  ② bin/ 的 ELF 可执行工具（llvm-config/llc/opt/FileCheck…）。
        import glob
        targets = glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so"), recursive=True)
        targets += glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so.*"), recursive=True)
        # bin/ 下所有真实 ELF（跳软链如 llvm-ranlib→llvm-ar、跳非 ELF 脚本）
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in os.listdir(bindir):
                p = os.path.join(bindir, name)
                if os.path.isfile(p) and not os.path.islink(p) and self._is_elf(p):
                    targets.append(p)
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for f in targets:
            if os.path.islink(f):
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        # LLVM 自带完整的 lib/cmake/llvm/LLVMConfig.cmake（组件依赖图 + llvm_map_components_to_libnames）。
        # 让消费方走 LLVM 自己的 config（cmake_find_mode=none），把 config 目录挂到 builddirs 供 CMAKE_PREFIX_PATH。
        self.cpp_info.set_property("cmake_file_name", "LLVM")
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = ["lib/cmake/llvm"]
        self.cpp_info.libs = ["LLVM"]              # libLLVM.so（聚合动态库）；组件静态库经 LLVM config 消费
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "dl", "pthread"]
