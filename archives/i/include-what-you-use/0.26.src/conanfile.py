#!/usr/bin/env python3
"""Conan recipe — include-what-you-use 0.26.src (cmake, 鸿蒙 PC 真机原生编译)

IWYU (include-what-you-use)：C/C++ #include 分析工具。0.26 仅兼容 Clang 22。
standalone 模式构建：find_package(LLVM/Clang CONFIG) 消费 clang/22.1.8 包
（libclang-cpp 动态库 + 真实 cmake config：AddLLVM/HandleLLVMOptions/clang-cpp 目标）。

产物：bin/include-what-you-use（自签名 ELF，RUNPATH=$ORIGIN/../lib）
      bin/fix_includes.py + bin/iwyu_tool.py（官方配套脚本）
      share/include-what-you-use/*.imp（映射）+ share/man/man1/
      lib/clang/22/include（builtin 头，自 clang 包 resource dir 拷入）
      lib/{libclang-cpp.so.22.1,libLLVM.so.22.1,libc++_shared.so}（自 clang 包捆绑，自包含运行时）

OHOS 适配要点（详见 notes.md 问题台账）：
  1. 设备 uname -s=HarmonyOS → LLVM 22 平台表无对应 → Platform/HarmonyOS.cmake（include Platform/Linux）
     经 CMAKE_MODULE_PATH 注入；不设 CMAKE_SYSTEM_NAME（保 CMAKE_CROSSCOMPILING=FALSE，llvm/clang 配方同款）。
  2. OHOS XPM：bin/ ELF 与 lib/ .so 均须代码签名（objcopy 去 .codesign + binary-sign-tool 自签，llvm/clang 配方同款）。
  3. 二进制 NEEDED libclang-cpp.so.22.1/libLLVM.so.22.1/libc++_shared.so 自 clang 包拷入包内 lib/，
     配合 CMAKE_INSTALL_RPATH=$ORIGIN/../lib 构成自包含运行时（无跨包 RPATH 依赖）。
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class IwyuConan(ConanFile):
    name = "include-what-you-use"
    version = "0.26.src"
    description = ("include-what-you-use (IWYU) C/C++ #include 分析工具"
                   "（基于 Clang 22 前端）：分析源文件头文件依赖，输出增删建议并可配合 fix_includes.py 改写")
    license = "Apache-2.0"
    homepage = "https://include-what-you-use.org"
    url = "https://github.com/include-what-you-use/include-what-you-use"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # W0 核验：7 依赖均已在 ohpcd 制品仓（conan download 实测 rc=0）
        self.requires("clang/22.1.8")      # 核心：LLVM/Clang 一体包（cmake config + libclang-cpp + resource dir）
        self.requires("llvm/22.1.0")       # LLVMConfig 提供方（与 clang 包同源 22 代）
        self.requires("zlib/1.3.2")
        self.requires("zstd/1.5.7")
        self.requires("xz/5.8.3.1")
        self.requires("libedit/20240808")
        self.requires("z3/4.15.4")

    def layout(self):
        from conan.tools.cmake import cmake_layout
        cmake_layout(self, src_folder=".")

    def source(self):
        # 官方 tag 0.26 归档（codeload = GitHub 官方归档后端；release 资产链设备不可达，实测见 notes.md）
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        bdir = os.path.join(self.build_folder, "build-ohos")
        clang_pkg = self.dependencies["clang"].package_folder
        # —— 平台模块：设备 uname -s=HarmonyOS，LLVM 22 无 Platform/HarmonyOS.cmake → 复用 Platform/Linux ——
        _pm = os.path.join(self.build_folder, "_cmake_modules")
        os.makedirs(os.path.join(_pm, "Platform"), exist_ok=True)
        with open(os.path.join(_pm, "Platform", "HarmonyOS.cmake"), "w", encoding="utf-8") as _f:
            _f.write("include(Platform/Linux)\n")
        defs = " ".join([
            '-DCMAKE_MODULE_PATH="{}"'.format(_pm),
            # 鸿蒙 PC 真机原生编译（aarch64→aarch64）：设备 hnp clang 直编（llvm/clang 配方同款），不设
            # CMAKE_SYSTEM_NAME → CMAKE_CROSSCOMPILING=FALSE
            '-DCMAKE_C_COMPILER="/data/service/hnp/bin/clang"',
            '-DCMAKE_CXX_COMPILER="/data/service/hnp/bin/clang++"',
            "-DCMAKE_BUILD_TYPE=Release",
            "-DCMAKE_INSTALL_LIBDIR=lib",
            # —— IWYU standalone 模式：消费 clang 包真实 cmake config（CMakeDeps 合成版无 AddLLVM/clang-cpp 目标）——
            '-DLLVM_DIR="{}"'.format(os.path.join(clang_pkg, "lib", "cmake", "llvm")),
            '-DClang_DIR="{}"'.format(os.path.join(clang_pkg, "lib", "cmake", "clang")),
            # —— builtin 头：iwyu 运行时相对自身（bin/ → ../lib/clang/22/include）解析 resource dir ——
            "-DIWYU_RESOURCE_RELATIVE_TO=iwyu",
            "-DIWYU_RESOURCE_DIR=../lib/clang/22",
            # —— 运行时自包含：安装后 RUNPATH=$ORIGIN/../lib → 包内 lib/（package() 捆绑所需 .so）——
            '-DCMAKE_INSTALL_RPATH="$ORIGIN/../lib"',
            # libiwyu 为 BUILDTREE_ONLY（不安装）；静态构建避免系统同名库动态污染（R26）
            "-DBUILD_SHARED_LIBS=OFF",
        ])
        self.run('cmake -B "{}" -S "{}" {}'.format(bdir, src, defs))
        self.run('cmake --build "{}" -- -j4'.format(bdir))

    def package(self):
        bdir = os.path.join(self.build_folder, "build-ohos")
        self.run('cmake --install "{}" --prefix "{}"'.format(bdir, self.package_folder))
        clang_pkg = self.dependencies["clang"].package_folder
        self._bundle_resource_headers(clang_pkg)
        self._bundle_runtime_libs(clang_pkg)
        self._sign_binaries()

    def _bundle_resource_headers(self, clang_pkg):
        # builtin 头（stddef.h/stdint.h 等编译器内建头）：clang 包 resource dir → 本包 lib/clang/22/include。
        # iwyu 的 ComputeCustomResourceDir 按 IWYU_RESOURCE_RELATIVE_TO=iwyu 相对二进制路径解析
        # （bin/include-what-you-use → ../lib/clang/22），与上游 CMakeLists 注释推荐的打包方式一致。
        import shutil
        src_res = os.path.join(clang_pkg, "lib", "clang", "22", "include")
        if not os.path.isdir(src_res):
            raise ConanException("clang package resource dir missing: {}".format(src_res))
        dst_res = os.path.join(self.package_folder, "lib", "clang", "22", "include")
        os.makedirs(os.path.dirname(dst_res), exist_ok=True)
        shutil.copytree(src_res, dst_res, dirs_exist_ok=True)

    def _bundle_runtime_libs(self, clang_pkg):
        # iwyu ELF 的 NEEDED（实测 readelf）：libclang-cpp.so.22.1 / libLLVM.so.22.1 / libc++_shared.so。
        # 自 clang 包拷入包内 lib/ + 安装 RPATH=$ORIGIN/../lib → 自包含运行时（同 clang 配方捆绑
        # libc++_shared.so 的先例），不依赖消费侧 conan 环境解析跨包 .so。
        import shutil
        needed = ["libclang-cpp.so.22.1", "libLLVM.so.22.1", "libc++_shared.so"]
        pkg_lib = os.path.join(self.package_folder, "lib")
        os.makedirs(pkg_lib, exist_ok=True)
        for lib in needed:
            src = os.path.join(clang_pkg, "lib", lib)
            if not os.path.isfile(src):
                raise ConanException(
                    "runtime lib missing in clang package: {} "
                    "(refusing to package a silently broken tool)".format(src))
            shutil.copy2(src, os.path.join(pkg_lib, lib))

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # OHOS XPM：被 exec 的可执行文件与被 dlopen 的 .so 都要代码签名，否则 Permission denied。
        # 流程同 llvm/clang 配方：objcopy 去 .codesign → binary-sign-tool 自签。
        import glob
        targets = glob.glob(os.path.join(self.package_folder, "lib", "*.so*"))
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
        # 命令行工具：bin/ 暴露 include-what-you-use + fix_includes.py + iwyu_tool.py。
        # lib/ 仅为本包 ELF 的自包含运行时（捆绑 .so）+ resource 头，不作为消费侧链接输入。
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
