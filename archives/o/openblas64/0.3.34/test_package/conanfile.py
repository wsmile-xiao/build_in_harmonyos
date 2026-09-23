import json
import os
import re
import subprocess
from conan import ConanFile
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # 直接编译+链接（非 dlopen）：既 #include <cblas.h>/<lapacke.h>/<lapack.h>
        # （依赖包的 include/），又链接 libopenblas64（依赖包的 lib/）——CI 的
        # L1e 破坏性反向验证会把这两个目录整个移走再跑一次，两处都真实依赖
        # 才不会被判成假测试。
        # 运行时 loader 靠 RPATH/LD_LIBRARY_PATH 找 libopenblas64.so.0：
        # 链接期同时埋 -rpath（运行时）与 -rpath-link（链接期），test() 再显式
        # 导出 LD_LIBRARY_PATH，双保险避免 musl/OHOS 报
        # "Error loading shared library libopenblas64.so.0"。
        dep = self.dependencies["openblas64"].cpp_info
        inc = " ".join("-I" + p for p in dep.includedirs)
        raw_ld = dep.libdirs[0]
        if os.path.isabs(raw_ld):
            libdir = raw_ld
        else:
            libdir = os.path.join(
                self.dependencies["openblas64"].package_folder, raw_ld)
        cc = self.conf.get("tools.build:compiler_executables", default={},
                           check_type=dict).get("c", "/data/service/hnp/bin/clang")
        # ILP64 消费者契约：lapack_int 宽度由 LAPACK_ILP64（上游 lapacke.h/lapack.h
        # 侧宏）决定，消费者侧必须定义；blasint 由包内 openblas_config.h 的
        # OPENBLAS_USE64BITINT（库侧 INTERFACE64=1 产生）决定。test.c 已在
        # include 前 #define LAPACK_ILP64 并显式校验 openblas_config.h，此处
        # 编译行再加 -DLAPACK_ILP64 双保险（即使头文件包含顺序变化仍为 64 位）。
        # 同时审计库侧：openblas_config.h 必须含 OPENBLAS_USE64BITINT，否则
        # 说明库未以 INTERFACE64=1 构建（配方 bug），直接报错而不掩盖。
        import glob as _glob
        _cfg_hits = _glob.glob(os.path.join(
            self.dependencies["openblas64"].package_folder, "**", "openblas_config.h"),
            recursive=True)
        _has_use64 = False
        for _h in _cfg_hits:
            try:
                with open(_h, encoding="utf-8", errors="replace") as _f:
                    if "OPENBLAS_USE64BITINT" in _f.read():
                        _has_use64 = True
                        break
            except OSError:
                continue
        self.output.info("[test_package] openblas_config.h hits=%s USE64BITINT=%s"
                         % (_cfg_hits, _has_use64))
        if not _has_use64:
            raise RuntimeError("库侧未开 ILP64：openblas_config.h 缺少 OPENBLAS_USE64BITINT")
        self.run("{cc} test.c -o test_probe -DLAPACK_ILP64 {inc} -L{ld} -Wl,-rpath,{ld} -Wl,-rpath-link,{ld} "
                 "-lopenblas64 -lm".format(cc=cc, inc=inc, ld=libdir))

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        # 真机线程/资源抖动会掩盖数值结果；test_probe 单线程跑（库仍为多线程构建）。
        # 运行期必须让 loader 找到本次刚装好的 libopenblas64.so.0：conanrun
        # env 在 self.run(env="conanrun") 时才自动注入，用 subprocess 捕获输出时
        # 需手动把依赖 libdir 拼进 LD_LIBRARY_PATH（否则报 Error loading shared
        # library libopenblas64.so.0 + 全符号 Error relocating）。
        dep_pkg = self.dependencies["openblas64"]
        raw_ld = dep_pkg.cpp_info.libdirs[0]
        if os.path.isabs(raw_ld):
            dep_libdir = raw_ld
        else:
            dep_libdir = os.path.join(dep_pkg.package_folder, raw_ld)
        for k, v in (("OPENBLAS_NUM_THREADS", "1"), ("GOTO_NUM_THREADS", "1"),
                     ("OMP_NUM_THREADS", "1")):
            os.environ[k] = v
        run_env = dict(os.environ)
        old_ld = run_env.get("LD_LIBRARY_PATH", "")
        run_env["LD_LIBRARY_PATH"] = dep_libdir + (":" + old_ld if old_ld else "")
        cmd = "./test_probe"
        self.output.info("RUN(test_package): %s (single-thread) LD_LIBRARY_PATH=%s" % (cmd, run_env["LD_LIBRARY_PATH"]))
        proc = subprocess.run(cmd, shell=True, cwd=self.build_folder,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True, errors="replace",
                              env=run_env)
        out = proc.stdout or ""
        # 回显真实输出，保证预检日志可审计（含 7 项断言明细与结论行）。
        for line in out.splitlines():
            self.output.info("[test_probe] " + line)
        # 解析真实断言数：test.c 打印 "  [ok]/[FAIL]" 行与 "结论 PASS/FAIL：N 项断言，M 项失败"。
        ok = len(re.findall(r"\[(?:ok|OK|PASS)\]", out))
        fail_tag = len(re.findall(r"\[(?:FAIL|FAILED)\]", out))
        m = re.search(r"(\d+)\s*项断言\D*?(\d+)\s*项失败", out)
        if m:
            discovered = int(m.group(1))
            failed = int(m.group(2))
            passed_count = discovered - failed
        else:
            discovered = ok + fail_tag
            failed = fail_tag
            passed_count = ok
        executed = proc.returncode == 0
        passed = (proc.returncode == 0 and failed == 0 and discovered > 0)
        marker = {"executed": True, "passed": passed, "command": cmd,
                  "discovered": discovered, "passedCount": passed_count}
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker))
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker))
        if proc.returncode != 0:
            raise RuntimeError("test_probe 失败 (exit %d)" % proc.returncode)
        if discovered <= 0 or not passed:
            raise RuntimeError("test_probe 断言未通过: %s" % json.dumps(marker))
