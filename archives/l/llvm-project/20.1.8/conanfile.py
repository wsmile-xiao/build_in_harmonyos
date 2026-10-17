#!/usr/bin/env python3
"""Conan recipe — llvm-project 20.1.8 (LLVM 20.1.8 + Clang 20.1.8 开发面, 鸿蒙 PC 真机原生编译)

为什么单包交付 LLVM + Clang（依赖项任务的根因）：
  下游 ispc 1.28.2 的 CMake 同时消费 LLVM 与 Clang 的开发面——
      include(cmake/FindLLVM.cmake) → find_program(llvm-config) → LLVM_DIR=<bin>/../lib/cmake/llvm
      find_package(LLVM) / run_llvm_config(--libdir/--includedir/--libfiles/--targets-built)
      find_library(clangFrontend|clangBasic|clangEdit|clangLex|clangSupport|clangASTMatchers
                   NAMES lib<name>.a clang-cpp HINTS ${LLVM_LIBRARY_DIRS})
  库中现状：llvm/20.1.0 只有 LLVM（无 Clang ⇒ ispc configure 得 clangFrontendPath-NOTFOUND）；
  clang/20.1.8 远端包损坏；clang/22.1.8 是 LLVM 22（超出 ispc 1.28.2 目标区间）。
  故本包把 llvm-project 20.1.8 的 LLVM + Clang 组件库/头/cmake 导出放在**同一 prefix** 内。

交付面（下游 ispc 的验收判据，缺一不可）：
  lib/cmake/llvm/LLVMConfig.cmake（LLVM 组件图 + LLVMExports）
  lib/cmake/clang/ClangConfig.cmake + ClangTargets.cmake + ClangTargets-release.cmake
  libLLVM.so*（聚合动态库）+ libLLVM*.a（组件静态库，llvm-config --libfiles 直接给全路径）
  libclangFrontend.a libclangBasic.a libclangEdit.a libclangLex.a libclangSupport.a
  libclangASTMatchers.a（+ 其余全部 clang 组件静态库）+ libclang-cpp.so / libclang.so（兜底）
  include/llvm/** include/llvm-c/** include/clang/** include/clang-c/**
  bin/llvm-config bin/FileCheck bin/llvm-lit bin/llvm-as bin/clang bin/clang++ bin/llc bin/opt ...

目标后端选择（关键适配点，与 llvm/20.1.0、clang/20.1.8、clang/22.1.8 的 AArch64-only 不同）：
  ispc 1.28.2 的 cmake/FindLLVM.cmake 用 `llvm-config --targets-built` 判定
      LLVM_SUPPORTS_ARM = (targets-built 同时含 "AArch64" 与 "ARM")
  仅 AArch64 时 LLVM_SUPPORTS_ARM=OFF ⇒ ARM_ENABLED=OFF；aarch64 宿主上 X86_HOST 亦为 OFF
  ⇒ "Either X86, ARM, WASM or XE targets need to be enabled." FATAL_ERROR。
  另外 ispc 自身 lit 套件有 167 个用例 `REQUIRES: X86_ENABLED`（下游 ≥90% 通过率门禁），
  且 X86_ENABLED=ON 时 ispc 会用 clang++ `--target=x86_64-unknown-unknown -march=core2 -emit-llvm`
  生成 dispatch bitcode、并为 x86 目标生成 builtins——两者都要求 LLVM 注册 X86 后端。
  故本包 LLVM_TARGETS_TO_BUILD="AArch64;ARM;X86"。

构建策略与 llvm/20.1.0、clang/20.1.8、clang/22.1.8 同族：鸿蒙 PC 真机原生编译，不设 CMAKE_SYSTEM_NAME
→ CMAKE_CROSSCOMPILING=FALSE → llvm-tblgen/clang-tblgen 原生编+跑，绕开交叉编译的 tblgen 主机版难题。
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get

# 设备 hnp 工具链（CI worker 与本地同一布局；与 llvm/20.1.0、clang/22.1.8 同口径）
HNP_CLANG = "/data/service/hnp/bin/clang"
HNP_CLANGXX = "/data/service/hnp/bin/clang++"
SDK_ROOT_GLOB = "/data/service/hnp/ohos-sdk.org/ohos-sdk_*"


class LlvmProjectConan(ConanFile):
    name = "llvm-project"
    version = "20.1.8"
    description = ("LLVM 20.1.8 + Clang 20.1.8 开发面（LLVMConfig + ClangConfig/ClangTargets + "
                   "libLLVM.so + LLVM/Clang 组件静态库 + 头文件 + llvm-config/FileCheck/llvm-lit），"
                   "AArch64+ARM 后端，RTTI 开，aarch64-unknown-linux-ohos")
    license = "Apache-2.0 WITH LLVM-exception"
    homepage = "https://llvm.org"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    # shared=True（默认，下游 ispc 消费的形态）→ 出 libLLVM.so/libclang-cpp.so 聚合动态库，
    # 同时仍安装全部组件静态库（llvm-config --libfiles 直接给全路径）；
    # shared=False → 只出静态库，工具静态内嵌（体积大，仅备用）。
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    # ------------------------------------------------------------------ 源码
    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        # 归档为 llvm-project-20.1.8.src/{llvm,clang,...}；strip_root 后 source_folder 直含 llvm/ 子目录。
        get(self, **self.conan_data["sources"], strip_root=True)

    def layout(self):
        cmake_layout(self, src_folder=".")

    # ------------------------------------------------------------------ 构建
    def build(self):
        apply_conandata_patches(self)
        src = os.path.join(self.source_folder, "llvm")   # llvm-project 的 CMakeLists 在 llvm/ 子目录
        bdir = os.path.join(self.build_folder, "build-ohos")

        # ① LLVM 的 cmake/config.guess 不认设备 `uname -s = HarmonyOS` → get_host_triple 跑 config.guess
        #    非零退出 FATAL（config-ix.cmake 无条件调用它，-DLLVM_HOST_TRIPLE 挡不住）。
        #    用 stub 覆盖 config.guess，直接输出设备 clang 的目标三元组。
        _cg = os.path.join(src, "cmake", "config.guess")
        with open(_cg, "w", encoding="utf-8") as _f:
            _f.write("#!/bin/sh\necho aarch64-unknown-linux-ohos\n")

        # ② 设备 uname -s=HarmonyOS，cmake 无 Platform/HarmonyOS 模块 → UNIX 变量未置 → LLVM 判 UNIX
        #    为假 → HandleLLVMOptions "Unable to determine platform" FATAL。提供 Platform/HarmonyOS.cmake
        #    （复用 Platform/Linux：置 UNIX=1 + Linux 链接/rpath 规则）挂到 CMAKE_MODULE_PATH。
        #    保持 native——不设 CMAKE_SYSTEM_NAME → 不触发 CMAKE_CROSSCOMPILING → tblgen 原生编+跑。
        _pm = os.path.join(self.build_folder, "_cmake_modules")
        os.makedirs(os.path.join(_pm, "Platform"), exist_ok=True)
        with open(os.path.join(_pm, "Platform", "HarmonyOS.cmake"), "w", encoding="utf-8") as _f:
            _f.write("include(Platform/Linux)\n")

        # 编译器：优先取 Conan conf（ci/conan/profiles/ohos-aarch64 的
        # tools.build:compiler_executables），取不到再回退设备 hnp 绝对路径。
        # R33 口径：不使用未定义的 shell 环境变量（${CC}/${CXX}），路径要么来自 conf，要么显式常量。
        _compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = _compilers.get("c") or HNP_CLANG
        cxx = _compilers.get("cpp") or HNP_CLANGXX

        # ③ 设备 SDK sysroot 的 C 头（hnp clang 自身已带默认搜索路径，这里只作保险；找不到则跳过）
        _sysroot = self._discover_sdk_sysroot()
        if _sysroot:
            os.environ["CPATH"] = "{0}/usr/include/aarch64-linux-ohos:{0}/usr/include".format(_sysroot)

        defs = " ".join([
            "-G Ninja",
            '-DCMAKE_MODULE_PATH="{}"'.format(_pm),
            '-DCMAKE_C_COMPILER="{}"'.format(cc),
            '-DCMAKE_CXX_COMPILER="{}"'.format(cxx),
            "-DCMAKE_BUILD_TYPE=Release",
            "-DCMAKE_INSTALL_LIBDIR=lib",
            # —— 产物：LLVM 本体 + clang 前端（同一 prefix，下游一次消费两面）——
            '-DLLVM_ENABLE_PROJECTS="clang"',
            # —— 后端：AArch64 + ARM + X86。ARM 是 ispc 1.28.2 的硬需求、X86 是 ispc lit
            #    套件 X86_ENABLED 用例与 dispatch/builtins 生成的需求（见文件头「目标后端选择」）——
            '-DLLVM_TARGETS_TO_BUILD="AArch64;ARM;X86"',
            "-DLLVM_HOST_TRIPLE=aarch64-unknown-linux-ohos",
            "-DLLVM_DEFAULT_TARGET_TRIPLE=aarch64-unknown-linux-ohos",
            # —— 动态聚合库（shared=True，默认）：工具与消费方链 libLLVM.so，避免 bin/ 静态内嵌后
            #    单文件超制品仓上限（408MB）。shared=False 时只出静态库 ——
            "-DLLVM_BUILD_LLVM_DYLIB={}".format("ON" if self.options.shared else "OFF"),
            "-DLLVM_LINK_LLVM_DYLIB={}".format("ON" if self.options.shared else "OFF"),
            "-DLLVM_ENABLE_RTTI=ON",
            "-DLLVM_ENABLE_PIC=ON",
            "-DLLVM_BUILD_TOOLS=ON",
            "-DLLVM_INSTALL_UTILS=ON",
            # —— runtimes 不源码构建：SDK libc++ 15 头与 clang 20 不兼容、compiler-rt 交叉链接失败。
            #    运行资源目录（crt/builtins）在 package() 中从 SDK 复制（同 clang/20.1.8 先例）——
            '-DLLVM_ENABLE_RUNTIMES=""',
            "-DLLVM_ENABLE_ASSERTIONS=OFF",
            "-DLLVM_INCLUDE_EXAMPLES=OFF",
            # 上游 lit/unittest 套件不参与构建（体量与同树 runtime 假设见 notes.md / MANIFEST.yml）
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
            # libLLVM.so / libclang-cpp.so 链接极吃内存 → 限制并行链接任务数防 OOM。
            "-DLLVM_PARALLEL_LINK_JOBS=4",
        ])
        self.run('cmake -B "{}" -S "{}" {}'.format(bdir, src, defs))
        # 内存偏紧（设备 GUI 常驻占用高）：编译并行限 -j6，防 OOM。
        self.run('cmake --build "{}" -- -j6'.format(bdir))

    # ------------------------------------------------------------------ 打包
    def package(self):
        bdir = os.path.join(self.build_folder, "build-ohos")
        self.run('cmake --install "{}" --prefix "{}"'.format(bdir, self.package_folder))
        self._bundle_extra_tools(bdir)
        self._bundle_sdk_resource_dir()
        self._sign_binaries()

    def _bundle_extra_tools(self, bdir):
        """install 规则默认不装 llvm-lit（utils/llvm-lit 只 configure 到 build/bin）与部分 clang
        测试工具；显式从构建树补齐，保证下游 lit 测试可用（同 clang/22.1.8 先例）。"""
        src_bin = os.path.join(bdir, "bin")
        dst_bin = os.path.join(self.package_folder, "bin")
        os.makedirs(dst_bin, exist_ok=True)
        for tool in ("llvm-lit", "clang-diff", "clang-fuzzer-dictionary"):
            src = os.path.join(src_bin, tool)
            dst = os.path.join(dst_bin, tool)
            if os.path.exists(src) and not os.path.exists(dst):
                shutil.copy2(src, dst)
        if not os.path.exists(os.path.join(dst_bin, "llvm-lit")):
            self.output.warning("llvm-lit 未在构建树 bin/ 中生成（LLVM_INCLUDE_UTILS 被关闭？）")

    # -- SDK 探测（不硬编码单一 SDK 版本；与 clang/22.1.8 同口径）----------------
    @staticmethod
    def _discover_sdk_sysroot():
        for root in sorted(glob.glob(SDK_ROOT_GLOB)):
            cand = os.path.join(root, "ohos", "native", "sysroot")
            if os.path.isdir(cand):
                return cand
        return ""

    @staticmethod
    def _discover_sdk_llvm():
        for root in sorted(glob.glob(SDK_ROOT_GLOB)):
            cand = os.path.join(root, "ohos", "native", "llvm")
            if os.path.isdir(cand):
                return cand
        return ""

    @staticmethod
    def _discover_sdk_clang_rt(sdk_llvm):
        """取 SDK lib/clang/<ver>/lib/aarch64-linux-ohos（不硬编码 15.0.4）。"""
        clang_root = os.path.join(sdk_llvm, "lib", "clang")
        found = []
        if os.path.isdir(clang_root):
            for name in os.listdir(clang_root):
                rt = os.path.join(clang_root, name, "lib", "aarch64-linux-ohos")
                if os.path.isdir(rt):
                    found.append((name, rt))
        if not found:
            return ""
        found.sort(key=lambda x: [int(p) if p.isdigit() else 0 for p in x[0].split(".")])
        return found[-1][1]

    def _bundle_sdk_resource_dir(self):
        """把 SDK 的 clang 运行资源（clang_rt crt/builtins、libunwind.a、libc++abi.a）复制进包内
        resource-dir，使包内 bin/clang 能完整链接（不依赖外部路径）。非致命：SDK 不在时跳过并告警。

        R26 合规：只复制静态库/目标文件，**不**复制 SDK 的 libc++.so / libc++_shared.so 等系统同名动态库。
        """
        sdk_llvm = self._discover_sdk_llvm()
        sysroot = self._discover_sdk_sysroot()
        sdk_res = self._discover_sdk_clang_rt(sdk_llvm) if sdk_llvm else ""
        if not sdk_res:
            self.output.warning("未发现 OHOS SDK clang 资源目录，跳过运行资源捆绑（包内 bin/clang 需外部 "
                                "--sysroot 才能链接）")
            return
        res_major = self.version.split(".")[0]
        res_dst = os.path.join(self.package_folder, "lib", "clang", res_major, "lib", "aarch64-linux-ohos")
        os.makedirs(res_dst, exist_ok=True)
        # ① SDK clang 资源目录内的文件（clang_rt.*、builtins 等）
        for name in os.listdir(sdk_res):
            src = os.path.join(sdk_res, name)
            dst = os.path.join(res_dst, name)
            if os.path.isfile(src) and not os.path.exists(dst):
                shutil.copy2(src, dst)
        # ② SDK llvm/lib/aarch64-linux-ohos/libunwind.a（clang 驱动默认 -l:libunwind.a）
        sdk_llvm_lib = os.path.join(sdk_llvm, "lib", "aarch64-linux-ohos")
        if os.path.isfile(os.path.join(sdk_llvm_lib, "libunwind.a")):
            shutil.copy2(os.path.join(sdk_llvm_lib, "libunwind.a"), os.path.join(res_dst, "libunwind.a"))
        # ③ sysroot 的 crt 启动文件（鸿蒙默认 -pie 链接需要 Scrt1.o）
        if sysroot:
            sysroot_lib = os.path.join(sysroot, "usr", "lib", "aarch64-linux-ohos")
            for name in ("Scrt1.o", "crt1.o", "crti.o", "crtn.o"):
                src = os.path.join(sysroot_lib, name)
                dst = os.path.join(res_dst, name)
                if os.path.isfile(src) and not os.path.exists(dst):
                    shutil.copy2(src, dst)
        # ④ libc++abi.a 静态库（C++ 消费者链接用；libc++abi 的 .so 不复制，R26）
        abi = os.path.join(sdk_llvm_lib, "libc++abi.a")
        if os.path.isfile(abi):
            lib_dst = os.path.join(self.package_folder, "lib")
            os.makedirs(lib_dst, exist_ok=True)
            if not os.path.exists(os.path.join(lib_dst, "libc++abi.a")):
                shutil.copy2(abi, os.path.join(lib_dst, "libc++abi.a"))

    # -- 代码签名 ---------------------------------------------------------------
    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        """OHOS XPM 要求 dlopen 的 .so 与被 exec 的可执行文件都代码签名，否则 Permission denied。
        ① lib/ 的 .so（libLLVM.so、libclang-cpp.so、libclang.so…）② bin/ 的 ELF 可执行
        （llvm-config/FileCheck/clang/llc/opt…）。只对真实 ELF 签名（跳过软链与 linker script 类 .so）。"""
        targets = glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so"), recursive=True)
        targets += glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so.*"), recursive=True)
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

    # ------------------------------------------------------------------ 导出
    def package_info(self):
        # 消费方走 LLVM/Clang 自带的 cmake config（cmake_find_mode=none ⇒ Conan 不生成 find 文件），
        # 把两个 config 目录同时挂到 builddirs ⇒ CMakeToolchain 会把它们放进 CMAKE_PREFIX_PATH，
        # 于是 find_package(LLVM) 与 find_package(Clang) 都直接命中包内原生 config。
        # （与 llvm/20.1.0 同口径；ClangConfig.cmake 内部会再 find_package(LLVM) 拿组件图。）
        self.cpp_info.set_property("cmake_file_name", "LLVM")
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = ["lib/cmake/llvm", "lib/cmake/clang"]
        self.cpp_info.libs = ["LLVM"] if self.options.shared else []   # 聚合动态库；组件静态库经 config 消费
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "dl", "pthread"]
