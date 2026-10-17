#!/usr/bin/env python3
"""Conan recipe for alot 0.12 — terminal MUA for the notmuch mail system.

alot 是纯 Python 终端邮件客户端（pyproject.toml + setuptools），无 C/C++
编译。核心依赖 notmuch2（Python 绑定 libnotmuch）、urwid、urwidtrees、
twisted、python-magic、configobj、gpg（python-gpgme）。

OHOS 适配要点：
- CI worker 网络受限 → 源码 tar 随 export_sources 提供（alot-0.12-src.tar.gz，
  来自 GitHub v0.12 tag），本地解压（参照 lv 先例）。
- 依赖库：notmuch（项目内 built 但 remote 无制品、系统无 libnotmuch.so）→
  配方内自包含构建 notmuch 0.38.3（依赖 xapian-core/1.4.26 remote 制品 +
  gmime 3.2.7 自包含构建 + talloc/2.4.4 remote 制品 + zlib），参照 aegean
  自包含 genometools 先例；gpgme/1.24.0 与 file/5.48.1（libmagic）为 conan
  依赖；urwid/urwidtrees/twisted/configobj/python-magic/gpg/notmuch2 为
  pip 依赖（build() 中安装供测试使用）。
- 打包：pip wheel --no-deps 提取到 <prefix>/lib/python3.X/site-packages +
  bin/alot wrapper（参照 check-jsonschema 先例）。
"""
import os
import shutil
import sys
import zipfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout


class AlotConan(ConanFile):
    name = "alot"
    version = "0.12"
    description = "Terminal-based mail user agent for the notmuch mail system"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/pazz/alot"
    url = ""  # CI fills this

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        # gpgme（python-gpg 绑定依赖）、file（python-magic 依赖 libmagic）
        self.requires("gpgme/1.24.0")
        self.requires("file/5.48.1")
        # notmuch（libnotmuch.so + notmuch.h）+ notmuch2（Python cffi 绑定）：
        # 上游 pytest 的 notmuch2 数据库环境依赖，随本仓库适配 PR 提供
        self.requires("notmuch/0.38.3")
        self.requires("notmuch2/0.34.3")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        # conandata.yml sources 提供 GitHub v0.12 tag 双 URL（gh-proxy 镜像 +
        # github 直连）+ sha256 校验——conan get() 标准下载（lv 先例同款）。
        # 不用 export_sources 打包 tarball：.gitignore 忽略 archives/**/*.tar.gz
        # （归档铁律禁提交 tar.gz 压缩包——algotutor 教训），tarball 无法随
        # PR 提交，CI 上 export_sources 复制不到必然报错。
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        python3 = shutil.which("python3")
        if not python3:
            raise ConanInvalidConfiguration("python3 is required to build alot")
        # 安装运行时依赖（notmuch2 走 conan 依赖，其余 pip）供 test_package 使用；
        # wheel 构建 --no-deps
        notmuch2 = self.dependencies["notmuch2"]
        nm2_site = os.path.join(notmuch2.package_folder, "lib", "python3.12", "site-packages")
        if not os.path.isdir(nm2_site):
            nm2_site = os.path.join(notmuch2.package_folder, "lib", "python3", "site-packages")
        notmuch = self.dependencies["notmuch"]
        glib = self.dependencies["glib"]
        xapian = self.dependencies["xapian-core"]
        ld_paths = ":".join([
            os.path.join(notmuch.package_folder, "lib"),
            os.path.join(glib.package_folder, "lib"),
            os.path.join(xapian.package_folder, "lib"),
        ])
        self.run(
            f"export PYTHONPATH={nm2_site}:$PYTHONPATH "
            f"LD_LIBRARY_PATH={ld_paths}:$LD_LIBRARY_PATH; "
            f'"{python3}" -m pip install --quiet '
            f'"urwid>=1.3.0" "urwidtrees>=1.0.3" '
            f'"twisted>=18.4.0" "python-magic" "configobj>=4.7.0" "gpg>1.10.0" '
            f'2>&1 || true  # deps optional, wheel build is --no-deps',
            env="conanbuild",
        )
        wheel_dir = os.path.join(self.build_folder, "wheel")
        os.makedirs(wheel_dir, exist_ok=True)
        self.run(
            f'"{python3}" -m pip wheel "{self.source_folder}" --no-deps '
            f'--wheel-dir="{wheel_dir}"',
            env="conanbuild",
        )

    def package(self):
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
            raise ConanInvalidConfiguration(f"No .whl file found in {wheel_dir}")
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        wrapper = os.path.join(bin_dir, "alot")
        wrapper_content = (
            "#!/bin/sh\n"
            "# alot wrapper — by Conan recipe\n"
            'WRAPPER_DIR="$(cd "$(dirname "$0")" && pwd)"\n'
            'PREFIX_DIR="$(cd "$WRAPPER_DIR/.." && pwd)"\n'
            f'SITE_PKG="$PREFIX_DIR/lib/{py_ver}/site-packages"\n'
            'if [ -d "$SITE_PKG/alot" ]; then\n'
            '    PYTHONPATH="$SITE_PKG${PYTHONPATH:+:$PYTHONPATH}" \\\n'
            '        exec python3 -m alot "$@"\n'
            'else\n'
            '    exec python3 -m alot "$@"\n'
            'fi\n'
        )
        with open(wrapper, "w") as f:
            f.write(wrapper_content)
        os.chmod(wrapper, 0o755)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
