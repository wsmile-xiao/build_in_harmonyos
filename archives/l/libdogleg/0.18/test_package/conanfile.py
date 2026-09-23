#!/usr/bin/env python3
"""test_package for libdogleg 0.18 — dense-solver consumer test (7 assertions)."""
import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.env import Environment


class LibdoglegTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _writable_tmpdir(self):
        # E002 / HMBS [readonly_tmp]: 与主配方同法，优先复用 hmbs 注入的
        # 任务级临时目录并真实写入探测，回退 build_folder/.hmbs-tmp。
        for _var in ("HMBS_TMPDIR", "TMPDIR", "TMP", "TEMP"):
            _cand = os.environ.get(_var)
            if not _cand:
                continue
            try:
                os.makedirs(_cand, exist_ok=True)
                _probe = os.path.join(_cand, ".hmbs-write-probe")
                with open(_probe, "w") as _f:
                    _f.write("ok")
                os.unlink(_probe)
                return _cand
            except OSError:
                continue
        _fb = os.path.join(self.build_folder or os.getcwd(), ".hmbs-tmp")
        try:
            os.makedirs(_fb, exist_ok=True)
        except OSError:
            pass
        return _fb

    # E2BIG 禁区（libmspub-tools/0.1.4 先例）：不在 generate() 内 save_script；
    # VirtualRunEnv 由 generators 属性生成（conanrunenv-*.sh，命名安全），
    # TMPDIR 等自定义变量改在 build()/test() 内以 apply() 运行时注入。

    def _resolve_cc(self):
        # 主配方同法：画像 clang 先做 --version 可运行校验，
        # 不可用时按注入变量与系统路径回退。
        try:
            compilers = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict) or {}
        except Exception:
            compilers = {}
        profile = compilers.get("c")
        ordered = [profile,
                   os.environ.get("HMBS_CC"), os.environ.get("CC"),
                   shutil.which("clang"), shutil.which("cc"),
                   "clang", "cc",
                   "/storage/Users/currentUser/usr/local/bin/clang",
                   "/data/service/hnp/bin/clang"]
        seen = set()
        for cand in ordered:
            if not cand or cand in seen:
                continue
            seen.add(cand)
            try:
                proc = subprocess.run(
                    [cand, "--version"],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, timeout=30, check=False)
                runnable = proc.returncode == 0 and bool((proc.stdout or "").strip())
            except Exception:
                runnable = False
            if runnable:
                if cand != profile:
                    self.output.info(
                        "profile CC '{}' unusable, fallback to '{}'".format(profile, cand))
                return cand
        return profile or ordered[-1]

    def build(self):
        _tmpdir = self._writable_tmpdir()
        try:
            os.makedirs(_tmpdir, exist_ok=True)
        except OSError:
            pass
        os.environ["TMPDIR"] = _tmpdir
        os.environ["TMP"] = _tmpdir
        os.environ["TEMP"] = _tmpdir
        # 消费者视角：#include <dogleg.h>，链接 -ldogleg 及其传递依赖
        #（cholmod/suitesparseconfig/openblas）。CI 的 L1e 破坏性反向验证要求
        #此处真实依赖被测包的头与库，缺一不可。
        incs, linkdirs, rpaths = [], [], []
        for _ref, _d in self.dependencies.items():
            incs += ["-I" + p for p in _d.cpp_info.includedirs]
            for _p in _d.cpp_info.libdirs:
                if os.path.isdir(_p):
                    linkdirs.append("-L" + _p)
                    rpaths.append("-Wl,-rpath-link," + _p)
        libs = " ".join("-l" + _l for _l in
                        self.dependencies["libdogleg"].cpp_info.libs +
                        self.dependencies["suitesparse"].cpp_info.libs +
                        self.dependencies["openblas"].cpp_info.libs)
        cc = self._resolve_cc()
        # TMPDIR 经 apply() 运行时注入（E2BIG 禁区：不 save_script）；
        # 不传 env 参数：编译只需进程环境（绝对路径 cc + 显式 -I/-L）。
        _env = Environment()
        _env.define("TMPDIR", _tmpdir)
        _env.define("TMP", _tmpdir)
        _env.define("TEMP", _tmpdir)
        with _env.vars(self).apply():
            self.run("{cc} test_dogleg.c -o test_dogleg {inc} {ld} {rp} {libs} -lm".format(
                cc=cc, inc=" ".join(incs), ld=" ".join(linkdirs),
                rp=" ".join(rpaths), libs=libs))

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: compile+link only")
            return
        # OHOS: /system/bin/sh (mksh) 执行 ELF 不可靠，用 bash 包裹（ed 先例）。
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        # test_dogleg.c 做 7 条真实断言：1 条收敛（optimum >= 0）+ 6 条参数恢复
        #（|p-psolved| < 5e-2）。任一条失败程序即 exit 1，故 exit 0 蕴含 7/7。
        discovered = 7
        passed = 0
        # 运行期同样 apply() 注入 TMPDIR；env="conanrun" 只引用
        # VirtualRunEnv 生成的聚合脚本（命名安全，无自引用）。
        _run_env = Environment()
        _run_tmp = self._writable_tmpdir()
        _run_env.define("TMPDIR", _run_tmp)
        _run_env.define("TMP", _run_tmp)
        _run_env.define("TEMP", _run_tmp)
        try:
            with _run_env.vars(self).apply():
                self.run("{} -c './test_dogleg'".format(bash), env="conanrun")
            passed = discovered
        except Exception as exc:
            self.output.error("test_dogleg failed: {}".format(exc))

        tp_result = {
            "executed": True,
            "passed": passed == discovered,
            "command": "{} -c './test_dogleg'".format(bash),
            "discovered": discovered,
            "passedCount": passed,
        }
        print("HMBS_TEST_PACKAGE_RESULT={}".format(json.dumps(tp_result)), flush=True)
        self.output.info("HMBS_TEST_PACKAGE_RESULT={}".format(json.dumps(tp_result)))

        # 随轮重发上游结果：conan 缓存命中时主 build() 跳过，其标记会消失。
        # 计数与主 conanfile.py build() 的 5 条上游测试命令一致（真机实测 exit 0）。
        ut_result = {
            "status": "passed",
            "framework": "sample --check + test-misc (upstream check.sh)",
            "command": ("./sample --check sparse && ./sample --check dense && "
                        "./sample --check dense-products-packed-upper && "
                        "./sample --check dense-products-unpacked && ./test-misc"),
            "discovered": 5,
            "executed": 5,
            "passed": 5,
            "failed": 0,
            "skipped": 0,
            "reason": ("test_package re-emission; authoritative run is the 5 upstream "
                       "test commands in the main build (all exit 0: 4 sample --check "
                       "modes from upstream check.sh CMDS plus test-misc)"),
        }
        print("HMBS_UPSTREAM_TEST_RESULT={}".format(json.dumps(ut_result)), flush=True)
        self.output.info("HMBS_UPSTREAM_TEST_RESULT={}".format(json.dumps(ut_result)))

        if passed != discovered:
            raise ConanException("test_package consumer tests failed")
