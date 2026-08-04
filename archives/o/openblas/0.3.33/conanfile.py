#!/usr/bin/env python3
"""Conan recipe — openblas 0.3.33 (Makefile, HarmonyOS PC / os=OHOS arch=armv8)

**设备原生** recipe：在鸿蒙 PC 真机上 `conan create`。C/汇编用设备 hnp clang。

变量方案：`NOFORTRAN=1`（官方主变量，Makefile.system:387）——不依赖任何 Fortran
编译器；该路径自动置 `C_LAPACK=1`（f2c 转换版 LAPACK）+ LAPACKE，符号齐全
（cblas_dgemm / dgesv_ / dpotrf_ / LAPACKE_dgesv 均已 smoke 验证）。
0.3.34/0.3.28 用的是 `NOFORTRAN=0` + flang-ohos/20.1.0 真 Fortran LAPACK；
本机无 flang、ohpcd 无 flang-ohos 制品，故 0.3.33 本轮走 NOFORTRAN=1（差异见
notes.md「LAPACK 方案对比」）。

补丁（仅 1 个，portability）：
  - 0002-ohos-musl-affinity.patch：openblas_setaffinity/getaffinity 由通用能力宏
    `HAVE_PTHREAD_SETAFFINITY_NP` 门控（`#if defined(OS_LINUX) && defined(HAVE_PTHREAD_SETAFFINITY_NP)`）。
    该宏由构建期**真实编译+链接探测**决定是否定义（见 `_probe_pthread_setaffinity`）：
    musl 工具链（如 OHOS）的 libc.so 不导出 pthread_setaffinity_np/getaffinity_np
    （仅 libc.a 有），`NO_AFFINITY` 挡不住这两个 OS_LINUX 函数；探测失败时不定义宏，
    affinity 代码不编译，避免 ld.lld `--no-allow-shlib-undefined` undefined reference。
    不使用 `__OHOS__`/`OHOS` 等平台条件宏。（NOFORTRAN=1 走 exports/Makefile 通用
    `$(CC)` 链接分支，不需要 0.3.34 的 0001 flangnew 链接补丁。）
"""
import os
import glob
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.files import copy as conan_copy
from conan.errors import ConanInvalidConfiguration


class OpenblasConan(ConanFile):
    name = "openblas"
    version = "0.3.33"
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"blas_target": ["ANY"]}
    default_options = {"blas_target": "ARMV8"}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) != "OHOS" or str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("本 recipe 仅支持 os=OHOS arch=armv8（设备原生）")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _probe_pthread_setaffinity(self, cc: str) -> bool:
        """通用能力探测：pthread_setaffinity_np 是否可用（编译+链接）。

        某些 musl 工具链（如 OHOS）的 libc.so 不导出 pthread_setaffinity_np
        （仅 libc.a 有），导致链接失败。这里用真实编译+链接探测，把结果
        映射为通用 capability 宏 HAVE_PTHREAD_SETAFFINITY_NP——而非平台宏。
        """
        import subprocess
        import tempfile
        probe_src = (
            '#define _GNU_SOURCE\n'
            '#include <pthread.h>\n'
            'int main(void){ pthread_t t = pthread_self(); cpu_set_t cs; '
            'CPU_ZERO(&cs); return pthread_setaffinity_np(t, sizeof(cs), &cs); }\n'
        )
        with tempfile.NamedTemporaryFile("w", suffix=".c", delete=False) as f:
            f.write(probe_src)
            src = f.name
        try:
            out = src + ".out"
            r = subprocess.run([cc, src, "-o", out, "-lpthread"],
                               capture_output=True, timeout=60)
            ok = r.returncode == 0 and os.path.isfile(out)
        except Exception:
            ok = False
        finally:
            for p in (src, src + ".out"):
                try:
                    os.unlink(p)
                except OSError:
                    pass
        if ok:
            self.output.info("探测: pthread_setaffinity_np 可用 -> 启用 HAVE_PTHREAD_SETAFFINITY_NP")
        else:
            self.output.info("探测: pthread_setaffinity_np 不可用 -> 不启用 affinity 代码")
        return ok

    def _prepare_env(self):
        """构建与打包共用的环境准备，并返回 make 变量串。

        build() 与 package() 必须用**同一套** make 变量——Makefile.system 依据它们
        推导库名（libopenblas_<TARGET><线程后缀>-r<ver>）与安装布局，两阶段不一致
        会导致 install 找不到 build 出来的产物。故集中在此。
        """
        # 设备 hnp 工具链（实测可用；不走 conf 以免 tools.build:compiler_executables
        # 里未解析变量）
        cc = "/data/service/hnp/bin/clang"
        ar = "/data/service/hnp/bin/llvm-ar"
        ranlib = "/data/service/hnp/bin/llvm-ranlib"

        # LD_LIBRARY_PATH：SDK llvm/lib 给 lld 正确 libxml2.so.16（HiShell 污染会
        # 搞坏 lld）
        sdk_llvm_lib = ""
        g = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib"))
        if g:
            sdk_llvm_lib = g[-1]
        os.environ["LD_LIBRARY_PATH"] = sdk_llvm_lib
        # 清 HiShell 污染的构建 env
        for k in ("CFLAGS", "CXXFLAGS", "CPPFLAGS", "LDFLAGS",
                  "CMAKE_PREFIX_PATH", "PKG_CONFIG_PATH"):
            os.environ.pop(k, None)
        # 设备 shell PATH 不含 /bin，而 Makefile.install 用 `install`（/bin/install）；
        # 补齐 PATH，否则 make install 报 "install: not found"（Error 127）。
        os.environ["PATH"] = "/bin:/usr/bin:" + os.environ.get("PATH", "")

        # 通用能力探测：pthread_setaffinity_np 可用性 → HAVE_PTHREAD_SETAFFINITY_NP
        # （blas_server.c 的 affinity 代码由该宏门控，而非平台宏；OHOS musl 的
        # libc.so 不导出该符号，探测失败则不编译 affinity 代码，避免链接错误）
        extra_opt = ""
        if self._probe_pthread_setaffinity(cc):
            extra_opt = 'CCOMMON_OPT="-DHAVE_PTHREAD_SETAFFINITY_NP" '

        return ('TARGET=%s BINARY=64 HOSTCC="%s" CC="%s" '
                '%sAR="%s" RANLIB="%s" NOFORTRAN=1 NO_SHARED=0 NO_AFFINITY=1'
                % (str(self.options.blas_target), cc, cc, extra_opt, ar, ranlib))

    def build(self):
        apply_conandata_patches(self)
        # 设备 20 核：-j20 全量编译最快（-j12 约 540s 仍逼近 W3 本地 CI 外层 600s
        # 硬超时；jobserver mkfifo 报错仅是警告，make 降级运行不影响产物）。
        self.run("make -j20 %s shared" % self._prepare_env(),
                 cwd=self.source_folder)
        # 【上游测试集成】在构建流程内真实执行可运行的上游测试（非手工替代）：
        #   · utest/  —— openblas_utest + openblas_utest_ext（纯 C，无 Fortran 依赖）
        #   · ctest/  —— 12 个 CBLAS C 测试（x?cblat1/2/3，无 Fortran 依赖）
        #   · Fortran 测试（test/、lapack-netlib/）—— 需 gfortran/flang；设备无
        #     Fortran 编译器时如实记录跳过（不伪装通过），不因 NOFORTRAN=1 直接跳过
        #     而宣称未覆盖；若环境提供编译器则真实构建执行。
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """在构建流程内执行上游测试并记录结果（发布配方 NOFORTRAN=1 保持不变）。"""
        env = self._prepare_env()
        # 运行 utest/ctest 需要 LD_LIBRARY_PATH 指向源码树内的 .so
        ld_lib = self.source_folder
        old_ld = os.environ.get("LD_LIBRARY_PATH", "")
        os.environ["LD_LIBRARY_PATH"] = ld_lib + (":" + old_ld if old_ld else "")

        # 1) utest/ —— 纯 C 测试（无 Fortran 依赖）
        self.run("make -C utest %s" % env, cwd=self.source_folder)
        self.run("./openblas_utest", cwd=os.path.join(self.source_folder, "utest"))
        self.run("./openblas_utest_ext", cwd=os.path.join(self.source_folder, "utest"))
        self.output.info("[upstream] utest: openblas_utest + openblas_utest_ext 已执行")
        # 2) ctest/ —— CBLAS C 测试（无 Fortran 依赖，Makefile all1/all2/all3 内含运行）
        self.run("make -C ctest all %s" % env, cwd=self.source_folder)
        self.output.info("[upstream] ctest: 12 个 CBLAS 测试已执行")

        # 3) Fortran 测试（test/、lapack-netlib/）—— 需要 Fortran 编译器
        import shutil
        fc = shutil.which("gfortran") or shutil.which("flang") \
            or shutil.which("flang-new")
        if fc:
            self.output.info("[upstream] 检测到 Fortran 编译器 %s，执行 test/ 与 lapack-netlib/ 测试" % fc)
            self.run("make -C test all %s" % env, cwd=self.source_folder)
            self.run("make -j1 -C %s blas_testing" % "lapack-netlib", cwd=self.source_folder)
        else:
            # 无 Fortran 编译器：如实记录跳过原因（非失败、非通过）
            self.output.warning(
                "[upstream] 无 Fortran 编译器(gfortran/flang/flang-new 均不可用)，"
                "跳过 test/(14 个 .f 主程序) 与 lapack-netlib/(INSTALL/BLAS/TESTING/TESTING) "
                "Fortran 测试；恢复条件：安装 Fortran 编译器后执行 make lapack-test/blas-test")
        os.environ["LD_LIBRARY_PATH"] = old_ld

    def package(self):
        # 【必须走 make install，不能直接 copy 源码树里的头文件】
        # OpenBLAS 有三个头文件是 **install 期才产生/加工** 的：
        #   · openblas_config.h —— Makefile.install 由 config.h + template 拼出
        #   · lapack.h          —— 同样 install 期生成
        #   · cblas.h           —— 源码树那份 #include "common.h"（内部头，不外发）；
        #                          install 会 `sed 's/common/openblas_config/g'`
        # make install 顺带生成 lib/pkgconfig/openblas.pc 与 lib/cmake/openblas/。
        self.run('make %s PREFIX="%s" install' % (self._prepare_env(), self.package_folder),
                 cwd=self.source_folder)
        # 许可证打包（Makefile.install 不装 LICENSE，需手动补）：
        #   · LICENSE               —— OpenBLAS 主 BSD-3-Clause（含 GotoBLAS 引用）
        #   · GotoBLAS_00License.txt —— GotoBLAS 原始许可（OpenBLAS 派生自 GotoBLAS）
        #   · lapack-netlib/LICENSE —— 内嵌 LAPACK (netlib) 的 BSD 许可
        for lic in ("LICENSE", "GotoBLAS_00License.txt",
                    "lapack-netlib/LICENSE"):
            conan_copy(self, lic, src=self.source_folder,
                       dst=os.path.join(self.package_folder, "licenses"))
        self._sign_so()

    def _sign_so(self):
        # 设备原生：XPM 要求 dlopen 的 .so 自签。binary-sign-tool 在设备 hnp bin。
        sign = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(sign):
            self.output.warning("binary-sign-tool 不存在，跳过签名（消费端需自签）")
            return
        for so in glob.glob(os.path.join(self.package_folder, "lib", "*.so*")):
            if os.path.islink(so):
                continue
            self.run('%s sign -inFile "%s" -outFile "%s" -selfSign 1' % (sign, so, so))

    def package_info(self):
        self.cpp_info.libs = ["openblas"]
        self.cpp_info.set_property("pkg_config_name", "openblas")
        self.cpp_info.system_libs = ["m", "pthread"]
