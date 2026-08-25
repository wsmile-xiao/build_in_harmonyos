#!/usr/bin/env python3
"""Conan recipe for antlr4-python3-runtime 4.9.3 — ANTLR4 Python runtime.

ANTLR4 generated-parser runtime (pure Python, noarch). Used by omegaconf
(pinned ==4.9.*). Source lives in src/antlr4 (setup.py handles package_dir).
No C/C++ compilation. No runtime deps.
"""
import os
import subprocess
import sys

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class Antlr4RuntimeConan(ConanFile):
    name = "antlr4-python3-runtime"
    version = "4.9.3"
    description = "ANTLR 4.9.3 runtime for Python 3"
    license = "BSD-3-Clause"
    homepage = "https://www.antlr.org/"
    url = ""

    # Pure Python noarch: no compiler needed (same pattern as soupsieve/acronym)
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # antlr4 纯 Python 无构建逻辑（setup.py 仅 package_dir 映射
        # {'': 'src'}）——pip install 的 setup.py egg_info 在 Python
        # 3.12 + setuptools 下反复失败实测（pbr entry point 加载失败，
        # --no-build-isolation + setuptools<70 + pbr 均无效）——
        # 直接复制 src/antlr4 到 staging site-packages（绕过构建系统，
        # 同 7zip/abbtr 等纯复制包模式）
        python_exe = sys.executable
        staging = os.path.join(self.build_folder, "staging")
        site_dst = os.path.join(staging, "lib", self._py_ver(), "site-packages")
        os.makedirs(site_dst, exist_ok=True)
        # copy pattern "antlr4" 对目录不生效（实测 staging 无 antlr4）；
        # keep_path=False 会平铺丢失子包目录（atn/dfa/tree/error/xpath——
        # 51 vs 57 .py 实测，__init__.py 导入子包失败）——
        # src 指向 antlr4 包目录 + keep_path=True 保留完整包结构
        copy(self, "*",
             src=os.path.join(self.source_folder, "src", "antlr4"),
             dst=os.path.join(site_dst, "antlr4"),
             keep_path=True)

        # Python 3.12 兼容修复（上游 antlr4 4.9.3 的 ATNDeserializer 对
        # bytes 迭代 int 调用 ord(c) 崩溃实测——TypeError: ord() expected
        # string of length 1, but int found——上游测试 xpathtest 加载
        # ExprParser 时触发）。conandata patches 机制在此纯复制包不生效
        # （apply 无输出实测）——复制后直接 python 替换 ATNDeserializer
        # 的 adjust 函数（同 patches/0001-py312-atn-deserializer.patch 内容）
        _atn = os.path.join(site_dst, "antlr4", "atn", "ATNDeserializer.py")
        with open(_atn) as _f:
            _src = _f.read()
        _old1 = "            v = ord(c)"
        _new1 = "            v = c if isinstance(c, int) else ord(c)"
        _old2 = "        temp[0] = ord(data[0])"
        _new2 = "        temp[0] = data[0] if isinstance(data[0], int) else ord(data[0])"
        if _old1 in _src and _old2 in _src:
            _src = _src.replace(_old1, _new1).replace(_old2, _new2)
            with open(_atn, "w") as _f:
                _f.write(_src)
            self.output.info("antlr4 ATNDeserializer Python3.12 compat applied")
        else:
            self.output.warning("antlr4 ATNDeserializer compat pattern not found")

        # 管理员规则 4：上游测试必须真实执行（GitHub git trees 双重核验
        # ——sdist 无测试但上游 antlr/antlr4 runtime/Python3/tests/ 有 16
        # 个测试文件：TestInputStream/TestFileStream/TestIntervalSet/
        # TestRecognizer/TestTokenStreamRewriter + ctest/run/xpathtest +
        # expr/parser/mocks 生成代码——ruamel-yaml 判例：sdist 无≠上游无）
        # ——运行时从上游 GitHub raw 下载 tests/ 到无空格目录 + 实跑
        # run.py（unittest 入口——5 个 Test* 类 + xpathtest），结果输出
        # 到 conan 日志供 PR 描述回填（同 swarp/sextractor 测试数据模式）
        import urllib.request
        tests_dir = "/data/storage/el2/base/cache/antlr4-tests"
        os.makedirs(tests_dir, exist_ok=True)
        _base = ("https://raw.githubusercontent.com/antlr/antlr4/4.9.3/"
                 "runtime/Python3/tests/")
        _files = (
            "TestInputStream.py", "TestFileStream.py", "TestIntervalSet.py",
            "TestRecognizer.py", "TestTokenStreamRewriter.py", "ctest.py",
            "run.py", "xpathtest.py", "__init__.py",
            "expr/ExprLexer.py", "expr/ExprParser.py", "expr/__init__.py",
            "parser/clexer.py", "parser/cparser.py", "parser/__init__.py",
            "mocks/TestLexer.py", "mocks/__init__.py",
        )
        _dl = 0
        for rel in _files:
            try:
                _url = _base + rel
                _req = urllib.request.Request(_url,
                                              headers={"User-Agent": "Mozilla/5.0"})
                _data = urllib.request.urlopen(_req, timeout=60).read()
                _fp = os.path.join(tests_dir, rel)
                os.makedirs(os.path.dirname(_fp), exist_ok=True)
                with open(_fp, "wb") as _f:
                    _f.write(_data)
                _dl += 1
            except Exception as _e:
                self.output.warning(f"antlr4 test download {rel} failed: {_e}")
        self.output.info(f"antlr4 upstream tests downloaded: {_dl}/{len(_files)}")
        if _dl > 0:
            # Python 3.12 兼容：上游测试 TestIntervalSet.py 用 assertEquals
            # 旧 API（Python 3.12 移除——实测 7 个 error 全为此，48/55）——
            # 替换为 assertEqual 让测试真实通过（同 ATNDeserializer 修复，
            # 属上游测试代码兼容修复——PR 描述如实记录）
            _tis = os.path.join(tests_dir, "TestIntervalSet.py")
            with open(_tis) as _f:
                _tsrc = _f.read()
            if "assertEquals" in _tsrc:
                _tsrc = _tsrc.replace("assertEquals", "assertEqual")
                with open(_tis, "w") as _f:
                    _f.write(_tsrc)
                self.output.info("antlr4 TestIntervalSet assertEquals->assertEqual applied")
            else:
                self.output.warning("antlr4 TestIntervalSet assertEquals pattern not found")
            # 实跑 unittest（run.py：5 个 Test* 类 + xpathtest——依赖 antlr4 包自身）
            _env = dict(os.environ)
            _env["PYTHONPATH"] = site_dst + os.pathsep + tests_dir
            _r = subprocess.run(
                [python_exe, os.path.join(tests_dir, "run.py")],
                capture_output=True, text=True, cwd=tests_dir, env=_env,
                timeout=600)
            _out = (_r.stdout or "") + (_r.stderr or "")
            self.output.info("=== antlr4 upstream tests result ===")
            for _line in _out.splitlines()[-20:]:
                self.output.info(_line)
            self.output.info(f"=== returncode={_r.returncode} ===")

    def package(self):
        # Copy staged site-packages + bin（soupsieve/acronym 同款模式）
        staging = os.path.join(self.build_folder, "staging")
        py_ver = self._py_ver()
        site_dst = os.path.join(
            self.package_folder, "lib", py_ver, "site-packages"
        )
        bin_dst = os.path.join(self.package_folder, "bin")

        site_src = None
        for candidate in (
            os.path.join(staging, "lib", py_ver, "site-packages"),
            os.path.join(staging, "lib", py_ver, "dist-packages"),
            os.path.join(staging, "local", "lib", py_ver, "site-packages"),
            os.path.join(staging, "local", "lib", py_ver, "dist-packages"),
        ):
            if os.path.isdir(candidate) and os.path.isdir(
                os.path.join(candidate, "antlr4")
            ):
                site_src = candidate
                break
        if site_src is None:
            raise Exception(
                f"antlr4 site-packages not found under staging={staging}"
            )
        copy(self, "*", src=site_src, dst=site_dst)

        for bin_src in (
            os.path.join(staging, "bin"),
            os.path.join(staging, "local", "bin"),
        ):
            if os.path.isdir(bin_src):
                copy(self, "*", src=bin_src, dst=bin_dst)

    def _py_ver(self):
        return f"python{sys.version_info.major}.{sys.version_info.minor}"

    def package_info(self):
        site = os.path.join(
            self.package_folder, "lib", self._py_ver(), "site-packages"
        )
        self.output.info(f"PYTHONPATH += {site}")
        self.env_info.PYTHONPATH.append(site)
