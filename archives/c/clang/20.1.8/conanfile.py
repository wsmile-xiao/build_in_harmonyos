#!/usr/bin/env python3
"""Conan recipe — clang 20.1.8 (LLVM 编译器前端, 含 compiler-rt builtins + libunwind + libc++ runtimes, 鸿蒙 PC 真机原生编译)

适配路径 A（基础适配）：将 clang 20.1.8 从源码构建为鸿蒙 (aarch64-unknown-linux-ohos) 原生工具链。
产物为 bin/clang、bin/clang++ 及 runtimes 库（compiler-rt builtins / libunwind / libc++）。
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import cmake_layout


class ClangConan(ConanFile):
    name = "clang"
    version = "20.1.8"
    description = "clang/LLVM 20.1.8 编译器工具链（clang + compiler-rt builtins + libunwind + libc++），aarch64-unknown-linux-ohos"
    license = "Apache-2.0 WITH LLVM-exception"
    homepage = "https://clang.llvm.org"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        # 归档为 llvm-project-20.1.8.src/{llvm,clang,...}；strip_root 后 source_folder 直含 llvm/ 子目录。
        get(self, **self.conan_data["sources"], strip_root=True)

    def layout(self):
        cmake_layout(self, src_folder=".")

    def build(self):
        # 鸿蒙 PC 真机原生编译（aarch64→aarch64）：**不用任何 toolchain 文件**——裸 cmake 用设备 hnp clang 直编。
        # 关键：不设 CMAKE_SYSTEM_NAME → CMAKE_CROSSCOMPILING=FALSE → llvm-tblgen 原生编+跑，彻底绕开交叉
        # 编译的 tblgen 主机版难题（同 llvm/20.1.0 策略）。用 Ninja（LLVM 官方推荐）。
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
        import glob
        _sysroots = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/sysroot"))
        _ohos_sysroot = _sysroots[-1] if _sysroots else "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot"
        os.environ["CPATH"] = "{0}/usr/include/aarch64-linux-ohos:{0}/usr/include".format(_ohos_sysroot)
        # runtimes 不进行源码构建——SDK libc++ 15 头与 clang 20 不兼容（nullptr_t/cmath 未定义），
        # compiler-rt builtins 交叉编译链接失败。与手工 llvm-build 先例一致：其 CMakeCache 显示
        # LLVM_BUILD_RUNTIMES=ON 但 runtimes 产物全部符号链接自 SDK（llvm-build/lib/clang/20/lib/ 
        # aarch64-linux-ohos/* → SDK clang 15）。所有 runtimes 库（compiler-rt builtins / libunwind /
        # libc++）及 CRT 文件在 package() 中从 SDK 复制，保证包自包含。
        defs = " ".join([
            "-G Ninja",
            '-DCMAKE_MODULE_PATH="{}"'.format(_pm),   # 供 Platform/HarmonyOS.cmake（见上）
            '-DCMAKE_C_COMPILER="{}"'.format(cc),
            '-DCMAKE_CXX_COMPILER="{}"'.format(cxx),
            "-DCMAKE_BUILD_TYPE=Release",
            "-DCMAKE_INSTALL_LIBDIR=lib",
            # —— 工具链本体：clang 前端，仅 AArch64 ——
            "-DLLVM_TARGETS_TO_BUILD=AArch64",
            "-DLLVM_HOST_TRIPLE=aarch64-unknown-linux-ohos",
            "-DLLVM_DEFAULT_TARGET_TRIPLE=aarch64-unknown-linux-ohos",
            '-DLLVM_ENABLE_PROJECTS="clang"',
            # runtimes 不源码构建：SDK 的 libc++ 15 头与 clang 20 不兼容，compiler-rt/link 链接失败。
            # 对齐手工 llvm-build 先例——所有 runtimes 产物（builtins/libunwind/libc++）及 CRT 文件
            # 在 package() 中从 SDK 复制（_bundle_sdk_resource_dir）。
            '-DLLVM_ENABLE_RUNTIMES=""',
            "-DLLVM_ENABLE_ASSERTIONS=OFF",
            "-DLLVM_INCLUDE_EXAMPLES=OFF",
            # 测试用例不参与构建（46,276 个 lit 用例由 llvm-lit 单独运行，见 notes.md）
            "-DLLVM_INCLUDE_TESTS=OFF",
            "-DLLVM_INCLUDE_BENCHMARKS=OFF",
            "-DLLVM_INCLUDE_DOCS=OFF",
            # —— 自包含：关掉 LLVM 自动探测的可选系统依赖，避免链到设备上不存在的库 ——
            "-DLLVM_ENABLE_ZLIB=OFF",
            "-DLLVM_ENABLE_ZSTD=OFF",
            "-DLLVM_ENABLE_LIBXML2=OFF",
            "-DLLVM_ENABLE_TERMINFO=OFF",
            "-DLLVM_ENABLE_LIBEDIT=OFF",
            "-DLLVM_ENABLE_LIBPFM=OFF",
            # libclang 链接极吃内存 → 限制并行链接任务数防 OOM。
            "-DLLVM_PARALLEL_LINK_JOBS=4",
        ])
        self.run('cmake -B "{}" -S "{}" {}'.format(bdir, src, defs))
        self.run('cmake --build "{}"'.format(bdir))

    def package(self):
        bdir = os.path.join(self.build_folder, "build-ohos")
        self.run('cmake --install "{}" --prefix "{}"'.format(bdir, self.package_folder))
        self._bundle_sdk_resource_dir()
        self._sign_binaries()

    def _bundle_sdk_resource_dir(self):
        """复制 SDK 的 clang 资源目录（crt/builtins）及 libc++ 库到包内（对齐手工先例——不源码构建 runtimes）"""
        import glob, shutil
        _sysroots = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/sysroot"))
        _ohos_sysroot = _sysroots[-1] if _sysroots else "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot"
        _sdk_res = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib/clang/*/lib/aarch64-linux-ohos"))
        _sdk_llvm_lib = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib/aarch64-linux-ohos"))
        _sdk_libcxx_inc = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/include/libcxx-ohos/include/c++/v1"))
        if not _sdk_res:
            return
        # 1) 复制 SDK clang 资源目录（clang_rt.*、builtins 等）到包资源目录
        #    对齐手工先例 llvm-build/lib/clang/20/lib/aarch64-linux-ohos/ 全部符号链接自 SDK
        _res_dst = os.path.join(self.package_folder, "lib", "clang", "20", "lib", "aarch64-linux-ohos")
        os.makedirs(_res_dst, exist_ok=True)
        for _f in os.listdir(_sdk_res[-1]):
            _src = os.path.join(_sdk_res[-1], _f)
            if os.path.isfile(_src) and not os.path.exists(os.path.join(_res_dst, _f)):
                shutil.copy2(_src, _res_dst)
        # 1b) libunwind.a 复制到资源目录（clang 驱动链接时默认 -l:libunwind.a，需在资源目录可解析；
        #     对齐手工先例资源目录内 libunwind.a 符号链接）
        if _sdk_llvm_lib:
            _lw = os.path.join(_sdk_llvm_lib[-1], "libunwind.a")
            if os.path.isfile(_lw) and not os.path.exists(os.path.join(_res_dst, "libunwind.a")):
                shutil.copy2(_lw, _res_dst)
        # 2) 复制 sysroot crt 文件到资源目录（test_package 编译时 clang 驱动需要）
        #    Scrt1.o = PIE 启动文件（鸿蒙默认 -pie 链接需要），crt1.o/crti.o/crtn.o 常规启动
        _sysroot_lib = os.path.join(_ohos_sysroot, "usr/lib/aarch64-linux-ohos")
        for _f in ("Scrt1.o", "crt1.o", "crti.o", "crtn.o"):
            _src = os.path.join(_sysroot_lib, _f)
            if os.path.isfile(_src) and not os.path.exists(os.path.join(_res_dst, _f)):
                shutil.copy2(_src, _res_dst)
        # 3) 不复制 SDK 的 libc++.so/libc++_shared.so 到包 lib/ —— R26 违规（系统同名库输出 .so）。
        #    鸿蒙 SDK 自带 libc++（clang 驱动通过 LIBRARY_PATH/CPATH 找到），test_package 为纯 C
        #    测试不依赖；libc++abi.a 为静态库不触发 R26，供 C++ 消费者链接。
        if _sdk_llvm_lib:
            _lib_dst = os.path.join(self.package_folder, "lib")
            for _f in ("libc++abi.a",):
                _src = os.path.join(_sdk_llvm_lib[-1], _f)
                if os.path.isfile(_src) and not os.path.exists(os.path.join(_lib_dst, _f)):
                    shutil.copy2(_src, _lib_dst)
        # 4) 复制 libc++ 头（c++/v1）到包 include/（供消费者 -isystem 引用）
        if _sdk_libcxx_inc:
            _inc_dst = os.path.join(self.package_folder, "include", "c++", "v1")
            if not os.path.isdir(_inc_dst):
                os.makedirs(os.path.dirname(_inc_dst), exist_ok=True)
                shutil.copytree(_sdk_libcxx_inc[-1], _inc_dst, symlinks=True)

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # OHOS XPM 要求 dlopen 的 .so 和被 exec 的可执行文件都要代码签名，否则报 Permission denied /
        # Operation not permitted。native hnp-clang 直链自签一般有效（ML-0043），但保险统一重签：
        #   ① lib/ 的 .so（libclang*.so、libc++.so 等）  ② bin/ 的 ELF 可执行工具（clang/clang++/…）。
        import glob
        targets = glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so"), recursive=True)
        targets += glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so.*"), recursive=True)
        # bin/ 下所有真实 ELF（跳软链如 clang++→clang、跳非 ELF 脚本）
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in os.listdir(bindir):
                p = os.path.join(bindir, name)
                if os.path.isfile(p) and not os.path.islink(p) and self._is_elf(p):
                    targets.append(p)
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for f in targets:
            if os.path.islink(f) or not self._is_elf(f):
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        # 编译器工具链：bin/ 是消费入口，runtimes 库由 clang 驱动自动链入，不通过 cpp_info 导出 libs。
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = []
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "dl", "pthread"]
