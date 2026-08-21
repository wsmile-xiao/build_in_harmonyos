#!/usr/bin/env python3
"""Conan recipe for venc-pyc 3.2.7 — Python bytecode 子包形态的独立归档。

venc-pyc 是 Alpine 生态中 VenC（Python 静态博客生成器）的"预编译 Python
bytecode"子包（Alpine 用 py-compile/compileall 生成 .pyc 供 python3 直接
加载）。本任务按路径 A 将 venc-pyc 3.2.7 作为独立 Conan 包归档，源码来源为
VenC 3.2.7 的 PyPI sdist（同一上游项目 framagit.org/denissalem/VenC），见
conandata.yml。

包内容策略（Alpine pyc 子包依附主包存在，本包独立归档需自包含）：
  1. 保留运行所需模块文件 venc3/**/*.py（独立包必须可运行，不能只依赖主包）
  2. 额外提供预编译 bytecode：__pycache__/*.cpython-*.pyc（pyc 子包本质）
  3. 生成可执行入口 bin/venc（等价 console script venc3.main:venc_entry_point）

纯 Python、无 C 扩展，无 ELF 签名需求。
settings 声明 os/compiler/build_type/arch 四项以兼容 OHOS profile
（CI L0p 门禁要求四项，纯 Python 包不实际使用编译器，build() 无编译步骤）。
运行时命令依赖：python3（解释器）、pyyaml/unidecode（纯 Python 包，以解释器
方式存在，不链接任何 C 库，故不放入 requires()，在 manifest.yaml 中声明）。
"""
import os
import shutil
import sys
import glob

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class VencPycConan(ConanFile):
    name = "venc-pyc"
    version = "3.2.7"
    description = ("venc-pyc - precompiled Python bytecode sub-package of "
                   "VenC (Python static blog generator)")
    license = "GPL-3.0"
    homepage = "https://framagit.org/denissalem/VenC"
    url = "https://framagit.org/denissalem/VenC"
    topics = ("blog", "static-site", "generator", "python")

    package_type = "application"
    # 纯 Python 包，无编译器依赖；按 CI L0p 门禁要求声明四项 settings
    # （与 OHOS profile 兼容；build() 无编译步骤，compiler/build_type 不参与构建）
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        # 源码为 VenC 3.2.7 sdist（venc-pyc 的 pyc 子包来源于此）
        get(self, strip_root=True, **self.conan_data["sources"])
        apply_conandata_patches(self)

    def build(self):
        # 1) 确保构建工具 flit_core/setuptools/wheel 可用（PEP 517 wheel 构建需要），
        #    并安装运行时 Python 包依赖 unidecode/pyyaml（社区源有
        #    cp312-ohos_aarch64 预编译 wheel）：venc3.datastore 顶层 import unidecode，
        #    venc CLI 运行依赖 yaml，缺失会导致下方 build 自检与 CLI smoke 在
        #    干净 CI 环境失败（CI #27124 根因：本地有 unidecode 而 CI worker 无）。
        ret = self.run("python3 -m pip install flit_core setuptools wheel "
                       "unidecode pyyaml --quiet 2>&1",
                       cwd=self.source_folder)
        if ret != 0:
            raise ConanException(f"pip install build tools failed with exit code {ret}")

        # 2) PEP 517 wheel 构建验证（可复现的源码构建，产物平台无关）
        ret = self.run("python3 -m pip wheel --no-deps --no-build-isolation "
                       "-w dist . 2>&1", cwd=self.source_folder)
        if ret != 0:
            raise ConanException(f"pip wheel build failed with exit code {ret}")

        # 3) 递归 py_compile src/venc3/ 下所有 .py 生成 .pyc（venc-pyc 的本质）
        ret = self.run("python3 -m compileall -f -q src/venc3 2>&1",
                       cwd=self.source_folder)
        if ret != 0:
            raise ConanException(f"compileall failed with exit code {ret}")

        # 4) 包内基础自检（确定性，不依赖 venv/ensurepip）：
        #    a) import venc3 + 关键子模块（datastore 需要 unidecode 运行时包）
        #    b) pyc 直接加载校验
        old_py = os.environ.get("PYTHONPATH")
        os.environ["PYTHONPATH"] = os.path.join(self.source_folder, "src") + (
            os.pathsep + old_py if old_py else "")
        try:
            ret = self.run('python3 -c "import venc3; '
                           'from venc3.main import venc_entry_point; '
                           'assert callable(venc_entry_point); '
                           'import venc3.datastore; '
                           'print(\'build self-check: import OK\')" '
                           "2>&1", cwd=self.source_folder)
            if ret != 0:
                raise ConanException(f"build import self-check failed with exit code {ret}")

            pycs = sorted(glob.glob(os.path.join(
                self.source_folder, "src", "venc3", "__pycache__",
                "__init__.cpython-*.pyc")))
            if not pycs:
                raise ConanException(
                    "build self-check: no venc3 __init__ cpython-*.pyc generated")
            load_code = ("import importlib.util; "
                         f"spec=importlib.util.spec_from_file_location('venc3', '{pycs[0]}'); "
                         "m=importlib.util.module_from_spec(spec); "
                         "spec.loader.exec_module(m); "
                         "print('build self-check: pyc load OK')")
            ret = self.run(f"python3 -c \"{load_code}\" 2>&1",
                           cwd=self.source_folder)
            if ret != 0:
                raise ConanException(
                    f"build pyc-load self-check failed with exit code {ret}")
        finally:
            if old_py is None:
                os.environ.pop("PYTHONPATH", None)
            else:
                os.environ["PYTHONPATH"] = old_py

    def package(self):
        pv = f"python{sys.version_info.major}.{sys.version_info.minor}"
        dst_sp = os.path.join(self.package_folder, "lib", pv, "site-packages")
        os.makedirs(dst_sp, exist_ok=True)

        src_venc3 = os.path.join(self.source_folder, "src", "venc3")
        if not os.path.isdir(src_venc3):
            raise ConanException("源码包内未找到 src/venc3: " + src_venc3)

        # 1) 完整保留 venc3/ 模块（含 package_data/ 资源：themes、oembed 等，
        #    缺失会导致 venc CLI 无法运行）
        dst_venc3 = os.path.join(dst_sp, "venc3")
        shutil.copytree(src_venc3, dst_venc3)

        # 2) 递归生成 __pycache__/*.pyc（venc-pyc 的本质）
        ret = self.run(f"python3 -m compileall -f -q {dst_venc3} 2>&1",
                       cwd=self.source_folder)
        if ret != 0:
            raise ConanException(f"compileall on package failed with exit code {ret}")
        pycs = sorted(glob.glob(os.path.join(dst_venc3, "__pycache__",
                                             "__init__.cpython-*.pyc")))
        if not pycs:
            raise ConanException(
                "pyc 生成失败: __pycache__ 中未找到 venc3 __init__ cpython-*.pyc")

        # 3) LICENSE.md 归档（GPL-3.0）
        src_lic = os.path.join(self.source_folder, "LICENSE.md")
        if os.path.isfile(src_lic):
            shutil.copy2(src_lic, os.path.join(dst_sp, "LICENSE.md"))

        # 4) 可执行入口 bin/venc（等价 console script venc3.main:venc_entry_point）
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        cli = os.path.join(bin_dir, "venc")
        with open(cli, "w") as f:
            f.write("#!/usr/bin/env python3\n")
            f.write("import os, sys\n")
            f.write(f"_sp = os.path.join(os.path.dirname(os.path.dirname("
                    f"os.path.abspath(__file__))), 'lib', '{pv}', 'site-packages')\n")
            f.write("if _sp not in sys.path:\n    sys.path.insert(0, _sp)\n")
            f.write("from venc3.main import venc_entry_point\n")
            f.write("if __name__ == '__main__':\n    venc_entry_point()\n")
        os.chmod(cli, 0o755)

        # 5) 包内自检（fail-fast，写入 conan create 日志可审计）
        self._self_check(dst_sp, cli, pycs[0])

    def _self_check(self, dst_sp, cli, pyc_path):
        """包内自检：import / CLI -v / pyc 存在 / pyc 直接加载。"""
        # conan 2.29 self.run() 的 env 参数不接受 dict，改用 os.environ 临时注入
        old_env = os.environ.get("PYTHONPATH")
        os.environ["PYTHONPATH"] = dst_sp + (os.pathsep + old_env if old_env else "")
        try:
            # a) import smoke（venc3 + 关键子模块 + 入口可调用）
            ret = self.run('python3 -c "import venc3; '
                           'from venc3.main import venc_entry_point; '
                           'assert callable(venc_entry_point); '
                           'print(\'import venc3 OK\')" '
                           "2>&1", cwd=self.source_folder)
            if ret != 0:
                raise ConanException(f"import smoke failed with exit code {ret}")

            # b) CLI smoke（venc -v 版本命令，退出码 0）
            ret = self.run(f"{cli} -v >/dev/null 2>&1", cwd=self.source_folder)
            if ret != 0:
                raise ConanException(f"CLI smoke (venc -v) failed with exit code {ret}")

            # c) pyc 直接加载：从 .pyc 加载 venc3 并确认 venc_entry_point 可调用
            pyc_name = os.path.basename(pyc_path)
            pyc_dir = os.path.dirname(pyc_path)
            load_code = ("import importlib.util, sys; "
                         f"spec=importlib.util.spec_from_file_location('venc3', "
                         f"'{pyc_dir}/{pyc_name}'); "
                         "m=importlib.util.module_from_spec(spec); "
                         "spec.loader.exec_module(m); "
                         "print('pyc load OK:', m.__name__)")
            ret = self.run(f"python3 -c \"{load_code}\" 2>&1", cwd=self.source_folder)
            if ret != 0:
                raise ConanException(f"pyc direct-load check failed with exit code {ret}")
        finally:
            if old_env is None:
                os.environ.pop("PYTHONPATH", None)
            else:
                os.environ["PYTHONPATH"] = old_env

        # d) 断言 .py 与 .pyc 同时存在（独立包自包含策略）
        assert os.path.isfile(os.path.join(dst_sp, "venc3", "__init__.py")), \
            "venc3/__init__.py missing"

    def package_info(self):
        # 无 C 库/头文件，仅产出可执行 + site-packages 资源
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
        import sys
        pv = f"python{sys.version_info.major}.{sys.version_info.minor}"
        self.runenv_info.append_path(
            "PYTHONPATH",
            os.path.join(self.package_folder, "lib", pv, "site-packages"))
