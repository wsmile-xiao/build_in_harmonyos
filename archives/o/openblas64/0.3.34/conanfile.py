#!/usr/bin/env python3
"""Conan recipe — openblas64 0.3.34 (Makefile, HarmonyOS PC / os=OHOS arch=armv8)

ILP64 (64-bit integer) variant of OpenBLAS: INTERFACE64=1 + LIBNAMESUFFIX=64,
NOFORTRAN=1 (f2c converted LAPACK, no Fortran toolchain needed).

Library: libopenblas64 (SONAME libopenblas64.so.0), headers define
OPENBLAS_USE64BITINT, blasint/lapack_int are 64-bit. Package name openblas64
keeps LP64 (openblas) and ILP64 side-by-side installable via Conan.

Device-native recipe: C/asm with device hnp clang on HarmonyOS PC真机.
Follows archives/o/openblas/0.3.33 (NOFORTRAN=1 + upstream C tests in build).
"""

import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy as conan_copy
from conan.tools.files import export_conandata_patches


class Openblas64Conan(ConanFile):
    name = "openblas64"
    version = "0.3.34"
    description = "Optimized BLAS library based on GotoBLAS2 (ILP64 64-bit integer interface)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/OpenMathLib/OpenBLAS"
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
        from conan.tools.files import get
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _jobs(self):
        # 真机文件系统不支持 GNU make FIFO jobserver（HMBS [make_jobserver_fifo]），
        # 且 hmbs 注入 tools.build:jobs=1；此处显式 -j1，避免 mkfifo Operation not permitted。
        try:
            j = self.conf.get("tools.build:jobs", default=1, check_type=int)
        except Exception:
            j = 1
        if not j or int(j) < 1:
            return 1
        # 上游 Makefile 高并行在真机易出现 jobserver/资源问题，固定单作业最稳。
        return 1

    def _probe_pthread_setaffinity(self, cc: str) -> bool:
        """通用能力探测：pthread_setaffinity_np 是否可用（编译+链接）。

        某些 musl 工具链（如 OHOS）的 libc.so 不导出 pthread_setaffinity_np
        （仅 libc.a 有），导致链接失败。这里用真实编译+链接探测，把结果
        映射为通用 capability 宏 HAVE_PTHREAD_SETAFFINITY_NP——而非平台宏。
        """
        import subprocess
        import tempfile
        probe_src = (
            "#define _GNU_SOURCE\n"
            "#include <pthread.h>\n"
            "int main(void){ pthread_t t = pthread_self(); cpu_set_t cs; "
            "CPU_ZERO(&cs); return pthread_setaffinity_np(t, sizeof(cs), &cs); }\n"
        )
        # HMBS [readonly_tmp]：/tmp 只读，必须用 HMBS 注入的 TMPDIR/TMP/TEMP。
        tmpdir = os.environ.get("TMPDIR") or os.environ.get("TMP") or os.environ.get("TEMP") or None
        if tmpdir and not os.path.isdir(tmpdir):
            tmpdir = None
        with tempfile.NamedTemporaryFile("w", suffix=".c", delete=False, dir=tmpdir) as f:
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
        推导库名与安装布局，两阶段不一致会导致 install 找不到 build 产物。
        ILP64 要素：INTERFACE64=1（64 位整型 ABI）+ LIBNAMESUFFIX=64
        （库名 libopenblas64，与 LP64 的 libopenblas 并存不冲突；符号保持上游
        默认不加 SYMBOLSUFFIX，单包内自洽）。
        """
        cc = "/data/service/hnp/bin/clang"
        ar = "/data/service/hnp/bin/llvm-ar"
        ranlib = "/data/service/hnp/bin/llvm-ranlib"

        sdk_llvm_lib = ""
        g = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib"))
        if g:
            sdk_llvm_lib = g[-1]
        os.environ["LD_LIBRARY_PATH"] = sdk_llvm_lib
        for k in ("CFLAGS", "CXXFLAGS", "CPPFLAGS", "LDFLAGS",
                  "CMAKE_PREFIX_PATH", "PKG_CONFIG_PATH"):
            os.environ.pop(k, None)
        os.environ["PATH"] = "/bin:/usr/bin:" + os.environ.get("PATH", "")

        extra_opt = ""
        if self._probe_pthread_setaffinity(cc):
            extra_opt = 'CCOMMON_OPT="-DHAVE_PTHREAD_SETAFFINITY_NP" '

        return ('TARGET=%s BINARY=64 INTERFACE64=1 LIBNAMESUFFIX=64 '
                'HOSTCC="%s" CC="%s" '
                '%sAR="%s" RANLIB="%s" NOFORTRAN=1 NO_SHARED=0 NO_AFFINITY=1'
                % (str(self.options.blas_target), cc, cc, extra_opt, ar, ranlib))

    def build(self):
        apply_conandata_patches(self)
        self.run("make -j%d %s shared" % (self._jobs(), self._prepare_env()),
                 cwd=self.source_folder)
        self._run_upstream_tests()

    def _capture(self, cmd, cwd):
        """真机执行命令并捕获合并输出（用于解析上游测试计数）。

        用 subprocess 而非 self.run 以便拿到 stdout 做真实计数；
        输出同时回显到 conan 日志，保证预检日志可审计。
        """
        import subprocess
        self.output.info("RUN(UPSTREAM): %s (cwd=%s)" % (cmd, cwd))
        proc = subprocess.run(cmd, shell=True, cwd=cwd,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True, errors="replace",
                              env=dict(os.environ))
        out = proc.stdout or ""
        for line in out.splitlines()[-40:]:
            self.output.info("[upstream-out] " + line)
        return proc.returncode, out

    def _run_upstream_tests(self):
        """在构建流程内执行上游测试并记录结果（发布配方 NOFORTRAN=1 保持不变）。

        utest/ + ctest/ 为纯 C 测试（无 Fortran 依赖），在 ILP64 下同样可构建
        执行（传入同一套 INTERFACE64/LIBNAMESUFFIX 变量）。
        Fortran 测试（test/、lapack-netlib/）需 gfortran/flang；设备无 Fortran
        编译器时如实记录跳过（不伪装通过）。
        """
        import json
        import re
        import shutil
        env = self._prepare_env()
        ld_lib = self.source_folder
        old_ld = os.environ.get("LD_LIBRARY_PATH", "")
        os.environ["LD_LIBRARY_PATH"] = ld_lib + (":" + old_ld if old_ld else "")
        # 上游测试单线程跑，避免真机线程/资源抖动掩盖数值结果；
        # ctest/Makefile 内写死 OPENBLAS_NUM_THREADS=2，此处仅约束 utest 与后续
        # 手动重跑，ctest 保持上游默认 2（与 LP64 同源行为一致）。
        os.environ["OPENBLAS_NUM_THREADS"] = "1"
        os.environ["GOTO_NUM_THREADS"] = "1"
        os.environ["OMP_NUM_THREADS"] = "1"

        # make -C utest 默认 target all -> run_test：构建并执行
        # openblas_utest + openblas_utest_ext（ctest.h 框架，打印 TEST ... [OK] 与 RESULTS）。
        rc, utest_build_out = self._capture("make -j%d -C utest %s" % (self._jobs(), env),
                                            self.source_folder)
        if rc != 0:
            raise RuntimeError("make -C utest 失败 (exit %d)" % rc)

        # ctest/Makefile 的 all 同样构建并执行 12 个 x*cblat（OPENBLAS_NUM_THREADS=2）。
        rc, ctest_out = self._capture("make -j%d -C ctest all %s" % (self._jobs(), env),
                                      self.source_folder)
        if rc != 0:
            raise RuntimeError("make -C ctest all 失败 (exit %d)" % rc)

        combined = utest_build_out + "\n" + ctest_out
        # 解析 utest ctest.h 输出：RESULTS: N tests (M ok, K failed...) 或 TEST ... [OK]/[FAILED]。
        discovered = 0
        passed = 0
        failed = 0
        for m in re.finditer(r"RESULTS:\s*(\d+)\s*tests?\s*\((\d+)\s*ok", combined):
            n = int(m.group(1))
            ok = int(m.group(2))
            discovered += n
            passed += ok
        ok_lines = len(re.findall(r"\[OK\]", combined))
        fail_lines = len(re.findall(r"\[(?:FAILED|FAIL)\]", combined))
        if discovered == 0 and (ok_lines or fail_lines):
            discovered = ok_lines + fail_lines
            passed = ok_lines
            failed = fail_lines
        else:
            failed += fail_lines
        # ctest/CBLAS：每个 x*cblat 二进制退出 0 视为 1 个可执行通过（上游无统一计数行时保底）。
        # 若 utest 已给出计数，仅把 ctest 可执行数累加为独立维度，避免冒充用例数。
        # 回退口径与 PR 声明一致：C 可执行 = utest 2（openblas_utest + openblas_utest_ext）+ ctest 12。
        utest_bins = ["openblas_utest", "openblas_utest_ext"]
        utest_dir = os.path.join(self.source_folder, "utest")
        utest_built = sum(1 for b in utest_bins
                          if os.path.isfile(os.path.join(utest_dir, b)))
        ctest_bins = ["xscblat1", "xdcblat1", "xccblat1", "xzcblat1",
                      "xscblat2", "xdcblat2", "xccblat2", "xzcblat2",
                      "xscblat3", "xdcblat3", "xccblat3", "xzcblat3"]
        ctest_dir = os.path.join(self.source_folder, "ctest")
        ctest_built = sum(1 for b in ctest_bins
                          if os.path.isfile(os.path.join(ctest_dir, b)))
        c_built = utest_built + ctest_built
        if c_built and discovered == 0:
            # 极端回退：框架输出未被识别时，按可执行数计（不伪装用例级通过）。
            discovered = c_built
            passed = c_built if failed == 0 else 0
        elif ctest_built:
            # utest 已有精确计数时，ctest 可执行数仅用于日志说明，不混入用例数。
            self.output.info("[upstream] ctest 可执行 %d/12、utest 可执行 %d/2 已按上游默认执行"
                             % (ctest_built, utest_built))
        executed = discovered
        skipped = 0
        status = "passed" if (discovered > 0 and failed == 0) else "failed"
        marker = {"status": status, "framework": "openblas-utest+ctest",
                  "command": "make -C utest && make -C ctest all",
                  "discovered": discovered, "executed": executed,
                  "passed": passed, "failed": failed, "skipped": skipped}
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker))
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker))
        if status != "passed":
            raise RuntimeError("上游 C 测试未通过: %s" % json.dumps(marker))

        fc = shutil.which("gfortran") or shutil.which("flang") \
            or shutil.which("flang-new")
        if fc:
            self.output.info("[upstream] 检测到 Fortran 编译器 %s，执行 test/ 与 lapack-netlib/ 测试" % fc)
            self.run("make -C test all %s" % env, cwd=self.source_folder)
            self.run("make -j1 -C lapack-netlib blas_testing", cwd=self.source_folder)
        else:
            self.output.warning(
                "[upstream] 无 Fortran 编译器(gfortran/flang/flang-new 均不可用)，"
                "跳过 test/ 与 lapack-netlib/ Fortran 测试；"
                "恢复条件：安装 Fortran 编译器后执行 make lapack-test/blas-test")
        os.environ["LD_LIBRARY_PATH"] = old_ld

    def package(self):
        # 【必须走 make install，不能直接 copy 源码树里的头文件】
        # openblas_config.h / lapack.h 系 install 期生成；cblas.h 需 sed 加工
        # （源码树版本 #include "common.h"，install 后改为 openblas_config.h）。
        # make install 顺带生成 lib/pkgconfig/openblas64.pc 与 lib/cmake/openblas/。
        self.run('make %s PREFIX="%s" install' % (self._prepare_env(), self.package_folder),
                 cwd=self.source_folder)
        for lic in ("LICENSE", "GotoBLAS_00License.txt",
                    "lapack-netlib/LICENSE"):
            conan_copy(self, lic, src=self.source_folder,
                       dst=os.path.join(self.package_folder, "licenses"))
        self._sign_so()

    def _sign_so(self):
        sign = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(sign):
            self.output.warning("binary-sign-tool 不存在，跳过签名（消费端需自签）")
            return
        for so in glob.glob(os.path.join(self.package_folder, "lib", "*.so*")):
            if os.path.islink(so):
                continue
            self.run('%s sign -inFile "%s" -outFile "%s" -selfSign 1' % (sign, so, so))

    def package_info(self):
        self.cpp_info.libs = ["openblas64"]
        self.cpp_info.set_property("pkg_config_name", "openblas64")
        self.cpp_info.system_libs = ["m", "pthread"]
        # ILP64 消费者必须以 64 位整型看头文件：LAPACK_ILP64（上游 lapacke.h/
        # lapack.h 侧宏）由消费端定义；OPENBLAS_USE64BITINT 由包内
        # openblas_config.h 提供，此处同时声明以便 CMake/pkg-config 消费端
        # 自动获得一致的 64 位视图（test_package 因手动拼 cc 命令行，另显式
        # 传 -DLAPACK_ILP64，见 test_package/conanfile.py）。
        self.cpp_info.defines = ["LAPACK_ILP64", "OPENBLAS_USE64BITINT"]
