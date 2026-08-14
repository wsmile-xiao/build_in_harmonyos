#!/usr/bin/env python3
"""Conan recipe for show-in-file-manager 1.1.4 — 纯 Python 工具包。

上游：damonlynch/showinfilemanager（PyPI 包名 show-in-file-manager），
提供 Python 模块 `showinfm` 与命令行工具 `showinfilemanager`
（console script 入口 showinfm.showinfm:main）。MIT 许可证。

路径 A 适配要点（HarmonyOS PC）：
  1. 平台识别：上游 system/__init__.py 仅识别 Windows/Linux/Darwin，
     本机 platform.system() 返回 "HarmonyOS" 会直接 raise
     NotImplementedError（补丁 0001 按 Linux 处理）。
  2. WSL 探测：detect_wsl()/wsl_version() 读取 /proc/version，HarmonyOS
     上该文件不可读（Permission denied）（补丁 0002 捕获 OSError）。
  3. 纯 Python、无 C 扩展：settings 仅 os/arch，无编译器、无 ELF 签名。
  4. 运行时依赖：python3 解释器 + packaging（linux.py 无条件
     `import packaging.version`）；pyxdg 为可选导入（try/except
     ImportError）；pywin32 仅 Windows。openssl 等命令不涉及。
  5. 安装产物：lib/python3.x/site-packages/showinfm/ 模块树 +
     bin/showinfilemanager 可执行入口 + LICENSE。
"""
import os
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class ShowInFileManagerConan(ConanFile):
    name = "show-in-file-manager"
    version = "1.1.4"
    description = ("Open the system file manager and select files in it "
                   "(Python module showinfm + CLI showinfilemanager)")
    license = "MIT"
    homepage = "https://github.com/damonlynch/showinfilemanager"
    url = "https://github.com/damonlynch/showinfilemanager"
    topics = ("file-manager", "desktop", "python", "uri")

    package_type = "application"
    # 纯 Python 包：声明标准四项 settings 以满足 CI L0p 门禁
    # （os/compiler/build_type/arch），实际无 C 编译
    settings = "os", "compiler", "build_type", "arch"

    def configure(self):
        # OHOS profile 的 os.version 不是本配方消费的 settings 项
        self.settings.rm_safe("os.version")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, strip_root=True, **self.conan_data["sources"])
        apply_conandata_patches(self)

    def build(self):
        # PEP 517 wheel 构建验证（可复现的源码构建，产物平台无关）。
        # 不使用 --no-build-isolation：CI Worker 的 Python 环境未预装
        # setuptools.build_meta，标准隔离构建让 pip 按 pyproject.toml 的
        # [build-system] requires 在临时隔离环境中准备 setuptools+wheel 后端。
        ret = self.run("python3 -m pip wheel --no-deps "
                       "-w dist . 2>&1", cwd=self.source_folder)
        if ret != 0:
            raise ConanException(f"pip wheel build failed with exit code {ret}")

        # 包内自检：打补丁后模块可导入（HarmonyOS 平台）
        old_py = os.environ.get("PYTHONPATH")
        os.environ["PYTHONPATH"] = os.path.join(self.source_folder, "src") + (
            os.pathsep + old_py if old_py else "")
        try:
            ret = self.run('python3 -c "import showinfm; '
                           'from showinfm.system import current_platform; '
                           'print(\'import showinfm OK, platform:\', current_platform)" '
                           "2>&1", cwd=self.source_folder)
            if ret != 0:
                raise ConanException(
                    f"build import self-check failed with exit code {ret}")
        finally:
            if old_py is None:
                os.environ.pop("PYTHONPATH", None)
            else:
                os.environ["PYTHONPATH"] = old_py

    def package(self):
        pv = f"python{sys.version_info.major}.{sys.version_info.minor}"
        dst_sp = os.path.join(self.package_folder, "lib", pv, "site-packages")
        src_pkg = os.path.join(self.source_folder, "src", "showinfm")
        if not os.path.isdir(src_pkg):
            raise ConanException("源码包内未找到 showinfm 模块目录: " + src_pkg)

        # 1) 安装模块树（showinfm 包 + system 子包）
        shutil.copytree(src_pkg, os.path.join(dst_sp, "showinfm"))

        # 2) 许可证
        license_src = os.path.join(self.source_folder, "LICENSE")
        if os.path.isfile(license_src):
            shutil.copy2(license_src, os.path.join(self.package_folder, "LICENSE"))

        # 3) 可执行入口 bin/showinfilemanager（等价 console script）
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        cli = os.path.join(bin_dir, "showinfilemanager")
        with open(cli, "w") as f:
            f.write("#!/usr/bin/env python3\n")
            f.write("import os, sys\n")
            f.write(f"_sp = os.path.join(os.path.dirname(os.path.dirname("
                    f"os.path.abspath(__file__))), 'lib', '{pv}', 'site-packages')\n")
            f.write("if _sp not in sys.path:\n    sys.path.insert(0, _sp)\n")
            f.write("from showinfm.showinfm import main\n")
            f.write("if __name__ == '__main__':\n    main()\n")
        os.chmod(cli, 0o755)

        # 4) 包内自检（fail-fast，写入 conan create 日志可审计）
        self._self_check(dst_sp, cli)

    def _self_check(self, dst_sp, cli):
        old_env = os.environ.get("PYTHONPATH")
        os.environ["PYTHONPATH"] = dst_sp + (os.pathsep + old_env if old_env else "")
        try:
            ret = self.run('python3 -c "import showinfm; '
                           'from showinfm.showinfm import show_in_file_manager, '
                           'valid_file_manager, user_file_manager, stock_file_manager; '
                           'assert callable(show_in_file_manager); '
                           'assert callable(valid_file_manager); '
                           'assert callable(user_file_manager); '
                           'assert callable(stock_file_manager); '
                           'print(\'import + API smoke OK\')" 2>&1',
                           cwd=self.source_folder)
            if ret != 0:
                raise ConanException(f"import smoke failed with exit code {ret}")

            # CLI smoke：--version 与 -h 退出码 0
            ret = self.run(f"{cli} --version >/dev/null 2>&1", cwd=self.source_folder)
            if ret != 0:
                raise ConanException(
                    f"CLI smoke (showinfilemanager --version) failed with exit code {ret}")
            ret = self.run(f"{cli} -h >/dev/null 2>&1", cwd=self.source_folder)
            if ret != 0:
                raise ConanException(
                    f"CLI smoke (showinfilemanager -h) failed with exit code {ret}")
        finally:
            if old_env is None:
                os.environ.pop("PYTHONPATH", None)
            else:
                os.environ["PYTHONPATH"] = old_env

        # d) 断言模块树与 CLI 存在
        assert os.path.isdir(os.path.join(dst_sp, "showinfm")), "showinfm 模块缺失"
        assert os.path.isfile(cli), "showinfilemanager 入口缺失"

    def package_info(self):
        # 无 C 库/头文件，仅产出可执行 + site-packages 模块资源
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
        pv = f"python{sys.version_info.major}.{sys.version_info.minor}"
        self.runenv_info.append_path(
            "PYTHONPATH",
            os.path.join(self.package_folder, "lib", pv, "site-packages"))
