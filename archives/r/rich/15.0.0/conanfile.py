#!/usr/bin/env python3
"""Conan recipe for rich 15.0.0 — pure Python terminal rich-text library.

rich is a pure Python (noarch) library for rich text / pretty printing in
the terminal (colors, tables, progress bars, markdown). No C/C++
compilation — package installs the `rich` module. Runtime deps: pygments
(+ markdown-it-py for Markdown rendering only). Same pattern as
python-magic/acronym noarch adaptions.
"""
import os

from conan import ConanFile
from conan.tools.files import get


class RichConan(ConanFile):
    name = "rich"
    version = "15.0.0"
    description = "rich — rich text and beautiful formatting in the terminal (pure Python)"
    license = "MIT"
    homepage = "https://github.com/Textualize/rich"
    url = ""

    # Pure Python noarch: no compiler needed, but OHOS profile requires
    # all four settings (CI L0p gate: missing compiler/build_type)
    settings = "os", "compiler", "build_type", "arch"
    # 运行时依赖：pygments（必填）；markdown-it-py 仅 Markdown 渲染用——
    # 本配方最小依赖集（test_package 消费验证；markdown 渲染可选）
    requires = "pygments/2.20.0"

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _py_ver(self):
        import sys
        return f"python{sys.version_info.major}.{sys.version_info.minor}"

    def build(self):
        # 纯 Python 包——无需 pip 构建（同 python-magic：环境 setuptools
        # egg_info 加载 entry point 报 pbr 缺失实测）——直接拷贝源码 rich/ 模块
        # 上游测试（rule 4 实测回填）：sdist 不含 tests/——从 GitHub 下载
        # 15.0.0 tag 的 tests/ 并运行 pytest，回填真实通过率
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        import sys
        import urllib.request
        import tarfile
        import subprocess

        # 下载上游 v15.0.0 tarball（含 tests/ 目录）
        gh_url = "https://codeload.github.com/Textualize/rich/tar.gz/refs/tags/v15.0.0"
        tarball = os.path.join(self.source_folder, "rich-src.tar.gz")
        urllib.request.urlretrieve(gh_url, tarball)
        with tarfile.open(tarball) as t:
            # 提取 tests/ 到 source_folder（无空格路径——CI git apply 教训）
            t.extractall(self.source_folder)
        src_root = os.path.join(self.source_folder, "rich-15.0.0")
        tests_dir = os.path.join(src_root, "tests")
        if not os.path.isdir(tests_dir):
            # tarball 顶层目录名可能带 v 前缀
            for name in os.listdir(self.source_folder):
                cand = os.path.join(self.source_folder, name, "tests")
                if os.path.isdir(cand):
                    tests_dir = cand
                    src_root = os.path.join(self.source_folder, name)
                    break
        # PYTHONPATH 指源码根（被测对象即打包源）——注意不能指 rich/ 子目录：
        # rich 自带 traceback.py 会遮蔽标准库 traceback（循环导入实测）
        env = dict(os.environ)
        env["PYTHONPATH"] = self.source_folder + \
            os.pathsep + env.get("PYTHONPATH", "")
        # test_brokenpipeerror 用 subprocess 调 `which python`/`which head`。
        # OHOS 沙箱 posix_spawn 不按 PATH 搜索相对名（shutil.which 能定位
        # /system/bin/which 但 subprocess 相对名 FileNotFoundError 实测——
        # python3/ls 相对名同样失败）——写 sitecustomize.py 强制 subprocess
        # 走 execvp（_USE_POSIX_SPAWN=False），Python 启动自动加载
        with open(os.path.join(self.source_folder, "sitecustomize.py"),
                  "w") as f:
            f.write("import subprocess\n"
                    "subprocess._USE_POSIX_SPAWN = False\n")
        # 运行 pytest（环境已装 pytest/attrs/pygments）
        r = subprocess.run(
            [sys.executable, "-m", "pytest", tests_dir, "-q", "--no-header"],
            cwd=src_root, env=env, capture_output=True, text=True)
        # 打印真实结果（rule 4 回填依据）
        tail = (r.stdout or "") + (r.stderr or "")
        print("[rich upstream tests] rc=%d" % r.returncode)
        for line in tail.splitlines()[-8:]:
            print("[rich upstream tests]", line)
        # 不因环境差异测试失败阻断构建——如实记录（CI 日志可见）
        self._upstream_test_result = tail

    def package(self):
        py_ver = self._py_ver()
        site_dst = os.path.join(
            self.package_folder, "lib", py_ver, "site-packages"
        )
        # 拷贝源码 rich/ 模块（含 _unicode_data/ 子包）
        import shutil
        shutil.copytree(os.path.join(self.source_folder, "rich"),
                        os.path.join(site_dst, "rich"))

    def package_info(self):
        # Pure Python — expose the site-packages path via PYTHONPATH
        py_ver = self._py_ver()
        site = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
        self.env_info.PYTHONPATH.append(site)
        self.cpp_info.libs = []
