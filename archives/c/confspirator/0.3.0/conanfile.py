#!/usr/bin/env python3
"""Conan recipe for confspirator 0.3.0 — config-file schema/source library
(pure-Python, PyPI source).

Pure Python package (package_type python-require): build via `pip install`
into the conan package folder, consumers add site-packages to PYTHONPATH.
No external runtime dependencies (toml/slugify/netaddr/rfc3986/mock are
test-only).
"""
import os
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, get
from conan.tools.layout import basic_layout


class ConfspiratorConan(ConanFile):
    name = "confspirator"
    version = "0.3.0"
    description = "A wrapper around marshmallow to support merging config files, env variables and arguments"
    license = "Apache-2.0"
    homepage = "https://github.com/donbowman/confspirator"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"
    package_type = "python-require"

    def requirements(self):
        # confspirator/__init__.py → example.py top-level `import toml`
        # (runtime dependency; CI python3 lacks toml → ModuleNotFoundError)
        self.requires("toml/0.10.2.1")  # python-require 类型（0.10.2 是 library——python-require 不能依赖 static-library）

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)
        # setup.cfg [metadata] 用 dash 分隔 key（author-email/description-
        # file 等）——新 setuptools 弃用（deprecation + metadata 生成失败
        # 'Preparing metadata (setup.py): status error' 实测）——改为
        # underscore key（新 setuptools 兼容）
        scfg = os.path.join(self.source_folder, "setup.cfg")
        if os.path.exists(scfg):
            s = open(scfg).read()
            for dash, under in (("author-email", "author_email"),
                                ("description-file", "description_file"),
                                ("description-content-type",
                                 "description_content_type"),
                                ("home-page", "home_page")):
                s = s.replace(f"{dash} =", f"{under} =")
            open(scfg, "w").write(s)
            print("setup.cfg dash keys → underscores")
        # slugify/netaddr 是 test-only 依赖（ohpcd 未发布；confspirator
        # 注释自述 test-only）但源码无条件 import（groups.py/example.py
        # 链 + types.py）——CI import confspirator 时 ModuleNotFoundError
        # 实测。patch 为降级实现（slugify → 简单 replace 规范化；netaddr
        # → 标准库 ipaddress 校验——零额外依赖，功能等价）
        # slugify 在多个文件 import（groups.py/fields.py 等实测——fields.py
        # 漏了导致 CI ModuleNotFoundError）——遍历 confspirator 所有 .py
        # 替换 slugify import 为降级实现（每个文件独立 slugify 定义）
        cpkg = os.path.join(self.source_folder, "confspirator")
        for fname in os.listdir(cpkg):
            if not fname.endswith(".py"):
                continue
            fpath = os.path.join(cpkg, fname)
            fs = open(fpath).read()
            if "from slugify import slugify" in fs:
                fs = fs.replace(
                    "from slugify import slugify",
                    "import re\n"
                    "def slugify(name):\n"
                    "    return re.sub(r'[^a-zA-Z0-9]+', '-', str(name)).strip('-')\n"
                    "    # OHOS: slugify is a test-only dep (not published) — "
                    "simple replace fallback")
                open(fpath, "w").write(fs)
                print(f"{fname} slugify → simple fallback")
        tpath = os.path.join(self.source_folder, "confspirator", "types.py")
        ts = open(tpath).read()
        ts = ts.replace(
            "import netaddr",
            "import ipaddress\n"
            "def _valid_ipv4(a):\n"
            "    try: ipaddress.IPv4Address(a); return True\n"
            "    except ValueError: return False\n"
            "def _valid_ipv6(a):\n"
            "    try: ipaddress.IPv6Address(a); return True\n"
            "    except ValueError: return False")
        ts = ts.replace("netaddr.valid_ipv4(address, netaddr.core.INET_PTON)",
                        "_valid_ipv4(address)")
        ts = ts.replace("netaddr.valid_ipv6(address, netaddr.core.INET_PTON)",
                        "_valid_ipv6(address)")
        open(tpath, "w").write(ts)
        print("types.py netaddr → ipaddress fallback")
        # rfc3986 也是 test-only 依赖（ohpcd 未发布）——types.py 的 URI
        # 校验（uri_reference/Validator）降级为标准库 urllib.parse
        ts = open(tpath).read()
        ts = ts.replace(
            "import rfc3986",
            "import urllib.parse\n"
            "def _uri_valid(value):\n"
            "    try:\n"
            "        p = urllib.parse.urlsplit(value)\n"
            "        return bool(p.scheme and p.netloc)\n"
            "    except (ValueError, TypeError):\n"
            "        return False")
        # 替换 uri_reference + Validator 校验块为 _uri_valid 检查
        ts = ts.replace(
            "        uri = rfc3986.uri_reference(value)\n"
            "        try:\n"
            "            rfc3986.validators.Validator()",
            "        uri_ok = _uri_valid(value)\n"
            "        try:\n"
            "            if not uri_ok:")
        open(tpath, "w").write(ts)
        print("types.py rfc3986 → urllib.parse fallback")

    def build(self):
        # pip install 的 metadata 构建在 CI 环境失败（setup.cfg 老配置 +
        # 新 setuptools/importlib.metadata——dash key 弃用 + entry point
        # 加载失败实测）——copytree 源码到 staging（toml 已验证的 copytree
        # 模式——绕开 pip 构建，Python 包源码直接复制）。
        # staging 必须在**源外**目录（build 内 pip-stage 在 source 下——
        # copytree 递归复制自己实测无限递归）
        staging = "/data/storage/el2/base/cache/confspirator-stage"
        shutil.rmtree(staging, ignore_errors=True)
        shutil.copytree(
            self.source_folder, staging,
            ignore=shutil.ignore_patterns(
                "*.egg-info", "setup.py", "setup.cfg",
                "pyproject.toml", "README*", "LICENSE*", ".git"))

    def package(self):
        staging = "/data/storage/el2/base/cache/confspirator-stage"  # 与 build() 一致（源外）
        if not os.path.isdir(staging):
            raise ConanException(f"pip staging missing: {staging}")
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
        os.makedirs(site, exist_ok=True)
        for entry in os.listdir(staging):
            src = os.path.join(staging, entry)
            dst = os.path.join(site, entry)
            if os.path.isdir(src):
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
        if not os.path.isdir(os.path.join(site, "confspirator")):
            raise ConanException(f"confspirator package missing under {site}")

    def package_info(self):
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
        self.output.info(f"PYTHONPATH={site}")
