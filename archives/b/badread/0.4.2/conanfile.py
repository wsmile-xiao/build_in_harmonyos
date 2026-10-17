#!/usr/bin/env python3
"""Conan recipe — badread 0.4.2 (pure Python wheel).

Build:  pip wheel . --no-deps
Install:解压 wheel 到 <prefix>/lib/python3.X/site-packages，创建 bin/badread wrapper
Type:   application (console_scripts: badread = badread.__main__:main)
Deps:   edlib, numpy, scipy, matplotlib (pip 安装，非 conan 依赖)

R26 不适用（非系统同名库）；R38 适用（命令行工具，需 commands.json）。
"""
import os
import shutil
import sys
import zipfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get
from conan.tools.layout import basic_layout


class BadreadConan(ConanFile):
    name = "badread"
    version = "0.4.2"
    description = "Badread: a long-read simulator that imitates many types of read problems"
    license = "GPL-3.0"
    homepage = "https://github.com/rrwick/Badread"
    url = "https://github.com/rrwick/Badread/archive/refs/tags/v0.4.2.tar.gz"

    # 纯 Python 应用，无 C/C++ 编译
    package_type = "application"
    settings = "os", "arch"  # 不需要 compiler/build_type

    def export_sources(self):
        # R28: 导出 conandata 中的补丁到 source_folder
        from conan.tools.files import export_conandata_patches
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # 应用 conandata 中声明的补丁（本包无补丁，保留调用以满足 R28）
        from conan.tools.files import apply_conandata_patches
        apply_conandata_patches(self)

        # pip wheel 构建（--no-deps：依赖由宿主 Python 环境提供）
        # 用绝对路径 python3，避免 conan 沙箱 PATH 找不到 pip
        wheel_dir = os.path.join(self.build_folder, "wheel")
        os.makedirs(wheel_dir, exist_ok=True)
        python3 = shutil.which("python3")
        if not python3:
            raise ConanInvalidConfiguration(
                "python3 is required to build badread; "
                "ensure python3 is on PATH")
        self.run(
            f'"{python3}" -m pip wheel "{self.source_folder}" --no-deps '
            f'--wheel-dir="{wheel_dir}"',
            env="conanbuild",
        )

    def package(self):
        # 解压 wheel 到 <prefix>/lib/python3.X/site-packages
        # ⚠️ 动态解析 Python 次版本：避免硬编码 python3.12，目标环境 Python
        # 升级（如 3.13）后 site-packages 路径变化导致 wrapper 找不到模块。
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site_pkg = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
        os.makedirs(site_pkg, exist_ok=True)

        wheel_dir = os.path.join(self.build_folder, "wheel")
        for whl in os.listdir(wheel_dir):
            if whl.endswith(".whl"):
                with zipfile.ZipFile(os.path.join(wheel_dir, whl)) as z:
                    z.extractall(site_pkg)
                break
        else:
            raise ConanInvalidConfiguration(
                f"No .whl file found in {wheel_dir}; "
                "pip wheel may have failed silently")

        # 创建 bin/badread wrapper — 设置 PYTHONPATH 指向同级 site-packages
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        wrapper = os.path.join(bin_dir, "badread")
        # wrapper 用相对路径解析同级 ../lib/python3.X/site-packages（py_ver 动态生成）
        wrapper_content = (
            "#!/bin/sh\n"
            "# badread wrapper — by Conan recipe\n"
            'WRAPPER_DIR="$(cd "$(dirname "$0")" && pwd)"\n'
            'PREFIX_DIR="$(cd "$WRAPPER_DIR/.." && pwd)"\n'
            f'SITE_PKG="$PREFIX_DIR/lib/{py_ver}/site-packages"\n'
            'if [ -d "$SITE_PKG/badread" ]; then\n'
            '    PYTHONPATH="$SITE_PKG${PYTHONPATH:+:$PYTHONPATH}" \\\n'
            '        exec python3 -m badread "$@"\n'
            'else\n'
            '    exec python3 -m badread "$@"\n'
            'fi\n'
        )
        with open(wrapper, "w") as f:
            f.write(wrapper_content)
        os.chmod(wrapper, 0o755)

    def package_info(self):
        # 命令行工具，声明 bindirs 让 conan 知道可执行文件位置
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
