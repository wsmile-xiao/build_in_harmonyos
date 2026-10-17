#!/usr/bin/env python3
"""Conan recipe for lebiniou-data 3.67.0 (pure data package).

LEBINIOU (le biniou) is a music visualization program; this package ships
its data files — 1415 GIMP palette colormaps, image themes (115 PNG + 8
JPEG across four theme directories), path trajectories, sequence definitions
(JSON), the Vue front-end resources, and the upstream autopkgtest material
(FLAC sample, configuration, test script). No compilation and no linking:
upstream installs everything under $(datadir)/lebiniou/ via autotools;
Debian distributes it the same way (all-arch data package installed to
/usr/share/lebiniou/).

Follows the kicad-demos/inform6-library pure-data pattern: build() is an
inventory drift check, package() copies the six data directories to
share/lebiniou/ (excluding Makefile.am, which upstream does not install),
package_id is cleared.

License: GPL-2.0-only.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, get


class LebiniouDataConan(ConanFile):
    name = "lebiniou-data"
    version = "3.67.0"
    description = ("LEBINIOU music visualizer data package: GIMP palette "
                   "colormaps, image themes, path trajectories, sequence "
                   "definitions and the Vue web UI resources")
    license = "GPL-2.0-only"
    homepage = "https://gitlab.com/lebiniou/lebiniou-data"
    url = ""  # CI fills this
    package_type = "unknown"

    # 纯数据/资源包：无编译、无链接，但保留 settings 以满足 CI L0 门禁的
    # 显式 settings 声明要求（与 kicad-demos 先例同款）。
    settings = "os", "compiler", "build_type", "arch"

    # 上游发行归档的逐目录文件数（构建期防漂移校验，实测计数；
    # 含各目录内的 Makefile.am，install 时排除）。
    _expected_files = {
        "colormaps": 1416,
        "images": 128,
        "paths": 9,
        "sequences": 17,
        "vue": 169,
        "test": 4,
    }
    _root_markers = ("configure.ac", "Makefile.am", "COPYING", "README.md",
                     "AUTHORS", "ChangeLog", "THANKS")

    _install_dirs = ("colormaps", "images", "paths", "sequences", "vue",
                     "test")
    _resource_dir = os.path.join("share", "lebiniou")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def export_sources(self):
        # 配方自足：源码与数据全部经 conandata sources（get）下载，
        # 除 conanfile.py/conandata.yml 外无本地文件需要随配方导出。
        pass

    def build(self):
        apply_conandata_patches(self)  # patches=[] 时为空操作，预留补丁入口
        # 纯数据包无编译步骤。构建期校验上游文件清单，防止下载内容或目录
        # 结构静默漂移（kicad-demos 先例范式）。只数 6 个安装目录与根标记
        # 文件，conan 在构建目录生成的 *.sh 环境脚本与上游 debian/ 目录
        # 不参与计数。
        for sub, expected in self._expected_files.items():
            path = os.path.join(self.source_folder, sub)
            total = sum(1 for _, _, files in os.walk(path) for f in files)
            if total != expected:
                raise ConanInvalidConfiguration(
                    f"lebiniou-data 3.67.0 inventory drift: {sub} has "
                    f"{total} files, expected {expected}"
                )
        for marker in self._root_markers:
            if not os.path.isfile(os.path.join(self.source_folder, marker)):
                raise ConanInvalidConfiguration(
                    f"lebiniou-data 3.67.0 inventory drift: missing root "
                    f"file {marker}"
                )

    def package(self):
        # 上游 autotools 只安装六个数据目录（bootstrap/ 不在 SUBDIRS，
        # Makefile.am 是构建文件不参与安装），安装根为 $(datadir)/lebiniou
        # （Debian all 架构包 /usr/share/lebiniou/ 同款布局）。
        for sub in self._install_dirs:
            # conan copy() 的 excludes 按“相对 src 的完整路径”做 fnmatch
            # 精确匹配："Makefile.am" 只挡 src 顶层同名文件，嵌套目录
            # （主题目录、vue 子目录、sequences/json）里的必须靠
            # "*/Makefile.am" 覆盖（fnmatch 的 * 可跨 "/"，匹配任意深度）。
            # 真机 conan 2.29.1 首次验证实测 10 个嵌套 Makefile.am 漏装。
            copy(self, "*", src=os.path.join(self.source_folder, sub),
                 dst=os.path.join(self.package_folder, self._resource_dir,
                                  sub),
                 excludes=["Makefile.am", "*/Makefile.am"])
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.resdirs = [self._resource_dir]
        self.cpp_info.libs = []
        self.runenv_info.define_path(
            "LEBINIOU_DATA_DIR",
            os.path.join(self.package_folder, self._resource_dir))

    def package_id(self):
        self.info.clear()
