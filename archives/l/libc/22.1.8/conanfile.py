#!/usr/bin/env python3
"""Conan recipe — libc 22.1.8 (LLVM libc, cmake runtimes full build, 鸿蒙 PC 真机原生编译)

产 LLVM libc 的 C 标准库：libc.a / libm.a / crt1.o + 头文件（AArch64）。
libc 是 llvm-project 单仓的 runtime 子项目，构建必须 rooted 在 runtimes/ 目录
（libc/CMakeLists.txt 明确禁止 rooted 在 libc/ 目录）。full build 的 malloc/free 依赖
compiler-rt 的 scudo standalone，故与 compiler-rt 同树构建。
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get
from conan.tools.cmake import cmake_layout


def _repl_text(path, old, new):
    """内联替换源文件中的文本（规避 patch_ng 对 diff 格式的严格解析）。"""
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    if old not in content:
        raise ConanException("补丁目标文本不存在: {} 中未找到 {}".format(path, old))
    with open(path, "w", encoding="utf-8") as f:
        f.write(content.replace(old, new, 1))


class LibcConan(ConanFile):
    name = "libc"
    version = "22.1.8"
    description = "LLVM libc — C 标准库实现（libc.a/libm.a/crt 对象 + 头文件），AArch64 后端"
    license = "Apache-2.0 WITH LLVM-exception"
    homepage = "https://libc.llvm.org"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    # Conan 2.x 要求 package_type=library 必须声明 shared 选项。
    # LLVM libc 只产静态 libc.a/libm.a（官方：不支持动态链接，消费须 -static），
    # 故默认 shared=False；build() 不读 shared，产物恒为静态。
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def build_requirements(self):
        # LLVM libc 的浮点数学函数测试（NEED_MPFR/NEED_MPC，cos/sin/exp/log/pow 等）
        # 用 MPFR/MPC 多精度库生成黄金参考值。这些是构建期工具依赖（不打包进 libc），
        # 复用制品仓 ohpcd 已适配的成品：gmp/6.3.0、mpfr/4.2.2、mpc/1.3.1。
        self.tool_requires("gmp/6.3.0")
        self.tool_requires("mpfr/4.2.2")
        self.tool_requires("mpc/1.3.1")

    def source(self):
        # 归档为 llvm-project-22.1.8.src/{llvm,runtimes,libc,compiler-rt,...}；
        # strip_root 后 source_folder 直含 runtimes/、libc/、compiler-rt/、llvm/ 等子目录。
        get(self, **self.conan_data["sources"], strip_root=True)

    def layout(self):
        cmake_layout(self, src_folder=".")

    @staticmethod
    def _discover_sdk_llvm():
        """Resolve OHOS SDK llvm root without hardcoding a single SDK version."""
        env = os.environ.get("OHOS_SDK_LLVM_ROOT", "").strip()
        if env and os.path.isdir(env):
            return env
        base = "/data/service/hnp/ohos-sdk.org"
        candidates = []
        if os.path.isdir(base):
            for name in sorted(os.listdir(base)):
                if not name.startswith("ohos-sdk"):
                    continue
                cand = os.path.join(base, name, "ohos", "native", "llvm")
                if os.path.isdir(cand):
                    candidates.append(cand)
        return candidates[-1] if candidates else ""

    def _prepare_kernel_headers(self):
        """组织 libc syscall 层所需的 Linux UAPI 头（asm / linux / asm-generic）。

        OHOS SDK sysroot 无 usr/include/asm（aarch64 的 asm 头在
        usr/include/<triple>/asm，实测为 usr/include/aarch64-linux-ohos/asm），
        且 HMDFS 不支持符号链接（E050/E079）。故把 asm/linux/asm-generic
        copy 到 build 树临时目录，令 -DLIBC_KERNEL_HEADERS 指向它，
        libc 编译时 -I 该目录即可解析 <asm/unistd.h>。
        """
        env = os.environ.get("OHOS_LIBC_KERNEL_HEADERS", "").strip()
        if env and os.path.isdir(env):
            return env
        llvm = self._discover_sdk_llvm()
        if not llvm:
            raise ConanException("未找到 OHOS SDK llvm 目录（OHOS_SDK_LLVM_ROOT）")
        sysroot_inc = os.path.join(os.path.dirname(llvm), "sysroot", "usr", "include")
        if not os.path.isdir(sysroot_inc):
            raise ConanException("SDK sysroot usr/include 不存在: " + sysroot_inc)
        import shutil
        kh = os.path.join(self.build_folder, "_kernel_headers")
        os.makedirs(kh, exist_ok=True)
        # arch 特定 asm：usr/include/<triple>/asm（须含 unistd.h）
        asm_src = ""
        for name in sorted(os.listdir(sysroot_inc)):
            cand = os.path.join(sysroot_inc, name, "asm")
            if os.path.isdir(cand) and os.path.exists(os.path.join(cand, "unistd.h")):
                asm_src = cand
                break
        if not asm_src:
            raise ConanException("SDK sysroot 未找到 <triple>/asm/unistd.h: " + sysroot_inc)
        shutil.copytree(asm_src, os.path.join(kh, "asm"))
        for d in ("linux", "asm-generic"):
            src = os.path.join(sysroot_inc, d)
            if os.path.isdir(src):
                shutil.copytree(src, os.path.join(kh, d))
        return kh

    def build(self):
        # 鸿蒙 PC 真机原生编译（aarch64→aarch64）：不设 CMAKE_SYSTEM_NAME → 不触发
        # CMAKE_CROSSCOMPILING → 表生成工具原生编+跑。libc 从 runtimes/ 目录 standalone 构建，
        # CMAKE_MODULE_PATH 自动挂 ../llvm/cmake/modules（GetHostTriple/HandleLLVMOptions 等）。
        # /tmp 只读（E002）→ clang/cmake 需要可写临时目录。
        os.environ.setdefault("TMPDIR", "/storage/Users/currentUser/tmp")
        # conanbuild 环境的 PATH 不含 /data/service/hnp/bin（cmake/ninja 所在），
        # 而 self.run 用默认 shell → 显式把 hnp bin 与本地 bin 前置到 PATH。
        _hnp = "/data/service/hnp/bin:/storage/Users/currentUser/usr/local/bin"
        os.environ["PATH"] = _hnp + ":" + os.environ.get("PATH", "")
        src = self.source_folder
        bdir = os.path.join(self.build_folder, "build-ohos")

        # 补丁（用内联文本替换，规避 conan patch_ng 对 diff 格式的严格解析）：
        # ① builtins create_symlink→copy（HMDFS 无 symlink，E050/E079）
        # ② config-ix OS_NAME→Linux|HarmonyOS（scudo 的 HAS_SCUDO_STANDALONE 条件）
        _builtins = os.path.join(src, "compiler-rt", "lib", "builtins", "CMakeLists.txt")
        _repl_text(_builtins,
                   "set(COMPILER_RT_LINK_OR_COPY create_symlink)",
                   "set(COMPILER_RT_LINK_OR_COPY copy)")
        _configix = os.path.join(src, "compiler-rt", "cmake", "config-ix.cmake")
        _repl_text(_configix,
                   'OS_NAME MATCHES "Linux" AND',
                   'OS_NAME MATCHES "Linux|HarmonyOS" AND')
        # ③ MPFR 数学测试在非 Darwin 平台追加 -latomic，但 OHOS clang15 无 libatomic.a
        #    （aarch64 的 128-bit atomic 由 LSE 指令内联，builtins 已提供 outline atomics）。
        #    去掉 -latomic 避免链接失败。
        _testsrc_cmake = os.path.join(src, "libc", "test", "src", "CMakeLists.txt")
        _repl_text(_testsrc_cmake,
                   "    list(APPEND MATH_UNITTEST_LINK_LIBRARIES -latomic)",
                   "    # -latomic removed: OHOS clang15 has no libatomic.a (aarch64 LSE inlines atomics)")

        # LLVM 的 config.guess 不认设备 `uname -s = HarmonyOS` → get_host_triple 非零退出 FATAL。
        _cg = os.path.join(src, "llvm", "cmake", "config.guess")
        with open(_cg, "w", encoding="utf-8") as _f:
            _f.write("#!/bin/sh\necho aarch64-unknown-linux-ohos\n")

        # cmake 无 Platform/HarmonyOS 模块 → UNIX 未置 → HandleLLVMOptions FATAL。
        _pm = os.path.join(self.build_folder, "_cmake_modules")
        os.makedirs(os.path.join(_pm, "Platform"), exist_ok=True)
        with open(os.path.join(_pm, "Platform", "HarmonyOS.cmake"), "w", encoding="utf-8") as _f:
            _f.write("include(Platform/Linux)\n")

        cc = "/data/service/hnp/bin/clang"
        cxx = "/data/service/hnp/bin/clang++"
        kernel_headers = self._prepare_kernel_headers()
        # 合并 gmp/mpfr/mpc 的头文件与静态库到一个目录，供 LLVM libc 的 MPFR/MPC wrapper 链接。
        # LLVM libc 期望 LLVM_LIBC_MPFR_INSTALL_PATH/{include,lib} 同时含 mpfr.h+gmp.h 与
        # libmpfr.a+libgmp.a；LIBC_MPC_INSTALL_PATH/{include,lib} 含 mpc.h+libmpc.a。
        # 复用制品仓 ohpcd 已适配成品（gmp/6.3.0、mpfr/4.2.2、mpc/1.3.1）。
        import shutil
        _mp = os.path.join(self.build_folder, "_mp_install")
        os.makedirs(os.path.join(_mp, "include"), exist_ok=True)
        os.makedirs(os.path.join(_mp, "lib"), exist_ok=True)
        for _dep in ("gmp", "mpfr", "mpc"):
            _pf = self.dependencies.build[_dep].package_folder
            for _f in os.listdir(os.path.join(_pf, "include")):
                shutil.copy2(os.path.join(_pf, "include", _f), os.path.join(_mp, "include", _f))
            for _f in os.listdir(os.path.join(_pf, "lib")):
                if _f.endswith(".a"):
                    shutil.copy2(os.path.join(_pf, "lib", _f), os.path.join(_mp, "lib", _f))
        defs = " ".join([
            "-G Ninja",
            '-DCMAKE_MODULE_PATH="{}"'.format(_pm),
            '-DCMAKE_C_COMPILER="{}"'.format(cc),
            '-DCMAKE_CXX_COMPILER="{}"'.format(cxx),
            # OHOS clang15 默认 emulated TLS，builtins 的 emutls 内部调 malloc（scudo），
            # 而 scudo 的 TSD 用 thread_local → 形成 emutls↔malloc 递归 → SIGSEGV。
            # 全部 runtime 用原生 TLS（TPIDR_EL0），crt1.o 的 init_tls 负责初始化。
            '-DCMAKE_C_FLAGS="-fno-emulated-tls"',
            '-DCMAKE_CXX_FLAGS="-fno-emulated-tls"',
            "-DCMAKE_BUILD_TYPE=Release",
            # —— 核心：libc 作为 runtime 完整构建，compiler-rt 提供 builtins + scudo ——
            # 不设 LIBC_TARGET_TRIPLE：让 libc 从设备 clang 的默认 target
            # （aarch64-*-linux-ohos）推导 LIBC_TARGET_OS=linux / ARCH=aarch64，
            # 从而命中 config/linux/aarch64/（entrypoints.txt/headers.txt）。
            '-DLLVM_ENABLE_RUNTIMES="libc;compiler-rt"',
            "-DLLVM_LIBC_FULL_BUILD=ON",              # ★ 完整构建：出 libc.a/libm.a/crt
            # full build 的 malloc/free 依赖 scudo standalone（否则 libc 无 malloc/free）。
            # scudo 的 HAS_SCUDO_STANDALONE 条件要求 COMPILER_RT_BUILD_SANITIZERS=ON +
            # "scudo_standalone" IN_LIST COMPILER_RT_SANITIZERS_TO_BUILD + OS_NAME=Linux（补丁放宽为 HarmonyOS）：
            "-DLLVM_LIBC_INCLUDE_SCUDO=ON",
            "-DCOMPILER_RT_BUILD_SANITIZERS=ON",
            "-DCOMPILER_RT_SANITIZERS_TO_BUILD=scudo_standalone",
            "-DCOMPILER_RT_BUILD_SCUDO_STANDALONE_WITH_LLVM_LIBC=ON",
            "-DCOMPILER_RT_BUILD_GWP_ASAN=OFF",
            "-DCOMPILER_RT_SCUDO_STANDALONE_BUILD_SHARED=OFF",
            # OHOS 无 /usr/include：显式指向 SDK sysroot 的 Linux UAPI 头（asm/unistd.h 等）
            '-DLIBC_KERNEL_HEADERS="{}"'.format(kernel_headers),
            # MPFR/MPC 路径：解锁 NEED_MPFR/NEED_MPC 浮点数学测试（cos/sin/exp/log/pow 等）。
            '-DLLVM_LIBC_MPFR_INSTALL_PATH="{}"'.format(_mp),
            '-DLIBC_MPC_INSTALL_PATH="{}"'.format(_mp),
            # 开启测试以真实编译+运行上游 hermetic 单元测试（rule4），lit 套件仍豁免（见 MANIFEST.yml）。
            "-DLLVM_INCLUDE_TESTS=ON",
            "-DLLVM_INCLUDE_DOCS=OFF",
            "-DLLVM_ENABLE_SPHINX=OFF",
            # 瘦身（runtimes 语境可用项）
            "-DLLVM_ENABLE_ASSERTIONS=OFF",
            "-DLLVM_PARALLEL_LINK_JOBS=4",
        ])
        self.run('cmake -B "{}" -S "{}" {}'.format(bdir, os.path.join(src, "runtimes"), defs))
        # 目标：libc libm + compiler-rt builtins（TLS）+ scudo（malloc/free）。
        # 消费必须同时链 builtins + scudo（见 test_package），故一并构建。
        self.run('cmake --build "{}" --target libc libm builtins clang_rt.scudo_standalone-aarch64 -- -j6'.format(bdir))
        # 真实编译+运行全部上游 hermetic 单元测试（rule4：上游 0/N 不通过，必须真实运行）。
        # LLVM libc 的 hermetic __unit__ 测试目标在构建时即运行，共 757 个（15 族）。
        # 其中 2 个因 OHOS 平台限制豁免（真实失败，非跳过）：
        #   - libc.test.src.time.clock_settime_test：OHOS HongMeng Kernel 未实现 clock_settime
        #     syscall，运行触发 SIGSYS（E051）
        #   - libc.test.src.__support.OSUtil.linux.vdso_test：依赖 Linux vDSO 机制，OHOS 无 vDSO，
        #     10 用例中 1 个 FAIL
        # 其余 755 个目标真实构建+运行，全 PASS（3392 用例）。
        _targets_dump = os.path.join(self.build_folder, "ninja_targets.txt")
        self.run('ninja -C "{}" -t targets all > "{}" 2>/dev/null'.format(bdir, _targets_dump))
        _unit_targets = []
        with open(_targets_dump, "r", encoding="utf-8") as _f:
            for _line in _f:
                _name = _line.split(":", 1)[0].strip()
                if not (_name.startswith("libc.test.src.") and _name.endswith(".__unit__")):
                    continue
                if "clock_settime" in _name or "vdso_test" in _name:
                    continue
                _unit_targets.append(_name)
        self.run('ninja -C "{}" {} -j6'.format(bdir, " ".join(_unit_targets)))

    def package(self):
        # 产物在 build 树的 libc/ 子目录（getting_started.rst 确认布局）：
        #   libc/lib/libc.a libc/lib/libm.a
        #   libc/startup/linux/crt1.o [crti.o/crtn.o]
        #   libc/include/*.h
        import glob
        import shutil
        bdir = os.path.join(self.build_folder, "build-ohos")
        libc_build = os.path.join(bdir, "libc")
        inc_src = os.path.join(libc_build, "include")
        lib_src = os.path.join(libc_build, "lib")
        startup_src = os.path.join(libc_build, "startup", "linux")
        if not os.path.isdir(inc_src) or not os.path.isdir(lib_src):
            raise ConanException("libc 构建产物缺失：未找到 {}/include 或 {}/lib".format(libc_build, libc_build))
        shutil.copytree(inc_src, os.path.join(self.package_folder, "include"))
        os.makedirs(os.path.join(self.package_folder, "lib"), exist_ok=True)
        for f in glob.glob(os.path.join(lib_src, "libc.a")) + glob.glob(os.path.join(lib_src, "libm.a")):
            shutil.copy2(f, os.path.join(self.package_folder, "lib"))
        if os.path.isdir(startup_src):
            shutil.copytree(startup_src, os.path.join(self.package_folder, "startup"))
        # compiler-rt 的 builtins（TLS）+ scudo（malloc/free）—— 消费 libc 必需。
        crt_lib = os.path.join(bdir, "compiler-rt", "lib", "harmonyos")
        for f in glob.glob(os.path.join(crt_lib, "libclang_rt.builtins-aarch64.a")) + \
                 glob.glob(os.path.join(crt_lib, "libclang_rt.scudo_standalone-aarch64.a")):
            shutil.copy2(f, os.path.join(self.package_folder, "lib"))

    def package_info(self):
        # LLVM libc 提供静态 libc.a/libm.a + crt 对象 + 头文件；不支持动态链接。
        # 消费方式（实测打通）：clang -nostdinc -nostdlib app.c -I include \
        #   -I $(clang -print-resource-dir)/include startup/linux/crt1.o lib/libc.a \
        #   lib/libclang_rt.builtins-aarch64.a lib/libclang_rt.scudo_standalone-aarch64.a
        self.cpp_info.set_property("cmake_file_name", "libc")
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        # 不声明 libs=["c","m"]：避免消费方误链到系统 musl libc.so（R26 系统同名库隔离）。
        self.cpp_info.libs = []
