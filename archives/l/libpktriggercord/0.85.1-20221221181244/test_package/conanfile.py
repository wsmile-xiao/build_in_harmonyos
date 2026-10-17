#!/usr/bin/env python3
"""Conan test_package — libpktriggercord 0.85.1-20221221181244.

消费者视角 L1 测试：直接编译 test_libpktriggercord.c 并链接被打包的
libpktriggercord.so，运行后解析被测程序**自己写出的** result 文件得到
discovered/passed/failed 真实计数（不与代码常量手工同步，R51/R52）。

走 direct-cc 路线（不引入 CMakeToolchain），避免 OHOS 上 CMake 编译器 ID 探测
在验证阶段引入额外失败面；编译器一律取自 Conan conf（R33）。
"""
import glob
import json
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.files import load
from conan.tools.layout import basic_layout

RESULT_RE = re.compile(r"discovered=(\d+)\s+passed=(\d+)\s+failed=(\d+)")
CASE_RE = re.compile(r"^case\s+(\S+)\s+(pass|fail)$", re.M)


class LibpktriggercordTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def _cc(self):
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cand = (compilers.get("c") or "").strip()
        if cand and os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
        if cand:
            self.output.warning("conf c compiler '%s' 不可用，回退 PATH" % cand)
        return shutil.which("clang") or shutil.which("cc") or "clang"

    def _pkg_paths(self):
        incs, libdirs = [], []
        for _ref, dep in self.dependencies.items():
            for i in dep.cpp_info.includedirs:
                incs.append(i if os.path.isabs(i) else os.path.join(dep.package_folder, i))
            for libdir in dep.cpp_info.libdirs:
                libdirs.append(libdir if os.path.isabs(libdir)
                               else os.path.join(dep.package_folder, libdir))
        return incs, libdirs

    def build(self):
        incs, libdirs = self._pkg_paths()
        libfile = ""
        for libdir in libdirs:
            cands = sorted(glob.glob(os.path.join(libdir, "libpktriggercord.*")))
            pref = [c for c in cands if c.endswith(".so")] + \
                   [c for c in cands if c.endswith(".a")]
            if pref:
                libfile = pref[0]
                break
        if not libfile:
            raise ConanException("libpktriggercord 产物未在 %r 中找到" % (libdirs,))
        src = os.path.join(self.source_folder, "test_libpktriggercord.c")
        out = os.path.join(self.build_folder, "test_libpktriggercord")
        os.makedirs(self.build_folder, exist_ok=True)
        self.run('"%s" -Wall -Wextra %s "%s" "%s" -lm -o "%s"' % (
            self._cc(), " ".join('-I"%s"' % i for i in incs), src, libfile, out))

    def test(self):
        if not can_run(self):
            self.output.info("交叉构建，host 测试二进制不可执行，跳过运行")
            return
        test_bin = os.path.join(self.build_folder, "test_libpktriggercord")
        result_file = os.path.join(self.build_folder, "test_result.txt")
        try:
            os.chmod(test_bin, 0o755)
        except OSError:
            pass
        if os.path.exists(result_file):
            os.remove(result_file)

        # 真实执行；非零退出码会由 conan 直接抛错，无需自行判定
        cmd = '"%s" "%s"' % (test_bin, result_file)
        self.run(cmd, env="conanrun")

        if not os.path.isfile(result_file):
            raise ConanException("测试程序未写出 result 文件，计数不可核验: %s" % result_file)
        text = load(self, result_file) or ""
        m = RESULT_RE.search(text)
        if not m:
            raise ConanException("result 文件无 RESULT 行，无法解析实测计数: %r" % text[:200])
        discovered, passed, failed = (int(x) for x in m.groups())
        cases = [{"name": n, "result": r} for n, r in CASE_RE.findall(text)]
        if discovered <= 0 or failed != 0 or passed != discovered:
            raise ConanException("libpktriggercord test_package 断言未全部通过: %s" % text)
        if len(cases) != discovered:
            raise ConanException("result 文件逐项数(%d)与汇总 discovered(%d) 不一致"
                                 % (len(cases), discovered))

        marker = {
            "executed": True,
            "passed": True,
            "command": cmd,
            "discovered": discovered,
            "passedCount": passed,
            "failedCount": failed,
            "cases": [c["name"] for c in cases],
            "framework": "direct-cc",
        }
        # code-style §19: 统一走 self.output，不用 print()
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker,
                                                               ensure_ascii=False))
