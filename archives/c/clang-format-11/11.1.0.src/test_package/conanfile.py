#!/usr/bin/env python3
"""Conan test_package — clang-format-11 11.1.0.src L1 消费者测试

R34 反空壳：真实执行打包的 clang-format 二进制，并断言格式化输出
（input.cpp --style=LLVM 的输出必须逐字节等于 expected.cpp），不依赖被测包即失败。

另覆盖上游 clang-format 组件的全部交付物（对齐 clang/tools/clang-format/CMakeLists.txt
的 install() 规则）：
  - bin/git-clang-format：可执行位 + 上游脚本本体（usage 字符串）+ py_compile 语法通过；
  - share/clang/*：5 个集成脚本齐全 + 可执行位（LLVM 11 对它们均用 install(PROGRAMS)）。
git 相关 e2e 为 best-effort（git 非本包交付物，且 conanrun 子环境的 PATH 不含宿主工具链）。
"""
import os
import sys

from conan import ConanFile


class ClangFormat11TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["clang-format-11"].package_folder
        cf = os.path.join(pkg_folder, "bin", "clang-format")
        if not os.path.isfile(cf):
            raise Exception("clang-format binary not found at {}".format(cf))
        # 1) 真实执行打包二进制（--version 退出码 0 证明可执行）
        self.run('"{}" --version'.format(cf), env="conanrun")
        # 2) 真实格式化样例并逐字节断言（R34 核心断言）
        self.run('"{}" -style=LLVM input.cpp > formatted.out'.format(cf),
                 cwd=self.source_folder, env="conanrun")
        with open(os.path.join(self.source_folder, "formatted.out"), encoding="utf-8") as f:
            got = f.read()
        with open(os.path.join(self.source_folder, "expected.cpp"), encoding="utf-8") as f:
            expected = f.read()
        if got != expected:
            raise Exception(
                "clang-format 输出与期望不符\n--- got ---\n{}--- expected ---\n{}".format(got, expected))
        # 3) 版本号断言（11.1.0 —— 确保打包的确实是本版本）
        self.run('"{}" --version | grep -q "clang-format version 11.1.0"'.format(cf), env="conanrun")
        # 4) bin/git-clang-format（上游 install(PROGRAMS) 交付物）：交付物完整性 + 脚本本体断言。
        #    核心断言（决定性，不依赖外部工具）：
        #      a) 文件存在且具可执行位（上游 PROGRAMS 语义）；
        #      b) 内容含上游 usage 字符串（证明是上游 git 集成脚本本体，而非占位文件）；
        #      c) py_compile 语法通过（可被 python3 加载执行）。
        gcf = os.path.join(pkg_folder, "bin", "git-clang-format")
        if not os.path.isfile(gcf) or not os.access(gcf, os.X_OK):
            raise Exception("git-clang-format missing or not executable: {}".format(gcf))
        with open(gcf, encoding="utf-8", errors="replace") as f:
            gcf_src = f.read()
        if "git clang-format [OPTIONS]" not in gcf_src:
            raise Exception("git-clang-format 内容异常：未找到上游 usage 字符串")
        # 语法校验用内存 compile()（不用 py_compile：后者会在包内写 bin/__pycache__/*.pyc 污染制品）
        _chk_py = os.path.join(self.source_folder, "_gcf_syntax_check.py")
        with open(_chk_py, "w", encoding="utf-8") as f:
            f.write("import sys\n"
                    "p = sys.argv[1]\n"
                    "compile(open(p, encoding='utf-8', errors='replace').read(), p, 'exec')\n"
                    "print('syntax-ok')\n")
        self.run('"{}" "{}" "{}"'.format(sys.executable, _chk_py, gcf), env="conanrun")
        # 5) share/clang/* 集成脚本齐全 + 可执行位（上游 LLVM 11 均 install(PROGRAMS)）
        _share = os.path.join(pkg_folder, "share", "clang")
        for _f in ("clang-format-diff.py", "clang-format.py", "clang-format-sublime.py",
                   "clang-format.el", "clang-format-bbedit.applescript"):
            _p = os.path.join(_share, _f)
            if not os.path.isfile(_p):
                raise Exception("share/clang 交付物缺失: {}".format(_p))
            if not os.access(_p, os.X_OK):
                raise Exception("share/clang 交付物缺可执行位（上游 install(PROGRAMS)）: {}".format(_p))
        self.output.info("交付物齐全：bin/clang-format + bin/git-clang-format + share/clang/*(5)")
        # 6) best-effort：conanrun 子环境内若探测到 git，则实跑 git-clang-format --help。
        #    该脚本 main() 首行即调 `git config --list`，"能跑"依赖宿主外部 git（git 不是本包
        #    交付物），故探测不到或输出不含 usage 时仅告警，不判负（避免把宿主环境差异误判为打包缺陷）。
        _probe_py = os.path.join(self.source_folder, "_gcf_git_probe.py")
        _probe_out = os.path.join(self.source_folder, "_gcf_git_probe.out")
        if os.path.exists(_probe_out):
            os.remove(_probe_out)  # 清理上一轮残留，避免读到过期探测结果
        with open(_probe_py, "w", encoding="utf-8") as f:
            f.write("import shutil\n"
                    "open({!r}, 'w').write('1' if shutil.which('git') else '0')\n".format(_probe_out))
        self.run('"{}" "{}"'.format(sys.executable, _probe_py), env="conanrun", ignore_errors=True)
        _git_in_env = ""
        if os.path.isfile(_probe_out):
            with open(_probe_out, encoding="utf-8", errors="replace") as f:
                _git_in_env = f.read().strip()
        self.output.info("git-clang-format: conanrun 环境内 git 探测 = {}".format(_git_in_env or "未知"))
        if _git_in_env == "1":
            _gcf_log = os.path.join(self.source_folder, "git-clang-format.out")
            self.run('"{}" "{}" --help > "{}" 2>&1'.format(sys.executable, gcf, _gcf_log),
                     cwd=self.source_folder, env="conanrun", ignore_errors=True)
            with open(_gcf_log, encoding="utf-8", errors="replace") as f:
                gcf_out = f.read()
            if "git clang-format" in gcf_out:
                self.output.info("git-clang-format --help e2e 校验通过（输出含 usage）")
            else:
                self.output.warning("git-clang-format --help 未产出 usage（宿主环境相关，非交付物缺陷）："
                                    + gcf_out.strip().replace("\n", " | ")[:300])
