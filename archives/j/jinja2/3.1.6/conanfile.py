#!/usr/bin/env python3
"""Conan recipe for Jinja2 3.1.6 — templating engine (pure Python).

上游 3.1.6 采用 **src 布局**（`src/jinja2/`）与 flit_core 构建后端
（pyproject.toml: requires = ["flit_core<4"], build-backend =
flit_core.buildapi）。纯 Python 无编译产物，故 package() 直接把 src/jinja2
拷入 site-packages（与 2.10.1 的 setuptools 平铺布局不同，需按 src 取路径）。

与 2.10.1 的关键差异（本配方因此**无需补丁**）：
  * 2.10.1 从 5 处 import `collections.Mapping` / `MutableMapping` /
    `MutableSet` / `MutableSequence`（py3.10 已移除），在 py3.12 下**无法
    import**，必须打 0001-collections-abc.patch；3.1.6 实测可直接 import
    并渲染模板 → patches 为空。
  * 2.10.1 把 markupsafe 钉在 1.1.1，因其 utils.py 依赖 MarkupSafe<2.1 才有的
    `soft_unicode`；3.1.6 的 pyproject 声明 `dependencies =
    ["MarkupSafe>=2.0"]`，故用 ohpcd 已发布的 markupsafe/3.0.3。

测试（R51，R51 要求真实运行并如实申报）：
  上游 requirements/tests.in 的测试依赖为 **pytest + trio**（tox.ini:
  deps = -r requirements/tests.txt，commands = pytest）。
  宿主 pytest 为 5.4.3 且与 py3.12 **不兼容**（实测 `TypeError: required
  field "lineno" missing from alias`，断言重写钩子失败）→ 按 setuptools 84.0.0
  先例，构建期从平台 pip 镜像取到独立目录（pytest>=7 + trio），再以该目录为
  PYTHONPATH 运行上游套件。
  取依赖失败或套件失败均**显式抛错**，不静默降级（杜绝「测试没跑但构建成功」）。
"""
import os
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout

# 上游 requirements/tests.in 声明的测试依赖（pytest + trio）
UPSTREAM_TEST_REQUIRES = ("pytest>=7", "trio")

# 平台 pip 镜像（与 CI 一致，见 ci/conan/setup.sh:55 PIP_COMMUNITY_INDEX）
PIP_INDEX = "https://pypi.cnb.cool/OpenHarmonyPCDeveloper/pypi/-/packages/simple"


class Jinja2Conan(ConanFile):
    name = "jinja2"
    version = "3.1.6"
    description = "A very fast and expressive template engine"
    license = "BSD-3-Clause"
    homepage = "https://github.com/pallets/jinja"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"
    package_type = "python-require"

    def export_sources(self):
        export_conandata_patches(self)  # 无补丁时空操作

    def requirements(self):
        # pyproject.toml: dependencies = ["MarkupSafe>=2.0"]
        # ohpcd 已发布 markupsafe/3.0.3（满足 >=2.0）。
        self.requires("markupsafe/3.0.3")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def _site_packages(self, dep_name):
        """Resolve a python-require dependency's site-packages directory."""
        dep = self.dependencies.get(dep_name)
        if dep is None:
            return None
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(dep.package_folder, "lib", py_ver, "site-packages")
        return site if os.path.isdir(site) else None

    def _py(self):
        """返回运行上游测试用的解释器。

        用宿主解释器（python3.12）而非依赖自带的解释器：jinja2 是纯 Python、
        无 ABI 绑定，且 markupsafe/3.0.3 为 python-require，其 site-packages
        只需在 PYTHONPATH 上即可被任意同版本 CPython 3.12 载入
        （与 2.10.1 / setuptools 84.0.0 先例一致）。
        """
        return sys.executable

    def _run_upstream_tests(self):
        """运行上游 pytest 套件并如实报告（R51）。"""
        tests_dir = os.path.join(self.source_folder, "tests")
        if not os.path.isdir(tests_dir):
            raise ConanException(
                "upstream tests/ not found; refusing to report a pass without "
                "running the suite (R51)")

        # 测试依赖独立目录（宿主 pytest 5.4.3 与 py3.12 不兼容，必须换新版）
        deps = os.path.join(self.build_folder, "test-deps")
        os.makedirs(deps, exist_ok=True)
        py = self._py()
        inst = subprocess.run(
            [py, "-m", "pip", "install", "--target", deps,
             "--break-system-packages", "--disable-pip-version-check",
             "--timeout", "120", "--retries", "3",
             "--index-url", PIP_INDEX, *UPSTREAM_TEST_REQUIRES],
            capture_output=True, text=True, timeout=1800)
        if inst.returncode != 0:
            tail = "\n".join(((inst.stdout or "") + (inst.stderr or ""))
                             .strip().splitlines()[-12:])
            raise ConanException(
                "could not obtain upstream test dependencies (pytest/trio) from "
                "the platform pip mirror, so the upstream suite could not be run "
                "(R51: refusing to report an unrun suite as passing). Tail:\n"
                + tail)

        env = dict(os.environ)
        paths = [deps, os.path.join(self.source_folder, "src")]
        dep_site = self._site_packages("markupsafe")
        if dep_site:
            paths.append(dep_site)
        if env.get("PYTHONPATH"):
            paths.append(env["PYTHONPATH"])
        env["PYTHONPATH"] = os.pathsep.join(paths)
        # 屏蔽宿主插件自动加载（宿主 pytest/typeguard 等与 py3.12 不兼容）
        env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
        # OHOS：新建目录属主被文件系统强制显示为挂载属主（20001006），
        # pytest 默认 <tmp>/pytest-of-<user> 属主检查必然 INTERNALERROR；
        # --basetemp 走 _given_basetemp 分支绕过（meson / setuptools 先例）。
        basetemp = os.path.join(self.build_folder, "pytest-basetemp")
        os.makedirs(basetemp, exist_ok=True)
        env["TMPDIR"] = os.path.join(self.build_folder, "tmp")
        os.makedirs(env["TMPDIR"], exist_ok=True)

        report = os.path.join(self.build_folder, "upstream-pytest-report.txt")
        res = subprocess.run(
            [py, "-m", "pytest", "tests", "-q", "--no-header",
             "-p", "no:cacheprovider", f"--basetemp={basetemp}"],
            cwd=self.source_folder, env=env,
            capture_output=True, timeout=5400)
        out = (res.stdout or b"").decode(errors="ignore")
        err = (res.stderr or b"").decode(errors="ignore")
        with open(report, "w") as f:
            f.write(out + "\n" + err)
        summary = out.strip().splitlines()[-1] if out.strip() else "n/a"
        self.output.info(f"upstream pytest: {summary}")
        if res.returncode != 0:
            tail = "\n".join((out + err).strip().splitlines()[-15:])
            raise ConanException(
                "upstream pytest suite failed (R51: refusing to report a "
                f"passing build with a failing suite). Tail:\n{tail}")

    def build(self):
        if not os.path.isdir(os.path.join(self.source_folder, "src", "jinja2")):
            raise ConanException("upstream src/jinja2 not found (src layout)")
        self._run_upstream_tests()

    def package(self):
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
        pkg_dir = os.path.join(site, "jinja2")
        os.makedirs(pkg_dir, exist_ok=True)
        # src 布局：源码在 <src>/jinja2
        src = os.path.join(self.source_folder, "src", "jinja2")
        for entry in sorted(os.listdir(src)):
            fpath = os.path.join(src, entry)
            if os.path.isdir(fpath):
                if entry == "__pycache__":
                    continue
                shutil.copytree(fpath, os.path.join(pkg_dir, entry),
                                ignore=shutil.ignore_patterns("__pycache__"))
                continue
            if entry.endswith((".c", ".h", ".so", ".pyc")):
                continue
            shutil.copy2(fpath, os.path.join(pkg_dir, entry))
        if not os.path.isfile(os.path.join(pkg_dir, "__init__.py")):
            raise ConanException(f"jinja2 package missing under {pkg_dir}")

    def package_info(self):
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
        # 声明 import 路径（aiohttp 教训：仅 print 不够，会让 CI 报
        # "No module named ..."）
        self.runenv_info.append_path("PYTHONPATH", site)
        self.buildenv_info.append_path("PYTHONPATH", site)
        self.output.info(f"PYTHONPATH={site}")
