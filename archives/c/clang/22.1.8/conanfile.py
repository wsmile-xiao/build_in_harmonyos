#!/usr/bin/env python3
"""Conan recipe — clang 22.1.8 (cmake, 鸿蒙 PC 真机原生编译)

产 clang/clang++ 编译器工具链（bin/）+ libclang/libLLVM（lib/）。
基于 llvm-project 单仓，CMakeLists 在 llvm/ 子目录，-DLLVM_ENABLE_PROJECTS=clang。
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import cmake_layout


class ClangConan(ConanFile):
    name = "clang"
    version = "22.1.8"
    description = "clang/clang++ 编译器工具链（LLVM 前端驱动 + libclang/libLLVM），AArch64 后端，RTTI 开"
    license = "Apache-2.0 WITH LLVM-exception"
    homepage = "https://clang.llvm.org"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        # 归档为 llvm-project-22.1.8.src/{llvm,clang,...}；strip_root 后 source_folder 直含 llvm/ 子目录。
        get(self, **self.conan_data["sources"], strip_root=True)

    def layout(self):
        cmake_layout(self, src_folder=".")

    def build(self):
        # 鸿蒙 PC 真机原生编译（aarch64→aarch64）：不用任何 toolchain 文件——裸 cmake 用设备 hnp clang 直编。
        # 不设 CMAKE_SYSTEM_NAME → CMAKE_CROSSCOMPILING=FALSE → llvm-tblgen/clang-tblgen 原生编+跑，绕开交叉
        # 编译的 tblgen 主机版难题。用 Ninja（LLVM 官方推荐）。
        apply_conandata_patches(self)
        src = os.path.join(self.source_folder, "llvm")   # CMakeLists 在 llvm/ 子目录
        bdir = os.path.join(self.build_folder, "build-ohos")
        # LLVM 的 config.guess 不认设备 `uname -s = HarmonyOS` → get_host_triple 跑 config.guess 非零退出
        # FATAL（config-ix.cmake 无条件调用它，-DLLVM_HOST_TRIPLE 挡不住）。用 stub 覆盖 config.guess 直接
        # 输出 ohos 三元组（设备 clang 的 target 即 aarch64-unknown-linux-ohos）。
        _cg = os.path.join(src, "cmake", "config.guess")
        with open(_cg, "w", encoding="utf-8") as _f:
            _f.write("#!/bin/sh\necho aarch64-unknown-linux-ohos\n")
        # 设备 uname -s=HarmonyOS，cmake 无 Platform/HarmonyOS 模块 → UNIX 变量未置 → LLVM 判 UNIX 为假
        # → HandleLLVMOptions "Unable to determine platform" FATAL。提供 Platform/HarmonyOS.cmake（复用
        # Platform/Linux：置 UNIX=1 + Linux 链接/rpath 规则）挂到 CMAKE_MODULE_PATH。保持 native——不设
        # CMAKE_SYSTEM_NAME → 不触发 CMAKE_CROSSCOMPILING → tblgen 仍原生编+跑。
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
            # —— 产物：LLVM 本体 + clang 项目 ——
            "-DLLVM_ENABLE_PROJECTS=clang",           # ★ 核心：clang/clang++ 工具链
            "-DLLVM_BUILD_LLVM_DYLIB=ON",             # 出 libLLVM.so（聚合动态库）
            "-DLLVM_LINK_LLVM_DYLIB=ON",              # 工具链 libLLVM.so：clang 可执行从 ~百MB 内嵌静态
                                                       # 降到 MB 级，绕过制品仓单文件上限（408MB）
            "-DLLVM_ENABLE_RTTI=ON",                  # 下游（llvmlite 等）常用，通用也常用（默认 OFF）
            "-DLLVM_ENABLE_PIC=ON",
            "-DLLVM_BUILD_TOOLS=ON",                  # llvm-config 等工具（下游必需）
            "-DLLVM_INSTALL_UTILS=ON",                # FileCheck/count/not 等（下游测试常用）
            # —— 瘦身：仅 AArch64、无 tests/examples/benchmarks/docs ——
            "-DLLVM_TARGETS_TO_BUILD=AArch64",
            "-DLLVM_HOST_TRIPLE=aarch64-unknown-linux-ohos",
            "-DLLVM_DEFAULT_TARGET_TRIPLE=aarch64-unknown-linux-ohos",
            "-DLLVM_ENABLE_ASSERTIONS=OFF",
            "-DLLVM_INCLUDE_EXAMPLES=OFF",
            "-DLLVM_INCLUDE_TESTS=OFF",
            "-DLLVM_INCLUDE_BENCHMARKS=OFF",
            "-DLLVM_INCLUDE_DOCS=OFF",
            # —— HLSL 头 + 测试辅助工具：lit 全量套件需要它们（hlsl.h 头被
            #    CLANG_ENABLE_HLSL 门控；c-index-test/apinotes-test 被
            #    CLANG_INCLUDE_TESTS 门控），开启以支持上游全量测试 ——
            "-DCLANG_ENABLE_HLSL=ON",
            "-DCLANG_INCLUDE_TESTS=ON",
            # —— 自包含：关掉 LLVM 会自动探测的可选系统依赖，避免链到设备上不存在的库 ——
            "-DLLVM_ENABLE_ZLIB=OFF",
            "-DLLVM_ENABLE_ZSTD=OFF",
            "-DLLVM_ENABLE_LIBXML2=OFF",
            "-DLLVM_ENABLE_TERMINFO=OFF",
            "-DLLVM_ENABLE_LIBEDIT=OFF",
            "-DLLVM_ENABLE_LIBPFM=OFF",
            # libLLVM.so 链接极吃内存 → 限制并行链接任务数防 OOM（本机 20 核 / 内存偏紧）。
            "-DLLVM_PARALLEL_LINK_JOBS=4",
        ])
        self.run('cmake -B "{}" -S "{}" {}'.format(bdir, src, defs))
        # 内存偏紧（本机 GUI 常驻占用高）：编译并行限 -j6，防 OOM。
        self.run('cmake --build "{}" -- -j6'.format(bdir))

    def package(self):
        bdir = os.path.join(self.build_folder, "build-ohos")
        self.run('cmake --install "{}" --prefix "{}"'.format(bdir, self.package_folder))
        self._bundle_test_tools(bdir)
        self._bundle_sdk_runtime()
        self._sign_binaries()

    def _bundle_test_tools(self, bdir):
        # clang-diff / clang-fuzzer-dictionary / llvm-lit 等 lit 套件必需工具：
        # LLVM 的 install 规则默认不装（add_clang_executable 的 install 被
        # LLVM_DISTRIBUTION_COMPONENTS 门控），但构建树里已有产物，显式补齐，
        # 保证上游 clang/test lit 全量套件可完整运行（Tooling/clang-diff-*、
        # Misc/fuzzer-dictionary、utils/update_cc_test_checks-*）。
        import shutil
        src_bin = os.path.join(bdir, "bin")
        dst_bin = os.path.join(self.package_folder, "bin")
        os.makedirs(dst_bin, exist_ok=True)
        for tool in ("clang-diff", "clang-fuzzer-dictionary", "llvm-lit"):
            src = os.path.join(src_bin, tool)
            dst = os.path.join(dst_bin, tool)
            if os.path.exists(src) and not os.path.exists(dst):
                shutil.copy2(src, dst)

    @staticmethod
    def _discover_sdk_llvm():
        """Resolve OHOS SDK llvm root without hardcoding a single SDK version.

        Prefer OHOS_SDK_LLVM_ROOT; otherwise glob /data/service/hnp/ohos-sdk.org/ohos-sdk*/...
        """
        env = os.environ.get("OHOS_SDK_LLVM_ROOT", "").strip()
        if env:
            if os.path.isdir(env):
                return env
            raise ConanException(
                "OHOS_SDK_LLVM_ROOT={} is set but not a directory".format(env)
            )
        base = "/data/service/hnp/ohos-sdk.org"
        candidates = []
        if os.path.isdir(base):
            for name in sorted(os.listdir(base)):
                if not name.startswith("ohos-sdk"):
                    continue
                cand = os.path.join(base, name, "ohos", "native", "llvm")
                if os.path.isdir(cand):
                    candidates.append(cand)
        if candidates:
            # Lexicographic max usually tracks newest ohos-sdk_X.Y.Z.W directory name.
            return candidates[-1]
        raise ConanException(
            "OHOS SDK llvm root not found. Set OHOS_SDK_LLVM_ROOT, or install "
            "ohos-sdk under /data/service/hnp/ohos-sdk.org/ohos-sdk*/ohos/native/llvm"
        )

    @staticmethod
    def _discover_sdk_clang_rt_dir(sdk_llvm):
        """Pick SDK lib/clang/<ver>/lib/aarch64-linux-ohos (do not hardcode 15.0.4)."""
        clang_root = os.path.join(sdk_llvm, "lib", "clang")
        if not os.path.isdir(clang_root):
            raise ConanException(
                "OHOS SDK has no lib/clang under {}".format(sdk_llvm)
            )

        def _ver_key(v):
            parts = []
            for p in v.split("."):
                try:
                    parts.append(int(p))
                except ValueError:
                    parts.append(0)
            return tuple(parts)

        found = []
        for name in os.listdir(clang_root):
            rt = os.path.join(clang_root, name, "lib", "aarch64-linux-ohos")
            if os.path.isdir(rt):
                found.append((name, rt))
        if not found:
            raise ConanException(
                "No SDK clang resource dir with lib/aarch64-linux-ohos under {}".format(
                    clang_root
                )
            )
        found.sort(key=lambda x: _ver_key(x[0]))
        return found[-1][1]

    def _bundle_sdk_runtime(self):
        # 自编 clang 的 resource-dir 只有内建头（lib/clang/22/include），没有编译器运行时
        # （crtbegin/crtend/builtins）。设备 SDK clang 的 resource-dir 里有这些文件，
        # 复制进包内 resource-dir（lib/clang/22/lib/aarch64-linux-ohos/），使 clang 能
        # 直接完整链接 C/C++ 程序，不依赖外部路径。
        # 同时把 libc++_shared.so 放进包内 lib/（clang 二进制 NEEDED 它，RUNPATH=$ORIGIN/../lib）。
        import shutil
        sdk_llvm = self._discover_sdk_llvm()
        sdk_cxx = os.path.join(sdk_llvm, "lib", "aarch64-linux-ohos", "libc++_shared.so")
        if not os.path.exists(sdk_cxx):
            raise ConanException(
                "OHOS SDK runtime missing (libc++_shared.so) under {}. "
                "Set OHOS_SDK_LLVM_ROOT to the SDK llvm root; refusing to package "
                "a silently broken toolchain.".format(sdk_llvm)
            )
        res_major = self.version.split(".")[0]                    # 22
        res_lib = os.path.join(self.package_folder, "lib", "clang", res_major, "lib", "aarch64-linux-ohos")
        os.makedirs(res_lib, exist_ok=True)
        sdk_res = self._discover_sdk_clang_rt_dir(sdk_llvm)
        for f in ("clang_rt.crtbegin.o", "clang_rt.crtend.o", "libclang_rt.builtins.a"):
            src = os.path.join(sdk_res, f)
            if not os.path.exists(src):
                raise ConanException(
                    "OHOS SDK compiler runtime missing: {}. "
                    "Set OHOS_SDK_LLVM_ROOT to a complete SDK llvm tree.".format(src)
                )
            shutil.copy2(src, os.path.join(res_lib, f))
        # libc++_shared.so → 包内 lib/
        shutil.copy2(sdk_cxx, os.path.join(self.package_folder, "lib", "libc++_shared.so"))

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # OHOS XPM 要求 dlopen 的 .so 和被 exec 的可执行文件都要代码签名，否则报 Permission denied /
        # Operation not permitted。统一重签：
        #   ① lib/ 的 .so（libLLVM.so、libclang*.so 等）  ② bin/ 的 ELF 可执行（clang/clang++/clang-format…）。
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
            if os.path.islink(f):
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        # clang 工具链：可执行文件在 bin/（clang/clang++/clang-format/clang-scan-deps 等）。
        # lib/ 含 libclang-cpp.so / libLLVM.so / libclang*.so 供消费方 dlopen 或链接。
        self.cpp_info.set_property("cmake_file_name", "Clang")
        self.cpp_info.set_property("cmake_find_mode", "config")
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = ["clang-cpp", "LLVM"]     # 聚合动态库；clang 组件静态库经 clang/LLVM config 消费
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "dl", "pthread"]
