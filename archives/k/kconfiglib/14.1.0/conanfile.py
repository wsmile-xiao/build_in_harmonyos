#!/usr/bin/env python3
"""Conan recipe for kconfiglib 14.1.0 on HarmonyOS PC.

Kconfiglib 是 Zephyr 项目维护的纯 Python Kconfig 解析库，附带一组命令行
配置工具（menuconfig / olddefconfig / savedefconfig / genconfig 等）。

OHOS 适配要点：
  * 纯 Python，无 C 扩展（setup.py 的 py_modules 全是 .py），不需要编译。
    适配工作 = 构建 wheel → 装到 lib/pythonX.Y/site-packages → PYTHONPATH 暴露。
  * ⚠️ guiconfig 依赖 Tkinter，而 OHOS 的 Python 不带 _tkinter 模块
    （实测：`import tkinter` → ModuleNotFoundError: No module named '_tkinter'），
    且 harmonybrew 无 tcl/tk。故本配方在 package() 阶段剔除 guiconfig.py，
    并在 notes.md 说明。其余 13 个模块均为纯文本处理，无平台依赖。
  * 上游测试是自带的自测套件 `testsuite.py`（3204 行，比对 tests/ 下 60 个
    Kconfig 用例），不是 pytest，直接以脚本方式运行。
  * R33：Python 解释器路径从环境/which 取，不硬编码。
"""
import os
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get

# Tkinter 依赖的模块，OHOS 上不可用（无 tcl/tk）
TK_MODULES = ("guiconfig.py",)

# 上游 setup.py 的 py_modules 清单（14 个，去掉 guiconfig 后交付 13 个）
PY_MODULES = (
    "kconfiglib.py",
    "menuconfig.py",
    "genconfig.py",
    "oldconfig.py",
    "olddefconfig.py",
    "savedefconfig.py",
    "defconfig.py",
    "alldefconfig.py",
    "allnoconfig.py",
    "allmodconfig.py",
    "allyesconfig.py",
    "listnewconfig.py",
    "setconfig.py",
)


class KconfiglibConan(ConanFile):
    name = "kconfiglib"
    version = "14.1.0"
    description = ("Kconfiglib — Zephyr 项目维护的 Kconfig 解析库，"
                   "附带 menuconfig/olddefconfig/savedefconfig 等配置工具")
    license = "ISC"
    homepage = "https://github.com/zephyrproject-rtos/Kconfiglib"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("python", "kconfig", "build-system", "zephyr")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("kconfiglib 仅在 Linux/OHOS 上验证过")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        python = self._python()
        src = self.source_folder

        # 上游测试套件 testsuite.py 把用例路径硬编码成 "Kconfiglib/tests/..."，
        # 它设计成从仓库的**父目录**运行（checkout 后目录名正是 Kconfiglib）。
        # Conan 解包后目录名是 Kconfiglib-14.1.0，故先在源内造一个同名目录。
        kdir = os.path.join(src, "Kconfiglib")
        if not os.path.isdir(kdir):
            os.makedirs(kdir, exist_ok=True)
            if os.path.isdir(os.path.join(src, "tests")):
                shutil.copytree(os.path.join(src, "tests"), os.path.join(kdir, "tests"))
            for f in os.listdir(src):
                if f.endswith(".py"):
                    shutil.copy(os.path.join(src, f), kdir)

        # 上游测试分两段：
        #   1) run_selftests()          纯 Kconfiglib 自测，无需外部依赖 → 本配方执行
        #   2) run_compatibility_tests() 与 Linux 内核 C 实现（scripts/kconfig）
        #      逐项比对，依赖内核源码树（`make kernelversion`）与 gcc。
        #      OHOS 上无内核源码树与对应构建环境，该段**不适用**，如实记录而非跳过不提。
        runner = os.path.join(src, "_run_selftests.py")
        with open(runner, "w") as f:
            f.write(
                "import sys, os\n"
                "sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))\n"
                "import testsuite\n"
                "testsuite.run_selftests()\n"
                "print('UPSTREAM_SELFTESTS_OK')\n"
            )
        self.run(f'"{python}" {os.path.basename(runner)}', cwd=src)

    def package(self):
        site_packages = os.path.join(
            self.package_folder, "lib",
            f"python{sys.version_info.major}.{sys.version_info.minor}",
            "site-packages",
        )
        os.makedirs(site_packages, exist_ok=True)

        # 拷贝上游的 13 个 .py 模块（用 setup.py 声明的 py_modules 清单）。
        # ⚠ 不能用 copy(self, "*.py", ...) —— 那会把 build() 里为跑测试造的
        #   _run_selftests.py 和 Kconfiglib/ 副本一并拷进去。
        for mod in PY_MODULES:
            copy(self, mod, src=self.source_folder, dst=site_packages)

        # 剔除依赖 Tkinter 的 guiconfig（OHOS 无 _tkinter）
        for m in TK_MODULES:
            p = os.path.join(site_packages, m)
            if os.path.exists(p):
                os.remove(p)

        # 清掉 build() 跑测试时生成的字节码缓存 —— 属构建产物，不该进制品
        pycache = os.path.join(site_packages, "__pycache__")
        if os.path.isdir(pycache):
            shutil.rmtree(pycache, ignore_errors=True)

        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = []
        site_packages = os.path.join(
            self.package_folder, "lib",
            f"python{sys.version_info.major}.{sys.version_info.minor}",
            "site-packages",
        )
        self.runenv_info.prepend_path("PYTHONPATH", site_packages)

    @staticmethod
    def _python():
        """R33：解释器路径不硬编码，按环境变量 → which → 当前解释器依次找。"""
        for cand in (os.environ.get("HMBS_PYTHON3"), shutil.which("python3"), sys.executable):
            if cand and os.path.isfile(cand):
                return cand
        raise ConanInvalidConfiguration("找不到 python3 解释器")
