#!/usr/bin/env python3
"""Conan recipe — rpl 1.15.5（递归文本替换工具）

rpl 是 Python 命令行工具，运行时依赖 chardet（字符编码探测）。
OHOS 无 chardet 包 → 随包打包 chardet 纯 Python 模块 + PYTHONPATH
注入（绕开 setuptools 构建；rpl.1 由 help2man 生成不随源分发）。
"""
import os
import sys

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class RplConan(ConanFile):
    name = "rpl"
    version = "1.15.5"
    description = "rpl — intelligent recursive search/replace utility（Python）"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/rrthomas/rpl"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    # OHOS profile 要求四项 settings（L0p 门禁）；纯 Python 但需与 profile 对齐
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _py_ver(self):
        return f"python{sys.version_info.major}.{sys.version_info.minor}"

    def build(self):
        # 应用 0001-use-stdlib-re.patch（regex → 标准库 re，消除 C 扩展 .so）
        apply_conandata_patches(self)
        # 纯 Python，无编译；pip 安装 chardet + chainstream 到构建目录
        # （补丁后 rpl 仅依赖 chardet + chainstream，均纯 Python 无 .so）
        self.run("pip3 install --quiet --target "
                 f"{self.build_folder}/chardet_pkg chardet chainstream")

    def package(self):
        src = self.source_folder
        bin_dst = os.path.join(self.package_folder, "bin")
        site_dst = os.path.join(
            self.package_folder, "lib", self._py_ver(), "site-packages"
        )
        os.makedirs(bin_dst, exist_ok=True)
        os.makedirs(site_dst, exist_ok=True)
        # rpl 可执行入口：rpl 为 Python 包（rpl/__init__.py 的 main()），
        # 生成 wrapper 脚本（shebang env python3；写新文件+chmod）
        dst = os.path.join(bin_dst, "rpl")
        wrapper = (
            "#!/usr/bin/env python3\n"
            "from rpl import main\n"
            "if __name__ == '__main__':\n"
            "    main()\n"
        )
        with open(dst, "w", encoding="utf-8") as f:
            f.write(wrapper)
        os.chmod(dst, 0o755)
        # rpl 包（rpl/ 目录，含 __init__.py 等）——复制后修正版本获取：
        # __init__.py 用 importlib.metadata.version('rpl')（需安装为 dist，
        # 未安装抛 PackageNotFoundError，同 Gentoo ebuild src_prepare 处理）；
        # 用 shutil.copytree（copy 工具 pattern 对目录复制不可靠）
        import shutil
        shutil.copytree(
            os.path.join(src, "rpl"), os.path.join(site_dst, "rpl")
        )
        init_py = os.path.join(site_dst, "rpl", "__init__.py")
        with open(init_py, "r", encoding="utf-8") as f:
            content = f.read()
        content = content.replace(
            "importlib.metadata.version('rpl')", "'1.15.5'"
        )
        with open(init_py, "w", encoding="utf-8") as f:
            f.write(content)
        # chardet + regex 依赖（pip 安装产物）：用 glob 定位实际路径
        # （basic_layout 的 build_folder 可能含 build-release 子目录，
        # 直接拼接路径不可靠）→ shutil.copytree（同 rpl 包可靠方案）
        import glob as _glob
        cp_dirs = _glob.glob(
            os.path.join(self.build_folder, "**", "chardet_pkg"),
            recursive=True,
        )
        if cp_dirs:
            cp_dir = cp_dirs[0]
            # 仅 chardet + chainstream（纯 Python，无 C 扩展 .so）
            for pkg in ("chardet", "chainstream"):
                shutil.copytree(
                    os.path.join(cp_dir, pkg), os.path.join(site_dst, pkg)
                )
        # License
        copy(self, "COPYING", src=src,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        bin_path = os.path.join(self.package_folder, "bin")
        site_path = os.path.join(
            self.package_folder, "lib", self._py_ver(), "site-packages"
        )
        if os.path.isdir(bin_path):
            self.runenv_info.append_path("PATH", bin_path)
            self.buildenv_info.append_path("PATH", bin_path)
        if os.path.isdir(site_path):
            self.runenv_info.append_path("PYTHONPATH", site_path)
            self.buildenv_info.append_path("PYTHONPATH", site_path)
