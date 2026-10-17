#!/usr/bin/env python3
"""Conan recipe — liblapacke 0.3.30 (HarmonyOS PC / os=OHOS arch=armv8)

LAPACKE（LAPACK 的标准 C 接口）无独立上游发布：0.3.x 版本号跟随
OpenMathLib/OpenBLAS（本版内嵌 LAPACK 3.12.0 与其 LAPACKE C 接口）。

交付形态（同 openblas 0.3.34 已验证先例）：在鸿蒙 PC 真机上用 tool_requires
的 flang-ohos/20.1.0 全量 Fortran 构建（NOFORTRAN=0）。不能走纯 C/NOFORTRAN
路线：Makefile.system 中 NOFORTRAN=1 强制 C_LAPACK=1（381-383 行），C_LAPACK=1
配合 NO_LAPACK=1 再强制 NO_LAPACKE=1（1456-1459 行），产不出 LAPACKE。
package() 走 make install 复刻上游安装布局——lapacke.h 及伴生头
（lapack.h/lapacke_config.h/lapacke_mangling.h/lapacke_utils.h，其中 lapack.h
等是 install 期加工产物，不能直接 copy 源码树）+ libopenblas 内的 LAPACKE_*
符号；消费者链接 -lopenblas。

上游测试：
  - utest（纯 C 单元测试）默认折入 build()，静态链接本构建产物并就地执行。
  - Fortran 全套（test/ blat、ctest/ CBLAS 包装、lapack-test 的 EIG/LIN/INSTALL
    + lapack_testing.py -r 精简判定）经 RUN_UPSTREAM_TESTS=1 可选开启：
    flang 驱动链接可执行文件时由 symlink overlay 资源目录补齐目标级链接件
    （crt/builtins/libunwind/libc），不改上游源码逻辑（见 notes.md）。

依赖：
  - tool_requires flang-ohos/20.1.0（设备原生编好的 LLVM Flang 工具链，编 LAPACK 的 Fortran 部分）
  - C 编译/链接用设备 hnp clang（/data/service/hnp/bin/clang）
"""
import os
import glob
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy


class LiblapackeConan(ConanFile):
    name = "liblapacke"
    version = "0.3.30"
    description = ("LAPACKE — standard C interface to LAPACK, as shipped by OpenBLAS 0.3.30 "
                   "(lapacke.h headers + LAPACKE_* symbols inside libopenblas)")
    license = "BSD-3-Clause"
    homepage = "https://github.com/OpenMathLib/OpenBLAS"
    url = ""
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"blas_target": ["ANY"]}
    default_options = {"blas_target": "ARMV8"}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) != "OHOS" or str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("本 recipe 仅支持 os=OHOS arch=armv8（设备原生）")

    def build_requirements(self):
        self.tool_requires("flang-ohos/20.1.0")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _prepare_env(self):
        """构建与打包共用的环境准备，并返回 make 变量串。

        build() 与 package() 必须用**同一套** make 变量——Makefile.system 依据它们
        推导库名（libopenblas_<TARGET><线程后缀>-r<ver>）与安装布局，两阶段不一致
        会导致 install 找不到 build 出来的产物。故集中在此，不用实例属性传递。
        """
        flang_pkg = self.dependencies.build["flang-ohos"].package_folder
        fc = os.path.join(flang_pkg, "bin", "flang")
        rt = os.path.join(flang_pkg, "lib", "libFortranRuntime.a")
        dec = os.path.join(flang_pkg, "lib", "libFortranDecimal.a")
        # 设备 hnp 工具链（实测可用；不走 conf 以免 tools.build:compiler_executables 里未解析变量）
        cc = "/data/service/hnp/bin/clang"
        ar = "/data/service/hnp/bin/llvm-ar"
        ranlib = "/data/service/hnp/bin/llvm-ranlib"

        # LD_LIBRARY_PATH：① SDK llvm/lib 给 lld 正确 libxml2.so.16（HiShell 污染会搞坏 lld）
        #                  ② flang 包 lib 给 flang 运行期的 libLLVM/libMLIR/libclang-cpp
        sdk_llvm_lib = ""
        g = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib"))
        if g:
            sdk_llvm_lib = g[-1]
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
            p for p in [sdk_llvm_lib, os.path.join(flang_pkg, "lib")] if p)
        # 清 HiShell 污染的构建 env
        for k in ("CFLAGS", "CXXFLAGS", "CPPFLAGS", "LDFLAGS", "CMAKE_PREFIX_PATH", "PKG_CONFIG_PATH"):
            os.environ.pop(k, None)

        return ('TARGET=%s BINARY=64 HOSTCC="%s" CC="%s" FC="%s" '
                'F_COMPILER=FLANGNEW NOFORTRAN=0 AR="%s" RANLIB="%s" NO_SHARED=0 '
                'FEXTRALIB="%s %s -lm"'
                % (str(self.options.blas_target), cc, cc, fc, ar, ranlib, rt, dec))

    def build(self):
        apply_conandata_patches(self)
        # 目标 `shared` = libs + netlib(含 lapackelib=LAPACKE) + re_lapack，
        # 并在源码树根产出 SONAME=libopenblas.so.0 的共享实体。
        self.run("make -j%s %s shared" % (os.cpu_count() or 8, self._prepare_env()),
                 cwd=self.source_folder)
        self._run_upstream_lapacke_examples()
        # 上游 utest（纯 C）默认折入：真实构建并就地执行（见方法 docstring）。
        self._run_upstream_utest()
        # 可选：上游 Fortran 全套（blat / ctest / lapack-test 精简判定），
        # RUN_UPSTREAM_TESTS=1 时开启，实测时长见 notes.md「上游测试」。
        if os.environ.get("RUN_UPSTREAM_TESTS") == "1":
            self._run_upstream_fortran_test_suite()

    def _run_upstream_utest(self):
        """上游 utest（utest/ 纯 C 单元测试：openblas_utest + openblas_utest_ext），
        上游 `make tests` 入口的 C 侧全部内容。静态链接本构建的 libopenblas
        归档（utest/Makefile: `$(CC) ... ../$(LIBNAME) $(EXTRALIB) $(FEXTRALIB)`），
        归档内 Fortran 对象（ilaenv 等）的 flang 运行时符号由 FEXTRALIB 的绝对
        路径 libFortranRuntime.a/libFortranDecimal.a 闭合。
        CROSS=0 覆盖 Makefile.conf 探测记录的 CROSS=1，解除上游 `ifneq (CROSS,1)`
        对 run_test 就地执行的门（构建机即目标机，原生执行真实有效）。
        utest 链接由设备 clang 驱动，不需要 _fortran_link_overlay。
        """
        self.run("make -j1 -C utest all %s CROSS=0" % self._prepare_env(),
                 cwd=self.source_folder)
        self.output.info("upstream utest executed in build (openblas_utest + openblas_utest_ext, "
                         "RESULTS lines above in make log)")

    def _fortran_link_overlay(self):
        """为 flang 驱动链接**可执行文件**搭 symlink overlay 资源目录。

        flang-ohos 20.1.0 包自带 libFortranRuntime/Decimal/Common.a，但缺目标级
        链接件：其驱动（Target: aarch64-unknown-linux-ohos）链接行固定取
        <resource-dir>/lib/aarch64-linux-ohos/ 下的 crtbeginS/crtendS/builtins，
        并裸名搜索 Scrt1/crti/crtn 与 -lc/-lm/-l:libunwind.a。SDK（clang 15 布局）
        的这些实体按 flang 驱动期望的**文件名**以 symlink 集中到 overlay 资源目录，
        链接期以 `LDFLAGS="-resource-dir <overlay>"` 注入（flang 驱动会自动给
        链接行追加 -L<overlay>/lib/aarch64-linux-ohos）。不改动上游源码逻辑、
        不改动 flang 包与 SDK 实体；仅 Fortran 链接使用（clang 链接的 utest 路径
        不经过这里，避免污染 clang 自身 resource dir 语义）。
        """
        g = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native"))
        if not g:
            raise ConanException("未找到 OHOS SDK（/data/service/hnp/ohos-sdk.org/*/ohos/native）")
        native = g[-1]
        rt_g = sorted(glob.glob(os.path.join(
            native, "llvm", "lib", "clang", "*", "lib", "aarch64-linux-ohos")))
        if not rt_g:
            raise ConanException("未找到 SDK clang runtime 目录（llvm/lib/clang/*/lib/aarch64-linux-ohos）")
        clang_rt = rt_g[-1]
        syslib = os.path.join(native, "sysroot", "usr", "lib", "aarch64-linux-ohos")
        llvm_lib = os.path.join(native, "llvm", "lib", "aarch64-linux-ohos")
        root = os.path.join(self.source_folder, "ohos-flang-link-rd")
        triple = os.path.join(root, "lib", "aarch64-linux-ohos")
        os.makedirs(triple, exist_ok=True)
        sources = {
            # flang 驱动按 clang-20 布局裸名取 crt；SDK clang-15 同实体异名
            "crtbeginS.o": os.path.join(clang_rt, "clang_rt.crtbegin.o"),
            "crtendS.o": os.path.join(clang_rt, "clang_rt.crtend.o"),
            "libclang_rt.builtins.a": os.path.join(clang_rt, "libclang_rt.builtins.a"),
            "libunwind.a": os.path.join(llvm_lib, "libunwind.a"),
            "Scrt1.o": os.path.join(syslib, "Scrt1.o"),
            "crti.o": os.path.join(syslib, "crti.o"),
            "crtn.o": os.path.join(syslib, "crtn.o"),
            "libc.so": os.path.join(syslib, "libc.so"),
            "libpthread.so": os.path.join(syslib, "libc.so"),
            "libm.a": os.path.join(syslib, "libm.a"),
        }
        missing = [n for n, p in sorted(sources.items()) if not os.path.isfile(p)]
        if missing:
            raise ConanException("flang 测试链接 overlay 缺少目标级链接件: %s" % ", ".join(missing))
        for name, target in sources.items():
            dst = os.path.join(triple, name)
            if not os.path.islink(dst):
                os.symlink(target, dst)
        return root

    def _run_upstream_fortran_test_suite(self):
        """上游 Fortran 测试全套（可选，RUN_UPSTREAM_TESTS=1）：
        - test/：BLAS 官方测试 blat1/2/3 × s/d/c/z 四精度（上游 `make tests` 的
          Fortran 主体），构建 + 就地执行；
        - ctest/：CBLAS 包装层官方测试（x*blat 可执行 + error-exit 检查）；
        - lapack-test：上游 Makefile 入口 = EIG 4 + LIN 10 静态链接可执行 +
          INSTALL 7 个小程序 + `lapack_testing.py -r -b TESTING` 精简集判定
          （PATH 需含设备 python3，CI profile buildenv 已提供）。
        三者的可执行链接全部走 $(FC)/$(LOADER)=flang 驱动，overlay 经 LDFLAGS
        注入；CROSS=0 解除就地执行门。被测代码与上游入口语义一致（同一 make
        变量、同一目标），仅补齐平台缺失的目标级链接件。
        """
        rd = self._fortran_link_overlay()
        env = self._prepare_env()
        ldl = 'LDFLAGS="-resource-dir %s"' % rd
        self.run("make -j1 -C test all %s CROSS=0 %s" % (env, ldl), cwd=self.source_folder)
        self.run("make -j1 -C ctest all %s CROSS=0 %s" % (env, ldl), cwd=self.source_folder)
        self.run("make -j1 lapack-test %s CROSS=0 %s" % (env, ldl), cwd=self.source_folder)
        self.output.info("upstream Fortran test suite executed in build "
                         "(test/ blat, ctest/, lapack-test EIG+LIN+INSTALL+lapack_testing.py -r)")

    def _run_upstream_lapacke_examples(self):
        """上游 LAPACKE 唯一的可执行 C 测试资产：lapack-netlib/LAPACKE/example 的
        4 个演示程序（DGESV/DGELS × colmajor/rowmajor）。上游入口
        `make lapacke_example` 会以 $(FC) 链接并就地执行它们；此处复用与 Fortran
        测试一致的 flang 链接能力已不必要——历史实现以设备 CC 链接（仅链接器一处
        偏差，MANIFEST.yml 声明），保持不变以保证默认路径轻量稳定。
        """
        src = os.path.join(self.source_folder, "lapack-netlib", "LAPACKE", "example")
        inc = os.path.join(self.source_folder, "lapack-netlib", "LAPACKE", "include")
        cc = "/data/service/hnp/bin/clang"
        sign = "/data/service/hnp/bin/binary-sign-tool"

        # 演示运行目录：放 SONAME 实体的自签副本（XPM 要求加载的 .so 自签，同
        # openblas 配方 _sign_so 先例）。链接行以该副本的绝对路径作显式输入
        # （禁隐式搜索路径），运行期加载器按 DT_NEEDED libopenblas.so.0 在此目录命中。
        demo_dir = os.path.join(self.source_folder, "lapacke_demos")
        os.makedirs(demo_dir, exist_ok=True)
        soname_link = os.path.join(self.source_folder, "libopenblas.so.0")
        so_copy = os.path.join(demo_dir, "libopenblas.so.0")
        if not os.path.isfile(so_copy):
            # copy2 默认跟随符号链接，复制的是实体内容
            shutil.copy2(soname_link, so_copy)
        if os.path.isfile(sign):
            self.run('%s sign -inFile "%s" -outFile "%s" -selfSign 1' % (sign, so_copy, so_copy))

        demos = ["example_DGESV_colmajor", "example_DGESV_rowmajor",
                 "example_DGELS_colmajor", "example_DGELS_rowmajor"]
        for d in demos:
            exe = os.path.join(demo_dir, d)
            self.run('%s %s.c lapacke_example_aux.c -I"%s" -I"%s" -o "%s" "%s" -lm'
                     % (cc, os.path.join(src, d), src, inc, exe, so_copy),
                     cwd=src)
            self.run('env LD_LIBRARY_PATH="%s" "%s"' % (demo_dir, exe), cwd=demo_dir)
        self.output.info(
            "upstream LAPACKE examples executed: %d/%d (upstream links with FC; "
            "CC used for this lightweight default path — deviation documented)"
            % (len(demos), len(demos)))

    def package(self):
        # 【必须走 make install，不能直接 copy 源码树里的头文件】
        # openblas_config.h / f77blas.h / lapack.h（install 期生成/加工）与
        # cblas.h（install 期 sed 's/common/openblas_config/g'）同 openblas 0.3.34
        # 的教训；LAPACKE 头（lapacke.h 等）也由 Makefile.install 统一安装。
        # 顺带生成 lib/pkgconfig/openblas.pc 与 lib/cmake/openblas/。
        self.run('make %s PREFIX="%s" install' % (self._prepare_env(), self.package_folder),
                 cwd=self.source_folder)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        self._sign_so()

    def _sign_so(self):
        # 设备原生：XPM 要求加载的 .so 自签（binary-sign-tool 在设备 hnp bin）。
        # 符号链接跳过，只签实体；实体被签后链接链（.so/.so.0 → 实体）整体有效。
        sign = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(sign):
            self.output.warning("binary-sign-tool 不存在，跳过签名（消费端需自签）")
            return
        for so in glob.glob(os.path.join(self.package_folder, "lib", "*.so*")):
            if os.path.islink(so):
                continue
            self.run('%s sign -inFile "%s" -outFile "%s" -selfSign 1' % (sign, so, so))

    def package_info(self):
        # 上游交付形态：LAPACKE 符号在 libopenblas 内（消费者链接 -lopenblas）。
        # lapacke.h/lapacke_config.h/lapacke_mangling.h/lapacke_utils.h/lapack.h
        # 均在 include/ 下，#include <lapacke.h> 即可用。
        self.cpp_info.libs = ["openblas"]
        self.cpp_info.system_libs = ["m", "pthread"]
