#!/usr/bin/env python3
"""Conan test_package — clang-format 22.1.8.src L1 消费者测试

R34 反空壳：真实执行打包的 clang-format 二进制，并断言格式化输出
（input.cpp --style=LLVM 的输出必须逐字节等于 expected.cpp），不依赖被测包即失败。
另覆盖上游 clang-format 组件的全部交付物：bin/git-clang-format（真实执行 --help）
与 share/clang/* 集成脚本（存在性 + clang-format-diff.py 可执行位）。
"""
import os
import sys

from conan import ConanFile


class ClangFormatTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["clang-format"].package_folder
        cf = os.path.join(pkg_folder, "bin", "clang-format")
        if not os.path.isfile(cf):
            raise Exception("clang-format binary not found at {}".format(cf))
        # 1) 真实执行打包二进制（--version 退出码 0 证明可执行 + 版本断言）
        self.run('"{}" --version'.format(cf), env="conanrun")
        # 2) 真实格式化样例并逐字节断言输出（R34 核心断言）
        self.run('"{}" -style=LLVM input.cpp > formatted.out'.format(cf),
                 cwd=self.source_folder, env="conanrun")
        with open(os.path.join(self.source_folder, "formatted.out"), encoding="utf-8") as f:
            got = f.read()
        with open(os.path.join(self.source_folder, "expected.cpp"), encoding="utf-8") as f:
            expected = f.read()
        if got != expected:
            raise Exception(
                "clang-format 输出与期望不符\n--- got ---\n{}--- expected ---\n{}".format(got, expected))
        # 3) 版本号断言（22.1.8 —— 确保打包的确实是本版本）
        self.run('"{}" --version | grep -q "clang-format version 22.1.8"'.format(cf), env="conanrun")
        # 4) bin/git-clang-format（上游 install(PROGRAMS) 交付物）：交付物完整性与脚本本体断言。
        #    核心断言（决定性，不依赖外部工具）：
        #      a) 文件存在且具可执行位（上游 PROGRAMS 语义）；
        #      b) 内容含上游 usage 字符串（证明是上游 git 集成脚本本体，而非占位文件）；
        #      c) ast.parse 语法校验通过（可被 python3 解析执行；不用 py_compile，见下）。
        #    增强断言（best-effort）：该脚本 main() 首行即调 `git config --list`，"能跑 --help"
        #    依赖宿主外部 git（git 不是本包交付物），且配方进程 PATH 与 self.run(env="conanrun")
        #    的实际 PATH 不同（conanrun 仅前置包 bin 目录）→ 先在 conanrun 子环境内探测 git，
        #    探测到才实跑 --help 并校验输出；失败仅告警，不判负（避免把宿主环境差异误判为打包缺陷）。
        gcf = os.path.join(pkg_folder, "bin", "git-clang-format")
        if not os.path.isfile(gcf) or not os.access(gcf, os.X_OK):
            raise Exception("git-clang-format missing or not executable: {}".format(gcf))
        with open(gcf, encoding="utf-8", errors="replace") as f:
            gcf_src = f.read()
        if "git clang-format [OPTIONS]" not in gcf_src:
            raise Exception("git-clang-format 内容异常：未找到上游 usage 字符串")
        # 语法自检：不用 py_compile —— 它会把字节码写到被编译文件同目录，污染已打包的
        # bin/ 目录（实测包内出现 bin/__pycache__/git-clang-formatcpython-312.pyc）。
        # 改用 ast.parse 纯解析校验（同样捕获语法错误，但不落盘），并断言包内无该残留。
        _syn_py = os.path.join(self.source_folder, "_gcf_syntax_check.py")
        with open(_syn_py, "w", encoding="utf-8") as f:
            f.write("import ast, sys\n"
                    "ast.parse(open(sys.argv[1], encoding='utf-8').read(), sys.argv[1])\n")
        self.run('"{}" "{}" "{}"'.format(sys.executable, _syn_py, gcf), env="conanrun")
        _stray = os.path.join(pkg_folder, "bin", "__pycache__")
        if os.path.isdir(_stray):
            raise Exception("打包目录被污染：bin/__pycache__ 不应存在（交付物必须纯净）: {}".format(_stray))
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
        else:
            self.output.info("conanrun 环境内无 git → 跳过 --help e2e（脚本本体已由静态断言覆盖）")
        # 5) share/clang/* 集成脚本（上游 install(FILES/PROGRAMS) 交付物）齐全
        share = os.path.join(pkg_folder, "share", "clang")
        required = ("clang-format-diff.py", "clang-format-sublime.py", "clang-format.el",
                    "clang-format.py", "clang-format-bbedit.applescript")
        missing = [n for n in required if not os.path.isfile(os.path.join(share, n))]
        if missing:
            raise Exception("share/clang 交付物缺失: {}".format(", ".join(missing)))
        if not os.access(os.path.join(share, "clang-format-diff.py"), os.X_OK):
            raise Exception("share/clang/clang-format-diff.py 缺少可执行位（上游 PROGRAMS）")
        self.output.info("clang-format 断言通过: 格式化逐字节一致 + git-clang-format 可执行 + share/clang 交付物齐全 (22.1.8)")
