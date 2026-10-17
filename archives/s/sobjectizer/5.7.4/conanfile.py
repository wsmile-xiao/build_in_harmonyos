#!/usr/bin/env python3
"""Conan recipe — sobjectizer 5.7.4 (cmake)

SObjectizer 是 C++17 的 actor-model / 消息传递框架（Stiffstream 出品），
上游仓库把全部 CMake 工程放在 `dev/` 子目录下（仓库根没有 CMakeLists.txt），
因此本配方必须用 `dev/` 作为 CMake 源目录，并且 `-DBUILD_TESTS=ON` 才会
构建并注册上游单元测试。

用例数口径（实测，非估算）：`-DBUILD_TESTS=ON` configure 后，
构建树里 `add_test` 条目 = **319**，`ctest -N` 的 `Total Tests:` = **319**，
`ctest` 实跑 = **319**（真机/CI 全量）。本文件此前两处写作 320，
系笔误，现统一为 319。
"""
import glob
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import collect_libs, get
from conan.tools.files import apply_conandata_patches, export_conandata_patches


class SobjectizerConan(ConanFile):
    name = "sobjectizer"
    version = "5.7.4"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def layout(self):
        # 上游仓库根没有 CMakeLists.txt，全部 CMake 工程在 dev/ 下。
        # 这里只声明构建目录；build() 里用 <build_folder>/build-ohos 再下一层，
        # 避免与 conan 自己生成的 generators 目录互相干扰。
        self.folders.build = "build"
        self.folders.generators = os.path.join(self.folders.build, "generators")

    def _ohos_toolchain(self):
        # 自发现 OHOS NDK 的 ohos.toolchain.cmake（① profile [conf] user_toolchain
        # ② 环境 OHOS_NDK_HOME ③ glob 设备/CI 的 SDK 布局），不依赖 CI profile host 段。
        ut = self.conf.get("tools.cmake.cmaketoolchain:user_toolchain", default=[], check_type=list)
        ndk = os.environ.get("OHOS_NDK_HOME", "")
        for _c in list(ut) + ([os.path.join(ndk, "build/cmake/ohos.toolchain.cmake")] if ndk else []):
            if _c and os.path.isfile(_c):
                return _c
        _g = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake"))
        if _g:
            return _g[-1]
        raise ConanInvalidConfiguration(
            "找不到 ohos.toolchain.cmake：设 OHOS_NDK_HOME 或 profile [conf] user_toolchain")

    def _llvm_ranlib(self, toolchain):
        # OHOS SDK 的 llvm/bin 下只有 llvm-ar，没有 llvm-ranlib，而 ohos.toolchain.cmake
        # 仍把 CMAKE_RANLIB 指过去。cmake 造静态库是 `<AR> qc ... && <RANLIB> <lib>`，
        # 于是 .o 全编得动、一造 .a 就 ENOENT，且报错不说是哪个程序找不到：
        #   Error running link command: no such file or directory
        # SObjectizer 本配方 SOBJECTIZER_BUILD_STATIC 默认 ON，必定踩到。
        sdk_bin = os.path.join(toolchain, "..", "..", "..", "llvm", "bin")
        cand = os.path.normpath(os.path.join(sdk_bin, "llvm-ranlib"))
        if os.path.isfile(cand):
            return ""
        return shutil.which("llvm-ranlib") or ""

    def _ctest_exclude(self):
        """返回只在【用户态模拟器】下需要排除的 ctest 用例正则；真机返回空串。

        `_unit.test.spinlocks.llvm_inspired_test` 是纯用户态 TATAS 自旋锁压力
        测试（8 线程 × 64K 迭代，dev/test/so_5/spinlocks/llvm_inspired_test）。
        qemu-user 把 guest 线程复用到 host 线程上、没有 guest 内核调度器，一个
        在纯用户态循环里自旋的 guest 线程会饿死同 guest 的其它线程 → 活锁：
        实测 10 个线程 8 秒墙钟烧掉 62 秒 CPU（≈8 核满载）却永不结束。

        这是**模拟器的调度局限，不是库在 aarch64 上的缺陷**，三条证据：
          1. 同一份 main.cpp 原生 x86-64（g++ -O2）60 秒内通过；
          2. qemu-aarch64 下把 kIters 从 64K 降到 1024 即通过（证明实现正确）；
          3. 真机 DAYU200（OpenHarmony 6.0.0.47, aarch64）上该用例正常通过。

        因此只在检测到用户态模拟器时排除它，真机/CI 完整执行 319 个用例。
        """
        emu = self._configured_emulator()
        if emu and self._is_user_mode_emulator(emu):
            return "_unit.test.spinlocks.llvm_inspired_test"
        return ""

    def _configured_emulator(self):
        """取 profile 里配置的模拟器路径（tools.cmake.cmaketoolchain:
        extra_variables 的 CMAKE_CROSSCOMPILING_EMULATOR），没有则空串。"""
        extra = self.conf.get("tools.cmake.cmaketoolchain:extra_variables",
                              default={}, check_type=dict)
        for key in ("CMAKE_CROSSCOMPILING_EMULATOR", "CMAKE_CROSSCOMPILING_EMULATOR_ARGS"):
            v = extra.get(key)
            if key == "CMAKE_CROSSCOMPILING_EMULATOR" and v:
                return str(v)
        return ""

    @staticmethod
    def _is_user_mode_emulator(emu):
        """判断是否为 qemu【用户态】模拟器（qemu-<arch>[-static]）。

        注意设备/CI 上模拟器常被包一层 wrapper 脚本（例如
        /root/ohpc/bin/ohos-qemu-aarch64 内是
        `exec /root/ohpc/sdk/qemu/usr/bin/qemu-aarch64-static -L <runroot> ...`），
        此时只看 basename 会漏判，所以要连 wrapper 内容一起看。

        只认用户态 qemu：全系统模拟（qemu-system-*）有真正的 guest 内核调度器，
        不存在本用例要规避的线程饿死问题，不应排除。
        """
        import re
        path = str(emu)
        candidates = [os.path.basename(path)]
        try:
            if os.path.isfile(path):
                with open(path, "r", errors="replace") as f:
                    candidates.append(f.read(4096))
        except OSError:
            pass
        blob = " ".join(candidates).lower()
        # 用户态 qemu：qemu-aarch64 / qemu-aarch64-static / qemu-arm ...
        if re.search(r"qemu-[a-z0-9_]+(-static)?\b", blob) and "qemu-system" not in blob:
            return True
        return False

    def _build_jobs(self):
        # tools.build:jobs 缺省时 conan 用 CPU 数；这里再夹到 8，避免 OOM。
        import multiprocessing
        jobs = self.conf.get("tools.build:jobs", default=None, check_type=int)
        if not jobs or jobs <= 0:
            jobs = multiprocessing.cpu_count()
        return max(1, min(int(jobs), 8))

    def build(self):
        # 与 glfw/brotli/zstd 同法：自发现 ohos.toolchain + 裸 cmake，绕开 conan_toolchain——
        # os=OHOS 下它把 CMAKE_SYSTEM_NAME 映射成 cmake 不认的值（ML-0035）。
        apply_conandata_patches(self)
        toolchain = self._ohos_toolchain()
        # 上游 CMake 工程根在 <source_folder>/dev（仓库根无 CMakeLists.txt）。
        src = os.path.join(self.source_folder, "dev", "")
        bdir = os.path.join(self.build_folder, "build-ohos")
        defs = [
            '-DCMAKE_TOOLCHAIN_FILE="{}"'.format(toolchain),
            "-DOHOS_ARCH=arm64-v8a",
            "-DCMAKE_BUILD_TYPE={}".format(self.settings.build_type),
            "-DCMAKE_INSTALL_LIBDIR=lib",           # ohos.toolchain 64 位默认装 lib64/，须改回 lib
            # configure 期就要给 prefix：GNUInstallDirs 的 CMAKE_INSTALL_FULL_*
            # 在 configure 期按当时 prefix 算成绝对路径写进 install 规则。
            '-DCMAKE_INSTALL_PREFIX="{}"'.format(self.package_folder),
            # sobjectizer 上游开关：动态库 so.5.7.4 + 静态库 so_s.5.7.4 都要出，
            # BUILD_TESTS=ON 才 enable_testing() 并注册 319 个上游单测
            # （实测口径：构建树 add_test 条目 319 = ctest -N Total Tests 319）。
            "-DSOBJECTIZER_BUILD_SHARED=ON",
            "-DSOBJECTIZER_BUILD_STATIC=ON",
            "-DSOBJECTIZER_INSTALL=ON",
            "-DBUILD_TESTS=ON",
        ]
        _rl = self._llvm_ranlib(toolchain)
        if _rl:
            defs.append('-DCMAKE_RANLIB="{}"'.format(_rl))
        # 无外部依赖（SObjectizer 只用 C++17 标准库 + pthread），不需要 find-deps 预加载。
        self.run('cmake -B "{}" -S "{}" {}'.format(bdir, src, " ".join(defs)))
        # 尊重 conan 的 tools.build:jobs（CI 会设小值）。上游 BUILD_TESTS=ON 会产出
        # 319 个测试可执行文件 + 2 个库，裸 `-j` 会起满核并把这台 11GB 的机器打爆
        # （gmake 报 Error 137/143，即被 OOM killer 杀掉）。这里取 min(jobs, 8)。
        self.run('cmake --build "{}" -j {}'.format(bdir, self._build_jobs()))

        # ── 上游 ctest（先签名测试二进制与构建树 .so，再运行；E077/E083）──
        self._sign_build_artifacts(bdir)
        old = os.environ.get("LD_LIBRARY_PATH", "")
        os.environ["LD_LIBRARY_PATH"] = bdir + (os.pathsep + old if old else "")
        # 串行执行 + 宽松超时：上游测试内部用墙钟 run_with_time_limit() 看门狗，
        # 并行跑会在模拟环境下互相饿死从而误判超时（详见 notes.md）。
        #
        # `-E` 排除项见 _ctest_exclude()：只在【用户态模拟器】下排除
        # spinlocks.llvm_inspired_test —— 它是纯自旋锁压力测试，在 qemu-user
        # 下会活锁（qemu 无 guest 内核调度器）。真机/CI 上该用例照常执行。
        excl = self._ctest_exclude()
        cmd = ('ctest --test-dir "{}" --output-on-failure --no-tests=error '
               '--timeout 900 -j1').format(bdir)
        if excl:
            self.output.info("CTest 排除（仅用户态模拟器下生效）: {}".format(excl))
            cmd += ' -E "{}"'.format(excl)
        self.run(cmd)

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    # OHOS 签名相关工具的候选位置。设备/CI 镜像把 binary-sign-tool 装在
    # /data/service/hnp/bin，但 llvm-objcopy/llvm-readelf 在有的镜像里并不在那
    # （实测本机 /data/service/hnp/bin 只有 bash/clang/clang++/binary-sign-tool），
    # 所以 objcopy/readelf 需要多路径探测 + PATH 兜底。
    _SIGNER_CANDIDATES = (
        "/data/service/hnp/bin/binary-sign-tool",
        "/usr/bin/binary-sign-tool",
    )
    _LLVM_BIN_CANDIDATES = (
        "/data/service/hnp/bin",
        "/root/ohpc/sdk/ohos-6.0/native/llvm/bin",
    )

    def _find_tool(self, name, extra_dirs):
        for d in extra_dirs:
            p = os.path.join(d, name)
            if os.path.isfile(p) and os.access(p, os.X_OK):
                return p
        return shutil.which(name) or ""

    def _sign_tools(self):
        signer = self._find_tool("binary-sign-tool", self._SIGNER_CANDIDATES)
        objcopy = self._find_tool("llvm-objcopy", self._LLVM_BIN_CANDIDATES)
        readelf = self._find_tool("llvm-readelf", self._LLVM_BIN_CANDIDATES)
        if not objcopy:
            objcopy = self._find_tool("objcopy", self._LLVM_BIN_CANDIDATES)
        return signer, objcopy, readelf

    def _sign_targets(self, targets):
        """给一批 ELF 加自签名代码签名块（幂等）。

        鸿蒙 PC 要求 dlopen 的 .so 与被 exec 的可执行文件带 .codesign，否则
        Permission denied / Operation not permitted。两个必要的坑：

        1. binary-sign-tool 在 .codesign **已存在**时不会覆盖，而是直接失败：
             [Error] [sign_elf.cpp] [WriteCodeSignBlock] [135] [SignElf]
                     .codesign section already exists
             [Error] ... [SignElf] sign elf failed
           所以签名前必须先用 objcopy --remove-section .codesign 剥掉旧块。
           原实现写的是 `objcopy ... 2>/dev/null || true`，看起来容错，实际是
           把「工具根本不存在（rc=127）」也一起吞掉，于是剥除从未发生、
           签名必然失败 —— 这正是本配方 package() 阶段真实踩到的失败：
             ERROR: sobjectizer/5.7.4: Error in package() method, line 234
             self._sign_targets(targets)
             ConanException: Error 1 while executing
        2. build() 已对构建树签过一次，package() 再签 install 出来的副本时，
           副本会带着构建树那次留下的 .codesign —— 正是上面 1 的场景。
        """
        signer, objcopy, readelf = self._sign_tools()
        if not signer:
            self.output.warning("找不到 binary-sign-tool，跳过代码签名"
                                "（真机上 dlopen/exec 可能被拒）")
            return
        for f in targets:
            if os.path.islink(f) or not os.path.isfile(f):
                continue
            if not self._is_elf(f):
                continue
            # 先剥掉可能存在的旧签名块，否则 signer 报 ".codesign section already exists"
            has_old = True
            if readelf:
                try:
                    out = subprocess.run([readelf, "-S", f],
                                         capture_output=True, text=True)
                    has_old = ".codesign" in (out.stdout or "")
                except OSError:
                    has_old = True
            if has_old and objcopy:
                subprocess.run([objcopy, "--remove-section", ".codesign", f],
                               capture_output=True)
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def _sign_build_artifacts(self, bdir):
        """签名构建树内的测试可执行文件与 .so，否则 OHOS 上 ctest 报 Operation not permitted（E077）。
        SObjectizer 的单测可执行文件叫 _unit.test.*，直接铺在构建树里。"""
        targets = glob.glob(os.path.join(bdir, "**", "*.so"), recursive=True)
        targets += glob.glob(os.path.join(bdir, "**", "*.so.*"), recursive=True)
        for name in os.listdir(bdir) if os.path.isdir(bdir) else []:
            p = os.path.join(bdir, name)
            if os.path.isfile(p) and not os.path.islink(p) and self._is_elf(p):
                targets.append(p)
        self._sign_targets(targets)

    # 上游 install 出来的是【带版本号】的文件名：
    #     lib/libso.5.7.4.so      共享库
    #     lib/libso_s.5.7.4.a     静态库
    # 上游自带的 sobjectizer-config.cmake 里直接写这两个精确文件名，所以上游
    # 自己的 find_package 能工作。但 conan 的 CMakeDeps 会按 cpp_info.libs 拼
    # `lib<name>.so` / `lib<name>.a` 去找，即 libso.so / libso_s.a，找不到就报：
    #     Library 'so_s' not found in package.
    # 因此在 package() 里补两个不带版本号的软链（不复制，避免包体积翻倍），
    # 让 CMakeDeps、裸 -lso / -lso_s 的消费者以及上游 config 三条路径都能用。
    _LIB_ALIASES = {
        "libso.5.7.4.so": "libso.so",
        "libso_s.5.7.4.a": "libso_s.a",
    }

    def _add_unversioned_lib_aliases(self):
        libdir = os.path.join(self.package_folder, "lib")
        for real, alias in self._LIB_ALIASES.items():
            src = os.path.join(libdir, real)
            dst = os.path.join(libdir, alias)
            if not os.path.exists(src):
                continue
            if os.path.islink(dst) or os.path.exists(dst):
                os.remove(dst)
            os.symlink(real, dst)

    def package(self):
        bdir = os.path.join(self.build_folder, "build-ohos")
        self.run('cmake --install "{}" --prefix "{}"'.format(bdir, self.package_folder))
        # 补不带版本号的库别名（CMakeDeps / 裸 -l 消费者需要；见 _LIB_ALIASES 注释）
        self._add_unversioned_lib_aliases()
        # 鸿蒙 PC XPM 要求 dlopen 的 .so 与被 exec 的可执行文件都要代码签名，
        # 否则报 Permission denied / Operation not permitted。
        # ① lib/ 的 .so  ② bin/ 的 ELF 可执行文件
        targets = glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so"), recursive=True)
        targets += glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so.*"), recursive=True)
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in os.listdir(bindir):
                p = os.path.join(bindir, name)
                if os.path.isfile(p) and not os.path.islink(p) and self._is_elf(p):
                    targets.append(p)
        self._sign_targets(targets)

    def package_info(self):
        """导出上游 install 产物的两个目标：SharedLib 与 StaticLib。

        上游 dev/so_5/CMakeLists.txt 用 `EXPORT_NAME SharedLib` / `StaticLib`
        （加了 `sobjectizer::` 命名空间）导出两个目标，并在
        `lib/cmake/sobjectizer/sobjectizer-targets.cmake` 里提供。conan 默认只把
        整个包报成一个组件，若只写 cmake_target_name=sobjectizer::SharedLib，
        CMakeDeps 只会生成 SharedLib，消费者写 StaticLib 就报：
            Target "..." links to: sobjectizer::StaticLib
            but the target was not found.
        因此这里显式建两个组件，各自指向对应的库文件与编译定义，让
        find_package + CMakeDeps 的消费者两个目标都能用。
        """
        self.cpp_info.set_property("cmake_file_name", "sobjectizer")

        # 共享库组件（上游 libso.<ver>.so，导出名 SharedLib）
        self.cpp_info.components["shared"].set_property(
            "cmake_target_name", "sobjectizer::SharedLib")
        self.cpp_info.components["shared"].libs = ["so"]

        # 静态库组件（上游 libso_s.<ver>.a，导出名 StaticLib）。
        # 上游给静态目标 PUBLIC 定义了 SO_5_STATIC_LIB，是独立于共享库的
        # 编译配置，消费者必须同样拿到这个定义才能正确编译。
        self.cpp_info.components["static"].set_property(
            "cmake_target_name", "sobjectizer::StaticLib")
        self.cpp_info.components["static"].libs = ["so_s"]
        self.cpp_info.components["static"].defines = ["SO_5_STATIC_LIB"]

        if self.settings.os in ("Linux", "OHOS", "Android"):
            self.cpp_info.components["shared"].system_libs = ["pthread"]
            self.cpp_info.components["static"].system_libs = ["pthread"]
