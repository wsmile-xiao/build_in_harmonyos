#!/usr/bin/env python3
"""Conan recipe — adb-enhanced 2.8.0 (pure Python CLI tool).

Build:  pip wheel . --no-deps --no-build-isolation
Install: extract wheel to <prefix>/lib/python3.X/site-packages, create bin/adbe wrapper
Type:   application (console_scripts: adbe = adbe.main:main)
Deps:   docopt==0.6.2, psutil>=7.2.1 (pip 安装，非 conan 依赖)

R26 不适用（非系统同名库）；R38 适用（命令行工具，需 commands.json）。
"""
import os
import shutil
import sys
import zipfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class AdbEnhancedConan(ConanFile):
    name = "adb-enhanced"
    version = "2.8.0"
    description = "ADB-Enhanced is a Swiss army knife for Android testing and development"
    license = "Apache-2.0"
    homepage = "https://github.com/ashishb/adb-enhanced"
    url = ""

    # 纯 Python 应用，无 C/C++ 编译
    package_type = "application"
    settings = "os", "arch"  # 不需要 compiler/build_type

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # 清理 conan 导出的 patches/ 目录，避免 setuptools 自动发现为包
        patches_dir = os.path.join(self.source_folder, "patches")
        if os.path.isdir(patches_dir):
            shutil.rmtree(patches_dir)

        # 确保 setuptools/wheel 可用于 --no-build-isolation
        # pyproject.toml 缺少 [build-system] 段，pip 默认使用 setuptools.build_meta，
        # 但 build isolation 在 OHOS 上可能失败（无法拉取构建依赖）。
        python3 = shutil.which("python3")
        if not python3:
            raise ConanInvalidConfiguration(
                "python3 is required to build adb-enhanced; "
                "ensure python3 is on PATH")
        ret = self.run(
            f'"{python3}" -m pip install --quiet setuptools wheel 2>&1',
            env="conanbuild",
        )
        if ret != 0:
            raise ConanException(f"pip install setuptools/wheel failed with exit code {ret}")

        # pip wheel 构建（--no-deps：依赖单独安装到 deps/ 目录）
        wheel_dir = os.path.join(self.build_folder, "wheel")
        os.makedirs(wheel_dir, exist_ok=True)
        ret = self.run(
            f'"{python3}" -m pip wheel "{self.source_folder}" --no-deps '
            f'--no-build-isolation --wheel-dir="{wheel_dir}"',
            env="conanbuild",
        )
        if ret != 0:
            raise ConanException(f"pip wheel build failed with exit code {ret}")

    def package(self):
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site_pkg = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
        os.makedirs(site_pkg, exist_ok=True)

        # 解压 wheel 到 site-packages
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

        # 安装运行时依赖到 deps/ 目录（docopt + psutil）
        deps_target = os.path.join(self.package_folder, "deps")
        os.makedirs(deps_target, exist_ok=True)
        python3 = shutil.which("python3")
        self.run(
            f'"{python3}" -m pip install --no-deps '
            f'--target="{deps_target}" '
            f'"docopt==0.6.2" "psutil>=7.2.1,<8.0"',
            env="conanbuild",
        )

        # 修复 .so 文件权限（psutil C 扩展需要可执行权限）
        for root, dirs, files in os.walk(deps_target):
            for f in files:
                if f.endswith('.so') or f.endswith('.dylib'):
                    so_path = os.path.join(root, f)
                    try:
                        os.chmod(so_path, 0o755)
                    except OSError:
                        pass  # E046: SELinux 可能限制 chmod

        # 创建 bin/adbe wrapper — 设置 PYTHONPATH 指向 site-packages 和 deps
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        wrapper = os.path.join(bin_dir, "adbe")
        wrapper_content = (
            "#!/bin/sh\n"
            "# adbe wrapper — by Conan recipe\n"
            'WRAPPER_DIR="$(cd "$(dirname "$0")" && pwd)"\n'
            'PREFIX_DIR="$(cd "$WRAPPER_DIR/.." && pwd)"\n'
            f'SITE_PKG="$PREFIX_DIR/lib/{py_ver}/site-packages"\n'
            'DEPS_DIR="$PREFIX_DIR/deps"\n'
            'PYTHONPATH="$SITE_PKG:$DEPS_DIR${PYTHONPATH:+:$PYTHONPATH}" \\\n'
            '    exec python3 -m adbe.main "$@"\n'
        )
        with open(wrapper, "w") as f:
            f.write(wrapper_content)
        os.chmod(wrapper, 0o755)

        # 复制 LICENSE
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # 命令行工具，声明 bindirs 让 conan 知道可执行文件位置
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libs = []

        # 设置 PYTHONPATH 让 adbe 能找到包本身和依赖
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        self.runenv_info.append_path(
            "PYTHONPATH", os.path.join(self.package_folder, "deps"))
        self.runenv_info.append_path(
            "PYTHONPATH", os.path.join(self.package_folder, "lib", py_ver, "site-packages"))
        self.buildenv_info.append_path(
            "PYTHONPATH", os.path.join(self.package_folder, "deps"))
        self.buildenv_info.append_path(
            "PYTHONPATH", os.path.join(self.package_folder, "lib", py_ver, "site-packages"))
