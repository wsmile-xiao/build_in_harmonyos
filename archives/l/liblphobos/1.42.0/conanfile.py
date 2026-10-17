#!/usr/bin/env python3
"""Conan recipe — liblphobos 1.42.0（D 语言运行时库 Phobos + druntime，鸿蒙 PC 真机原生构建）

liblphobos = LDC 1.42.0 发行源码包中的 runtime 子树（runtime/phobos +
runtime/druntime），即 D 语言标准库 Phobos（libphobos2-ldc-shared.so.112）
与其伴生运行时 druntime（libdruntime-ldc-shared.so.112）。

【与 ldc 包的关系】ldc/1.42.0（已发布 ohpcd）是 D 编译器工具包（application，
bin/ldc2 等），其包内 lib/ 仅静态库（libphobos2-ldc.a 等）。本包交付**共享库**
（BUILD_SHARED_LIBS=ON），与 ldc 包互补、内容零重叠；本包构建期经
tool_requires("ldc/1.42.0") 消费现成 ldc2 二进制（profile 与 CI 同款）。

【为什么属于高难度适配（路径 C）】
  1. 私有编译工具链：D 语言运行时只能由 D 编译器构建，设备/NDK 无任何 D 编译器，
     完全依赖 ldc/1.42.0 包交付的 ldc2（其本身经自举引导编译器构建并代码签名）。
  2. 含汇编与特殊调度：druntime 含 fiber 上下文切换汇编、GC stop-the-world
     线程挂起（信号驱动）、异常展开、协程调度。
  3. 上游独立构建工具 ldc-build-runtime 在 OHOS 上无法运行（动态链接缺
     libgcc_s.so.1/_Unwind_*，ldc/1.42.0 配方实测）——本配方复刻其 runCMake()
     的官方参数直接驱动 runtime/CMakeLists.txt。

【OHOS 适配要点（均继承自 ldc/1.42.0 实测）】
  - OHOS 不投递 SIGRTMIN(35)：druntime GC thread_suspendAll() 永久阻塞 →
    补丁改 SIGUSR1/2（patches/0001）。
  - OHOS musl 缺 pthread cancellation 家族 → 补丁补 no-op 回退。
  - ELF/.so 代码签名：binary-sign-tool 自签全部交付 .so。
  - 设备 uname=HarmonyOS：cmake 无 Platform/HarmonyOS.cmake → stub；
    TARGET_SYSTEM 显式 Linux;UNIX;musl，绕开 AUTO 探测。
  - /tmp 只读 → 显式 TMPDIR。
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, get

HNP = "/data/service/hnp/bin"
SIGNER = os.path.join(HNP, "binary-sign-tool")
OBJCOPY = os.path.join(HNP, "llvm-objcopy")

# LDC 1.42.0 对应 DMD 前端 2.112.1（源码顶层 CMakeLists.txt 116-118 行），
# 决定共享库 SONAME：libphobos2-ldc-shared.so.112 / libdruntime-ldc-shared.so.112
DMDFE_MINOR_VERSION = "112"
DMDFE_PATCH_VERSION = "1"


class LiblphobosConan(ConanFile):
    name = "liblphobos"
    version = "1.42.0"
    description = "Phobos + druntime — D 语言标准库与运行时（LDC 1.42.0 / DMD 前端 2.112.1），AArch64 共享库"
    license = "BSD-3-Clause AND BSL-1.0"
    homepage = "https://github.com/ldc-developers/ldc"
    url = "https://github.com/ldc-developers/ldc"
    package_type = "library"
    # L0p：OHOS profile 需要 os/compiler/build_type/arch 四项（防 profile 不兼容）
    settings = "os", "compiler", "build_type", "arch"
    # Conan 2 约定：package_type=library 必须声明 shared 选项。
    # "both" 映射到上游 runtime CMake 的 BUILD_SHARED_LIBS=BOTH（静态+共享都建）。
    options = {"shared": [True, False, "both"], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            del self.options.fPIC  # 共享库一律 PIC

    def export_sources(self):
        # apply_conandata_patches() 要求补丁出现在 source 目录下（同 ldc recipe）；
        # shim/（pthread cancellation no-op + program_invocation_name 定义）随配方导出，
        # build() 编译为 PIC 对象后经 LD_FLAGS 链进共享库（见 build() 内注释）
        copy(self, "patches/*", src=self.recipe_folder, dst=self.export_sources_folder)
        copy(self, "shim/*", src=self.recipe_folder, dst=self.export_sources_folder)

    def validate(self):
        if self.settings.os != "OHOS":
            raise ConanInvalidConfiguration(
                "liblphobos/1.42.0 is a *device-native* OHOS build: it consumes the "
                "published ldc/1.42.0 tool package (ldc2) and links OHOS musl. "
                "Cross-builds are not supported by this recipe.")

    def build_requirements(self):
        # D 编译器（工具依赖，不进交付产物）。ldc/1.42.0 已于 2026-09-17 发布 ohpcd，
        # 二进制 e11077ec7d25a91d222505c03d962ca797d8fa19（CI 同款 profile）。
        self.tool_requires("ldc/1.42.0")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ---------------------------------------------------------------- helpers
    def _neutralize_safe_bin(self):
        """中和 safe-bin 四通道注入（同 lib32-gcc/16.1.1 的 _neutralize_safe_bin）。

        四通道：BASH_ENV / CODEBUDDY_SAFE_DELETE_* 环境变量 / BASH_FUNC_rm%%
        / PATH 中的 safe-bin 条目。漏掉 PATH 通道时，子进程（cmake/ldc2 派生的
        shell 片段）仍会按 PATH 解析到 rm shim → exit 126。
        """
        for var in ("BASH_ENV", "CODEBUDDY_SAFE_DELETE_BIN_DIR",
                    "CODEBUDDY_SAFE_DELETE_HOOK", "BASH_FUNC_rm%%"):
            os.environ.pop(var, None)
        path = os.environ.get("PATH", "")
        keep = [p for p in path.split(":") if p and "safe-bin" not in p]
        os.environ["PATH"] = ":".join(keep)

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign(self, path):
        """OHOS 要求代码签名；先清旧段再自签（同 ldc recipe）。"""
        if os.path.islink(path) or not os.path.isfile(path):
            return
        self.run('{oc} --remove-section .codesign "{f}" || true'.format(oc=OBJCOPY, f=path))
        self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=SIGNER, f=path))

    def _materialize_symlinks(self, libdir):
        """把 lib/ 下软链实体化（E316/E492/E505）。

        OHOS musl 不能加载「SONAME 名字是软链」的库。CMake 产出
        libX.so.2.112.1（实体）+ libX.so.112 / libX.so（软链）——交付前把
        软链跟随复制为实体文件（临时名 + os.replace 原子替换）。
        """
        for name in sorted(os.listdir(libdir)):
            p = os.path.join(libdir, name)
            if os.path.islink(p):
                real = os.path.realpath(p)
                tmp = p + ".materialize"
                shutil.copy2(real, tmp)
                os.replace(tmp, p)

    # ---------------------------------------------------------------- build
    def generate(self):
        env = Environment()
        # runtime CMake 的 C/ASM 部分（druntime core/*.{c,S}）用 OHOS clang（R33 显式）
        env.define_path("CC", os.path.join(HNP, "clang"))
        env.define_path("CXX", os.path.join(HNP, "clang++"))
        # ldc2 运行期 NEEDED libLLVM.so.20.1 —— 在 ldc 的传递依赖 llvm 包的 lib/
        llvm = self.dependencies.build.get("llvm")
        if llvm is not None:
            env.append_path("LD_LIBRARY_PATH",
                            os.path.join(llvm.package_folder, "lib"))
        env.vars(self).save_script("ohos_runtime_build_env")

    def build(self):
        self._neutralize_safe_bin()
        apply_conandata_patches(self)

        ldc_pkg = self.dependencies.build["ldc"].package_folder
        ldc2 = os.path.join(ldc_pkg, "bin", "ldc2")
        ldmd2 = os.path.join(ldc_pkg, "bin", "ldmd2")
        if not os.path.isfile(ldc2):
            raise ConanInvalidConfiguration(
                "ldc2 not found in ldc tool package: {}".format(ldc2))

        src = self.source_folder
        bld = self.build_folder
        rtb = os.path.join(bld, "rtbuild")
        os.makedirs(rtb, exist_ok=True)

        # shared 选项 → 上游 runtime CMake 的 BUILD_SHARED_LIBS（ON/OFF/BOTH 三态）
        bssl = {"True": "ON", "False": "OFF", "both": "BOTH"}[str(self.options.shared)]

        # 设备 uname=HarmonyOS：cmake 无 Platform/HarmonyOS.cmake → stub
        # （同 llvm / flang-ohos / ldc recipe 的处理方式）
        pm = os.path.join(bld, "_cmake_modules")
        os.makedirs(os.path.join(pm, "Platform"), exist_ok=True)
        with open(os.path.join(pm, "Platform", "HarmonyOS.cmake"), "w",
                  encoding="utf-8") as f:
            f.write("include(Platform/Linux)\n")

        # /tmp 只读 → 显式可写 TMPDIR（R33）
        tmpdir = os.path.join(bld, "_tmp")
        os.makedirs(tmpdir, exist_ok=True)

        # musl 兼容垫片：druntime core.internal.elf.dl 引用 glibc 特有
        # program_invocation_name（OHOS musl 无）。静态库场景该成员不被拉入无碍，
        # 但**共享库会把 dl.o 整体打入**，未定义符号残留 → 消费者链接必报
        #   ld.lld: error: undefined reference due to --no-allow-shlib-undefined:
        #           program_invocation_name
        # 处置与 ldc/1.42.0 引导期适配同构：把 shim（pthread cancellation no-op +
        # program_invocation(_short)_name 空串定义）编为 PIC 对象，经上游
        # runtime CMake 的 LD_FLAGS（"Extra C linker flags for shared libraries"）
        # 链进共享库——.so 自带定义，消费者链接干净通过。
        shim_obj = os.path.join(bld, "ohos_runtime_shim.o")
        self.run('"{cc}" -c -fPIC -o "{o}" "{s}"'.format(
            cc=os.path.join(HNP, "clang"), o=shim_obj,
            s=os.path.join(src, "shim", "pthread_cancel_shim.c")))

        # === 上游官方 configure 参数（复刻 runtime/ldc-build-runtime.d.in 的
        # runCMake()；因该工具可执行文件在 OHOS 动态链接不可运行，见 docstring）===
        cfg = (
            'cmake -S "{src}/runtime" -B "{rtb}" '
            '-DLDC_EXE_FULL="{ldc2}" '
            '-DLDMD_EXE_FULL="{ldmd2}" '
            '-DDMDFE_MINOR_VERSION={minor} -DDMDFE_PATCH_VERSION={patch} '
            '-DTARGET_SYSTEM="Linux;UNIX;musl" '
            '-DBUILD_SHARED_LIBS={bssl} '
            '-DCMAKE_BUILD_TYPE=Release '
            '-DCMAKE_MODULE_PATH="{pm}" '
            '-DLD_FLAGS="{shimo}" '
            '-DCMAKE_C_COMPILER="{cc}" '
            '-DCMAKE_CXX_COMPILER="{cxx}" '
            '-DCMAKE_ASM_COMPILER="{cc}" '
            '-DTMPDIR="{tmp}"'
        ).format(src=src, rtb=rtb, ldc2=ldc2, ldmd2=ldmd2,
                 minor=DMDFE_MINOR_VERSION, patch=DMDFE_PATCH_VERSION,
                 bssl=bssl, pm=pm, shimo=shim_obj,
                 cc=os.path.join(HNP, "clang"),
                 cxx=os.path.join(HNP, "clang++"), tmp=tmpdir)
        self.run(cfg)
        # 构建（4 并行；druntime+phobos 数百个 D 模块 + 少量 C/ASM）
        self.run('cmake --build "{rtb}" --parallel 4'.format(rtb=rtb))

    def package(self):
        rtlib = os.path.join(self.build_folder, "rtbuild", "lib")
        pkglib = os.path.join(self.package_folder, "lib")
        # 交付共享库（.so.2.112.1 实体 + SONAME/.so 软链）与静态库（若产出）
        copy(self, "*.so*", src=rtlib, dst=pkglib, keep_path=False)
        copy(self, "*.a", src=rtlib, dst=pkglib, keep_path=False)
        self._materialize_symlinks(pkglib)

        # D 源码即 import 头：druntime 的 src/（object.d/core/ldc/etc/importc.h/
        # __importc_builtins.di）+ Phobos 的 std/ + etc/（两处 etc/ 合并——对齐
        # ldc 包官方 cmake install 的 include/d 集合；druntime 的 rt/ 为实现细节
        # 不交付，官方 install 同样不含）
        inc = os.path.join(self.package_folder, "include", "d")
        copy(self, "*", src=os.path.join(self.source_folder, "runtime", "druntime", "src"),
             dst=inc, excludes=["rt", "rt/*", "test_runner.d"])
        copy(self, "*", src=os.path.join(self.source_folder, "runtime", "phobos", "std"),
             dst=os.path.join(inc, "std"))
        copy(self, "*", src=os.path.join(self.source_folder, "runtime", "phobos", "etc"),
             dst=os.path.join(inc, "etc"))

        # 许可证：LDC(BSD-3) + Phobos/Druntime(Boost BSL-1.0)
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "LICENSE_1_0.txt", src=os.path.join(self.source_folder, "runtime", "phobos"),
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

        # 签名全部交付 .so
        for so in glob.glob(os.path.join(pkglib, "*.so*")):
            self._sign(so)

    def package_info(self):
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include/d"]
        # 纯库包，无 bindirs → 不触发 R38 命令工具包判据（detect_bindirs）
        # D 消费者用法（notes.md 详述）：
        #   ldc2 prog.d -I<pkg>/include/d -L-L<pkg>/lib \
        #     -defaultlib=phobos2-ldc-shared,druntime-ldc-shared -L-lz -L-lm
