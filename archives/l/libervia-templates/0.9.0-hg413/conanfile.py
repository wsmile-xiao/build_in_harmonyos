#!/usr/bin/env python3
"""Conan recipe for libervia-templates 0.9.0-hg413 — Libervia (XMPP) official
Jinja2 template set (pure Python + template/i18n data).

上游是纯 Python 包，无 C/C++ 编译产物：
  * pyproject.toml 用 **hatchling** 构建后端，version 动态取自
    `sat_templates/__init__.py` 的 `__version__`（hg413 快照 = "0.9.0.dev0"；
    `sat_templates/VERSION` 文件仍为 "0.8.0"，为上游遗留，不参与构建）。
  * 包内容：`sat_templates/` 目录（`__init__.py` + `VERSION` +
    `i18n/`（babel 翻译 .po/.mo）+ `templates/`（default/bulma 两套主题的
    Jinja2 模板与静态资源））。无 Python 模块逻辑，仅有 `__version__`。
  * 按 jinja2/3.1.6 先例采用 python-require 布局：`package()` 把整个
    `sat_templates/` 拷入 `<pkg>/lib/python3.12/site-packages/`，
    `package_info()` 注入 PYTHONPATH。

运行依赖：jinja2/3.1.6（ohpcd 已发布，W0 预检 conan download 通过）。
上游 pyproject.toml 声明的 dependencies = []（模板渲染期由宿主/消费者
注入 jinja2 环境），但 sat_templates 本身是“Jinja2 模板包”，消费方必然
需要 jinja2，故声明为运行时依赖以保证依赖链完整。

测试（R51 如实申报）：
  hg413 快照 **无上游测试套件**：无 tests/ 目录、无 test_*.py / *_test.py、
  无 tox.ini / pytest.ini / setup.cfg / pyproject.toml 的 pytest 配置段
  （build() 内做真实检查并如实记录「上游无测试用例（0 个）」）。
  test_package/ 补充真实功能测试（R34）：import sat_templates 校验
  __version__、校验打包布局，并用 jinja2 的 FileSystemLoader 渲染打包内
  实际模板（default/bulma 两套主题的 error/404.html 全链：extends →
  base.html → components/common.html + i18n trans + script 注入），
  断言输出。任何一步失败都会使 conan create 失败，不以空壳测试冒充通过。
"""
import os
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (
    apply_conandata_patches, export_conandata_patches, get)
from conan.tools.layout import basic_layout


class LiberviaTemplatesConan(ConanFile):
    name = "libervia-templates"
    version = "0.9.0-hg413"
    description = "Templates for Libervia XMPP client"
    license = "AGPL-3.0-or-later"
    homepage = "https://libervia.org"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"
    package_type = "python-require"

    def export_sources(self):
        export_conandata_patches(self)  # 无补丁时空操作

    def requirements(self):
        # 模板包消费方必然用 jinja2 渲染；ohpcd 已发布 jinja2/3.1.6。
        self.requires("jinja2/3.1.6")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def _check_upstream_test_suite(self):
        """真实检查上游是否携带测试套件（R51 如实申报，禁止空壳）。"""
        root = self.source_folder
        # 1) tests/ 目录（任意命名）
        tests_dirs = [
            d for d in sorted(os.listdir(root))
            if os.path.isdir(os.path.join(root, d)) and d.lower() in (
                "tests", "test", "testing")]
        # 2) 测试文件（test_*.py / *_test.py）
        test_files = []
        for dirpath, _dirs, files in os.walk(root):
            if "templates" in dirpath:  # 模板静态资源目录，跳过
                continue
            for fname in sorted(files):
                if (fname.startswith("test_") and fname.endswith(".py")) or \
                   (fname.endswith("_test.py")):
                    test_files.append(os.path.relpath(
                        os.path.join(dirpath, fname), root))
        # 3) pytest / tox 配置
        pytest_cfgs = []
        for cfg in ("tox.ini", "pytest.ini", "setup.cfg", "pyproject.toml"):
            path = os.path.join(root, cfg)
            if not os.path.isfile(path):
                continue
            with open(path, encoding="utf-8", errors="ignore") as fh:
                text = fh.read()
            if ("pytest" in text and
                    any(mark in text for mark in
                        ("[tool.pytest", "[pytest", "[tool:tox", "[tox"))):
                pytest_cfgs.append(cfg)
        if tests_dirs or test_files or pytest_cfgs:
            raise ConanException(
                "upstream test suite detected but cannot be run faithfully: "
                f"tests_dirs={tests_dirs} test_files={test_files} "
                f"pytest_cfgs={pytest_cfgs} (R51: refusing to skip a real "
                "upstream suite)")
        self.output.info("upstream test suite: NONE "
                         "(no tests/ dir, no test_*.py, no tox/pytest config) "
                         "=> 上游无测试用例（0 个）")

    def build(self):
        pkg = os.path.join(self.source_folder, "sat_templates")
        if not os.path.isdir(pkg):
            raise ConanException(f"sat_templates/ missing in source: {pkg}")
        if not os.path.isfile(os.path.join(pkg, "__init__.py")):
            raise ConanException("sat_templates/__init__.py missing")
        if not os.path.isfile(os.path.join(pkg, "VERSION")):
            raise ConanException("sat_templates/VERSION missing")
        if not os.path.isdir(os.path.join(pkg, "templates")):
            raise ConanException("sat_templates/templates/ missing")
        if not os.path.isdir(os.path.join(pkg, "i18n")):
            raise ConanException("sat_templates/i18n/ missing")
        self._check_upstream_test_suite()

    def package(self):
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
        dst = os.path.join(site, "sat_templates")
        src = os.path.join(self.source_folder, "sat_templates")
        os.makedirs(site, exist_ok=True)
        shutil.copytree(
            src, dst,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        if not os.path.isfile(os.path.join(dst, "__init__.py")):
            raise ConanException(f"sat_templates package missing under {dst}")
        if not os.path.isdir(os.path.join(dst, "templates")):
            raise ConanException(f"sat_templates/templates missing under {dst}")

    def package_info(self):
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
        # 声明 import 路径（jinja2/aiohttp 教训：仅 print 不够，必须真正注入）
        self.runenv_info.append_path("PYTHONPATH", site)
        self.buildenv_info.append_path("PYTHONPATH", site)
        self.output.info(f"PYTHONPATH={site}")
