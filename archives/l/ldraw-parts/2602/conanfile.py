#!/usr/bin/env python3
"""Conan recipe for ldraw-parts 2602 (pure data package).

The LDraw parts library is the official LEGO-style CAD parts library of
LDraw.org: plain-text .dat geometry files (parts, subparts, primitives),
texture PNGs and colour configuration files — no compilation, no linking.
Debian/Ubuntu ship it the same way (all-arch data package installed to
/usr/share/ldraw/, ldraw-parts 2602+ds-1). Follows the kicad-demos
pure-data pattern: build() is an inventory drift check, package() copies
the tree to share/ldraw/, package_id is cleared.

Upstream is the official complete.zip (LDraw update 2602, 2026-02), a
rolling URL with no fixed sha256. The recipe therefore pins the Debian
2602+ds-1 repacked orig.tar.xz from the Ubuntu pool (USTC/aliyun mirrors):
byte-identical to complete.zip except the 4 mklist utility files that
Debian excludes (mklist.exe/mklist1_4.zip/mklist1_6.zip/mklist-c.zip,
see debian/copyright Files-Excluded of ldraw-parts 2602+ds-1).

License: CC-BY-4.0 (the library was relicensed by LDraw.org; CA files
carry CC-BY-2.0 heritage — both legal texts ship in the package).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, get


class LDrawPartsConan(ConanFile):
    name = "ldraw-parts"
    version = "2602"
    description = ("LDraw parts library 2602: official LEGO-style CAD parts, "
                   "subparts, primitives, textures and colour configuration "
                   "(pure data)")
    license = "CC-BY-4.0"
    homepage = "https://library.ldraw.org/"
    url = ""  # CI fills this
    package_type = "unknown"

    # 纯数据/资源包：无编译、无链接，但保留 settings 以满足 CI L0 门禁的
    # 显式 settings 声明要求（与 kicad-demos 先例同款）。
    settings = "os", "compiler", "build_type", "arch"

    _resource_dir = os.path.join("share", "ldraw")

    # 2602 发行归档的静态清单（从钉死的 orig.tar.xz 实测计数，构建期
    # 防漂移校验）。
    _root_files = ("Readme.txt", "LDConfig.ldr", "LDCfgalt.ldr",
                   "LDConfig_TLG.ldr", "CAreadme.txt", "CAlicense.txt",
                   "CAlicense4.txt")
    # (子目录, 扩展名, 期望计数)：parts/s 与 parts/textures 分开计，
    # p/8 与 p/48 分开计（rule4 子目录教训：子目录也要数清楚）。
    _dir_counts = (
        ("parts", ".dat", 23839),           # 平铺零件
        ("parts/s", ".dat", 8813),          # 子零件
        ("parts/textures", ".png", 135),    # 贴图纹理
        ("p", ".dat", 1743),                # 标准图元
        ("p/8", ".dat", 127),               # 低分辨率图元
        ("p/48", ".dat", 920),              # 高分辨率图元
        ("models", "", 139),                # 更新记录 + 样例模型（135 txt + 2 dat + 2 ldr）
    )
    _expected_total = 35723

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def export_sources(self):
        # 配方自足：源码与数据全部经 conandata sources（get）下载，
        # 除 conanfile.py/conandata.yml 外无本地文件需要随配方导出。
        pass

    def build(self):
        apply_conandata_patches(self)  # patches=[] 时为空操作，预留补丁入口
        # 纯数据包无编译步骤。构建期校验上游文件清单，防止下载内容或
        # 目录结构静默漂移（kicad-demos 先例范式）。
        missing = [f for f in self._root_files
                   if not os.path.isfile(os.path.join(self.source_folder, f))]
        if missing:
            raise ConanInvalidConfiguration(
                "ldraw-parts 2602 inventory drift: missing files "
                + ", ".join(missing)
            )
        for sub, ext, expected in self._dir_counts:
            d = os.path.join(self.source_folder, sub)
            actual = sum(1 for f in os.listdir(d)
                         if f.endswith(ext)
                         and os.path.isfile(os.path.join(d, f)))
            if actual != expected:
                raise ConanInvalidConfiguration(
                    f"ldraw-parts 2602 {sub}{ext} count {actual} != {expected}"
                )
        # conan 2 basic_layout 会把源码拷入构建目录并在其中生成
        # conanbuild*.sh 等环境脚本，全量计数会误报；上游 35723 个文件
        # 无一为 .sh 或 conaninfo.txt，排除之即可，防漂移能力不受损
        # （inform6-library 真机实证同款）。
        total = sum(1 for _, _, files in os.walk(self.source_folder)
                    for f in files
                    if not f.endswith(".sh") and f != "conaninfo.txt")
        if total != self._expected_total:
            raise ConanInvalidConfiguration(
                f"ldraw-parts 2602 total file count {total} "
                f"!= {self._expected_total}"
            )

    def package(self):
        # conan 2 basic_layout 在 package() 期间 source_folder 指向构建目录，
        # 其中混有 conan 生成的 *.sh 环境脚本与 conaninfo.txt，copy("*") 会
        # 一并打包（inform6-library 真机实证 21 文件）。excludes 必须是
        # pattern 列表，单个逗号串会被整体当作一个 fnmatch pattern 而不生效。
        copy(self, "*", src=self.source_folder,
             dst=os.path.join(self.package_folder, self._resource_dir),
             excludes=["*.sh", "conaninfo.txt"])
        # 两版 CC 法律文本 + 再分发协议进 licenses/（inform6-library 同款布局）。
        for f in ("CAlicense.txt", "CAlicense4.txt", "CAreadme.txt"):
            copy(self, f, src=self.source_folder,
                 dst=os.path.join(self.package_folder, "licenses"),
                 keep_path=False)

    def package_info(self):
        self.cpp_info.resdirs = [self._resource_dir]
        self.cpp_info.libs = []
        # LDraw 消费工具（LeoCAD/LDView 等）以 LDRAWDIR 定位库根目录。
        libdir = os.path.join(self.package_folder, self._resource_dir)
        self.runenv_info.define_path("LDRAWDIR", libdir)

    def package_id(self):
        self.info.clear()
