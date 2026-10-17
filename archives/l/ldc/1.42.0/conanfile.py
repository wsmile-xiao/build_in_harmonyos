#!/usr/bin/env python3
"""Conan recipe — ldc 1.42.0 (cmake, 鸿蒙 PC 真机原生编译)

LDC = LLVM D Compiler，D 语言的 LLVM 后端编译器工具链。

【为什么属于高难度适配（路径 C）】
  1. 自举（bootstrap）：LDC 前端是 D 写的（dmd/ 下 109 个 .d 文件），必须由 D 编译器编译；
     而设备/NDK 不提供任何 D 编译器，且 D 无法从 C/C++ 侧自举（LLVM 不含 D 前端）。
     本包因此在构建期引入上游预编译 ldc2 作引导编译器（见 conandata.yml 的 bootstrap）。
  2. 依赖 LLVM（find_package(LLVM 15.0 REQUIRED)，30+ 组件）——巨型依赖。
  3. 运行时含汇编与特殊调度：druntime 有 fiber 上下文切换汇编、GC、异常、协程。
  4. 全量测试校验成本高：druntime + Phobos 共 236 个测试模块。

【OHOS 适配要点（均经实测）】
  - ELF 代码签名：OHOS 要求被 exec 的 ELF 与 dlopen 的 .so 都签名，否则
    Permission denied / rc=126。引导编译器与所有产物均须 binary-sign-tool 自签。
  - OHOS 不投递 SIGRTMIN(35)：实测自投递与跨线程投递均不触发处理函数，
    而 SIGRTMIN+1(36)/37..40/SIGUSR1(10)/SIGUSR2(12) 正常；druntime 的 GC
    thread_suspendAll() 恰用 SIGRTMIN，会永久阻塞 → 运行时死锁。补丁改 SIGUSR1/2。
  - OHOS musl 缺 pthread cancellation 家族：druntime core.thread.osthread 引用
    pthread_setcancelstate 等导致链接失败，补丁补 no-op 回退。
  - /tmp 只读：cmake/编译器需 TMPDIR 指向可写目录。
  - 设备 uname=HarmonyOS，cmake 无 Platform/HarmonyOS.cmake，
    LLVM 的 config.guess 亦不识别 → 须 stub（同 llvm/flang-ohos recipe）。
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, get

HNP = "/data/service/hnp/bin"
SIGNER = os.path.join(HNP, "binary-sign-tool")
OBJCOPY = os.path.join(HNP, "llvm-objcopy")


class LdcConan(ConanFile):
    name = "ldc"
    version = "1.42.0"
    description = "LDC — LLVM D Compiler（D 语言编译器工具链，含 druntime/Phobos），AArch64"
    license = "BSD-3-Clause AND BSL-1.0"
    homepage = "https://github.com/ldc-developers/ldc"
    url = "https://github.com/ldc-developers/ldc"
    # 编译器工具链：与同族的 flang-ohos 一致，作 application 供下游 tool_requires。
    package_type = "application"
    # L0p：OHOS profile 需要 os/compiler/build_type/arch 四项（防 profile 不兼容）
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        # apply_conandata_patches() 要求补丁出现在 **source 目录**下，而 source 目录
        # 只包含 export_sources 的内容 + 下载源码。不导出会报：
        #   FileNotFoundError: .../s/patches/0001-ohos-thread-gc-signals.patch
        copy(self, "patches/*", src=self.recipe_folder, dst=self.export_sources_folder)
        # 引导编译器链接用的垫片源码亦须随配方导出
        copy(self, "shim/*", src=self.recipe_folder, dst=self.export_sources_folder)

    def configure(self):
        if self.settings.os != "OHOS":
            raise ConanInvalidConfiguration(
                "ldc/1.42.0 is a *device-native* OHOS build: it links against the "
                "OHOS LLVM package and requires a signed bootstrap D compiler. "
                "Cross-builds are not supported by this recipe."
            )

    def requirements(self):
        # libLLVM 是硬依赖：LDC 的 CMake 用 find_package(LLVM 15.0 REQUIRED)，
        # 运行期 ldc2 亦 NEEDED libLLVM.so。llvm recipe 以 cmake_find_mode=none
        # 暴露自带 LLVMConfig.cmake，消费方经 CMAKE_PREFIX_PATH 找到。
        self.requires("llvm/20.1.0")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # 引导编译器：解到 _bootstrap/，稍后在 build() 里签名后使用。
        bdir = os.path.join(self.source_folder, "_bootstrap")
        os.makedirs(bdir, exist_ok=True)
        get(self, **self.conan_data["bootstrap"], destination=bdir, strip_root=True)

    # 注：不使用 cmake_layout()。不调用 layout() 时 CMake helper 直接用 build_folder
    # 作为构建目录，本配方在此布局下已验证可用（174/174 步、test_package 通过）。
    # cmake_layout() 会改写为 build/<build_type> 结构并附加 CMakePresets 约定，
    # 对本包无收益，故保持默认。

    # ---------------------------------------------------------------- helpers
    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign(self, path):
        """OHOS 要求代码签名；先清旧段再自签。"""
        if os.path.islink(path) or not os.path.isfile(path):
            return
        self.run('{oc} --remove-section .codesign "{f}" || true'.format(oc=OBJCOPY, f=path))
        self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=SIGNER, f=path))

    def _bootstrap_compiler(self):
        """返回签名后的引导编译器路径。

        用包内的 **ldmd2** 而不是 ldc2：LDC 的 CMake 在 D_COMPILER_ID=LDMD 时按 DMD
        方言发标志（实测有 `-inline`、`-version=IN_LLVM`），而 `ldc2` 在非 DMD 兼容
        模式下不认这两个（报 "Unknown command line argument '-inline'" 与
        "for the --version option: does not allow a value!"），导致 dmd/*.d 前端
        编译失败。`ldmd2` 是 LDC 提供的 DMD 命令行兼容入口，实测两者都接受。
        """
        bootdir = os.path.join(self.source_folder, "_bootstrap", "bin")
        ldmd2 = os.path.join(bootdir, "ldmd2")
        if not os.path.isfile(ldmd2):
            raise ConanInvalidConfiguration(
                "bootstrap compiler not found at {}; check conandata.yml".format(ldmd2))
        # ldc2 亦一并签名：LDC 自举时可能自查同目录的 ldc2。
        for name in ("ldmd2", "ldc2"):
            p = os.path.join(bootdir, name)
            if os.path.isfile(p):
                self.output.info("signing bootstrap compiler {}".format(name))
                self._sign(p)
        return ldmd2

    # ---------------------------------------------------------------- build
    def generate(self):
        tc = CMakeToolchain(self)
        tc.generator = "Ninja"
        # CMAKE_BUILD_TYPE 由 CMakeToolchain 依 settings.build_type 自动生成
        # （profile 里为 Release），不再硬编码，否则会忽略 profile 设置。
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        # R33：不继承环境，显式固定工具链绝对路径
        tc.variables["CMAKE_C_COMPILER"] = os.path.join(HNP, "clang")
        tc.variables["CMAKE_CXX_COMPILER"] = os.path.join(HNP, "clang++")
        # LDC 用自己的 cmake/Modules/FindLLVM.cmake，它靠 **llvm-config** 而非
        # LLVMConfig.cmake 取 LLVM 信息。若不指定，find_program 会命中设备 SDK 里的
        # /data/service/hnp/bin/llvm-config，而那个 llvm-config 指向 SDK 自带的 LLVM
        # 安装（缺少 libLLVMLoongArch*/LineEditor 等本仓库 llvm 包未构建的组件），
        # 报一串 "llvm-config: error: missing: ..." 后 FATAL。
        # 故显式指向本仓 llvm 依赖的 bin/llvm-config 与根目录。
        llvm_pkg = self.dependencies["llvm"].package_folder
        llvm_libdir = os.path.join(llvm_pkg, "lib").replace("\\", "/")
        tc.variables["LLVM_ROOT_DIR"] = llvm_pkg.replace("\\", "/")
        tc.variables["LLVM_CONFIG"] = os.path.join(llvm_pkg, "bin", "llvm-config").replace("\\", "/")
        # 构建期工具（gen_gccbuiltins 等）在 configure/build 阶段就要被**执行**，
        # 它们链接 libLLVM.so.20.1。若不告诉链接器去哪找，运行时报：
        #   Error loading shared library libLLVM.so.20.1
        #   Error relocating ...gen_gccbuiltins: _ZN4llvm...: symbol not found
        # 故把 LLVM 的 lib 目录写进 BUILD_RPATH（仅影响构建期，不进最终产物的 RPATH）。
        tc.variables["CMAKE_BUILD_RPATH"] = llvm_libdir
        tc.variables["CMAKE_BUILD_RPATH_USE_ORIGIN"] = "ON"
        tc.generate()
        # LDC 的 CMakeLists 自行改写 RPATH，CMake 的 BUILD_RPATH 对 bin/ldc2 不生效
        # （实测产物无 RUNPATH）。构建中期新编出的 ldc2 会被立即执行（用于编译
        # druntime/Phobos），运行时找不到 libLLVM.so.20.1 即失败：
        #   Error loading shared library libLLVM.so.20.1
        # 故用 Environment 在**构建环境**里补 LD_LIBRARY_PATH（只影响本包构建）。
        env = Environment()
        env.append_path("LD_LIBRARY_PATH", llvm_libdir)
        env.vars(self).save_script("ohos_ld_library_path")

    def _build_bootstrap_shim(self):
        """编译供**引导编译器**链接用的 OHOS 垫片，返回其 .a 路径。

        上游预编译 ldc2 自带的 libdruntime-ldc.a 引用 pthread_setcancelstate 家族
        （OHOS musl 不导出）。LDC 的 CMake 在 configure 阶段会用引导编译器链接若干
        探测用 D 程序（如 ExtractDMDSystemLinker），缺该家族即链接失败：
          ld.lld: error: undefined symbol: pthread_setcancelstate
        故按 -L 喂入本垫片。垫片只服务引导阶段，不进入交付产物。
        """
        # 注意：export_sources() 把 shim/ 复制到 **source 文件夹**，而 build() 阶段
        # self.recipe_folder 指向的是 export 文件夹（只有 conanfile.py + conandata.yml），
        # 用 recipe_folder 会报 "No such file or directory .../shim/pthread_cancel_shim.c"。
        src = os.path.join(self.source_folder, "shim", "pthread_cancel_shim.c")
        out = os.path.join(self.build_folder, "_bootstrap_shim")
        os.makedirs(out, exist_ok=True)
        obj = os.path.join(out, "pthread_cancel_shim.o")
        lib = os.path.join(out, "libohos_bootstrap_shim.a")
        cc = os.path.join(HNP, "clang")
        self.run('"{cc}" -c -fPIC -o "{o}" "{s}"'.format(cc=cc, o=obj, s=src))
        self.run('"{ar}" rcs "{l}" "{o}"'.format(ar=os.path.join(HNP, "llvm-ar"), l=lib, o=obj))
        return lib

    def build(self):
        apply_conandata_patches(self)
        boot = self._bootstrap_compiler()
        shim = self._build_bootstrap_shim()

        src = self.source_folder
        # 设备 uname=HarmonyOS：LLVM 的 config.guess 与 cmake 的 platform 探测都不认。
        # 同 llvm / flang-ohos recipe 的处理方式。
        guess = os.path.join(src, "cmake", "config.guess")
        os.makedirs(os.path.dirname(guess), exist_ok=True)
        with open(guess, "w", encoding="utf-8") as f:
            f.write("#!/bin/sh\necho aarch64-unknown-linux-ohos\n")
        os.chmod(guess, 0o755)
        pm = os.path.join(self.build_folder, "_cmake_modules")
        os.makedirs(os.path.join(pm, "Platform"), exist_ok=True)
        with open(os.path.join(pm, "Platform", "HarmonyOS.cmake"), "w", encoding="utf-8") as f:
            f.write("include(Platform/Linux)\n")

        # /tmp 只读 → 指定可写 TMPDIR（R33：显式给出，不依赖环境）
        tmpdir = os.path.join(self.build_folder, "_tmp")
        os.makedirs(tmpdir, exist_ok=True)

        cmake = CMake(self)
        cmake.configure(variables={
            # 引导编译器：自举的关键
            "D_COMPILER": boot,
            # LDC 的 cmake/Modules/FindDCompiler.cmake 仅凭**文件名**判定宿主 D 编译器
            # （只认 dmd / ldmd2 / gdmd），否则 FATAL_ERROR "Unsupported D compiler
            # filename"。引导二进制名为 ldc2，故必须显式给出 D_COMPILER_ID；
            # 取 LDMD：ldc2 接受 DMD 风格命令行，与上游 ldc2 自举的口径一致。
            "D_COMPILER_ID": "LDMD",
            # -L 把参数原样转发给链接器：把 OHOS 垫片（pthread cancellation 家族 +
            # program_invocation_name）喂给引导编译器，否则它链接任何 D 程序都会因
            # libdruntime-ldc.a 引用 pthread_setcancelstate 而失败。
            "D_COMPILER_FLAGS": "-O -release -L{}".format(shim),
            # 连同运行时一起构建 → ldc2 开箱可编可跑（test_package 需真实执行）
            "LDC_BUILD_RUNTIME": "ON",
            # 关掉非必需组件，缩小构建面
            "LDC_WITH_MLIR": "OFF",
            "LDC_ENABLE_PLUGINS": "OFF",
            "LDC_DYNAMIC_COMPILE": "OFF",
            "LDC_INSTALL_LTOPLUGIN": "OFF",
            "LDC_BUNDLE_LLVM_TOOLS": "OFF",
            "LDC_ENABLE_ASSERTIONS": "OFF",
            "LDC_LINK_MANUALLY": "OFF",
            # 真机原生：不设 CMAKE_SYSTEM_NAME（交叉编译会让 tblgen 等构建期工具无法运行）
            "CMAKE_MODULE_PATH": pm,
            "TMPDIR": tmpdir,
        })
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE*", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        # 统一签名：bin/ 下的 ELF 与 lib/ 下的 .so
        targets = []
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in os.listdir(bindir):
                p = os.path.join(bindir, name)
                if os.path.isfile(p) and not os.path.islink(p) and self._is_elf(p):
                    targets.append(p)
        targets += glob.glob(os.path.join(self.package_folder, "lib", "*.so"))
        targets += glob.glob(os.path.join(self.package_folder, "lib", "*.so.*"))
        for f in targets:
            self._sign(f)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]
        # 消费方：DC=ldc2（D 编译器约定变量名）；运行时/构建时都需 lib/ 在库里路径上
        self.buildenv_info.define_path("DC", os.path.join(self.package_folder, "bin", "ldc2"))
        self.buildenv_info.define_path("DMD", os.path.join(self.package_folder, "bin", "ldc2"))
        for env in (self.runenv_info, self.buildenv_info):
            env.append_path("LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))
            env.append_path("PATH", os.path.join(self.package_folder, "bin"))
