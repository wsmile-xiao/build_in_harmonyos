#!/usr/bin/env python3
"""Conan recipe for ldraw-parts-free 2602 (pure data package, DFSG free subset).

The LDraw parts library is the official LEGO-style CAD parts library of
LDraw.org: plain-text .dat geometry files (parts, subparts, primitives),
colour configuration files and example models — no compilation, no linking.
This package ships the Debian DFSG **free subset** (Debian source package
ldraw-parts-free 2602+dfsg-1): every .dat carries exactly the CC-BY-4.0
license line, parts still under CC-BY-2.0 (or dual-licensed) plus their
dependency ancestors are excluded by Debian's gendfsgsrc.py, and the
textures directory is not carried at all. Result: 32387 files in the pinned
tarball vs 35723 in the complete library (sibling package ldraw-parts).

Follows the kicad-demos pure-data pattern (same as ldraw-parts 2602):
build() is an inventory drift check, package() copies the library tree to
share/ldraw/ (excluding mklist.c/include — build sources of the separate
Debian ldraw-mklist binary package, not library data), package_id is cleared.

License: CC-BY-4.0 (all shipped .dat files; both CA legal texts ship for
reference, CAlicense.txt being the CC-BY-2.0 heritage text).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, get


class LDrawPartsFreeConan(ConanFile):
    name = "ldraw-parts-free"
    version = "2602"
    description = ("LDraw parts library 2602 DFSG free subset: CC-BY-4.0-only "
                   "parts, subparts, primitives and colour configuration "
                   "(pure data; Debian ldraw-parts-free 2602+dfsg-1)")
    license = "CC-BY-4.0"
    homepage = "https://library.ldraw.org/"
    url = ""  # CI fills this
    package_type = "unknown"

    # 纯数据/资源包：无编译、无链接，但保留 settings 以满足 CI L0 门禁的
    # 显式 settings 声明要求（与 ldraw-parts / kicad-demos 先例同款）。
    settings = "os", "compiler", "build_type", "arch"

    _resource_dir = os.path.join("share", "ldraw")

    # dfsg orig 归档顶层目录。dpkg-source 生成的条目带 "./" 前缀
    # （./ldraw-parts-free-2602/...），conan get(strip_root=True) 的
    # commonpath 顶层判定遇 "./" 不剥离（真机 conan 2.29.1 实证：b/ 下
    # 仍为整目录）。故 get() 原样解压 + _src_root() 显式下钻，行为确定，
    # 不依赖 conan 的 strip 语义。
    _src_root_name = "ldraw-parts-free-2602"

    def _src_root(self):
        root = os.path.join(self.source_folder, self._src_root_name)
        if not os.path.isdir(root):
            raise ConanInvalidConfiguration(
                "ldraw-parts-free 2602: source root not found: " + root)
        return root

    # 2602+dfsg 发行归档的静态清单（从钉死的 dfsg orig.tar.xz 实测计数，
    # 构建期防漂移校验）。根文件 7 件与完整库逐字节一致（LDConfig 三件 +
    # Readme + CA 协议三件）；mklist.c 与 include/*.h 为 Debian repack.sh
    # 从 mklist1_6.zip 提取的 mklist 工具源码（dfsg 归档必带，但属
    # ldraw-mklist 二进制包构建输入，package() 不携带）。
    _root_files = ("Readme.txt", "LDConfig.ldr", "LDCfgalt.ldr",
                   "LDConfig_TLG.ldr", "CAreadme.txt", "CAlicense.txt",
                   "CAlicense4.txt")
    _aux_files = ("mklist.c",)          # dfsg 归档携带、package() 剔除
    _aux_dirs = (("include", ".h", 3),)  # 同上
    # (子目录, 扩展名, 期望计数)：free 子集经 gendfsgsrc.py 过滤后的精确
    # 计数（rule4 子目录教训：子目录也要数清楚）。textures 目录整类不
    # 存在于 dfsg 归档（verbatim 清单不含），单独负向断言。
    _dir_counts = (
        ("parts", ".dat", 21186),          # 平铺零件（完整库 23839，剔 2653）
        ("parts/s", ".dat", 8267),         # 子零件（完整库 8813，剔 546）
        ("p", ".dat", 1741),               # 标准图元（完整库 1743，剔 2）
        ("p/8", ".dat", 127),              # 低分辨率图元（与完整库一致）
        ("p/48", ".dat", 920),             # 高分辨率图元（与完整库一致）
        ("models", ".txt", 135),           # 更新记录（car/pyramid 样例模型被剔）
    )
    _expected_total = 32387               # 完整库 35723 - 3199 .dat - 135 PNG
                                          # - 4 样例模型 + mklist.c + 3 .h

    def source(self):
        get(self, **self.conan_data["sources"])

    def export_sources(self):
        # 配方自足：源码与数据全部经 conandata sources（get）下载，
        # 除 conanfile.py/conandata.yml 外无本地文件需要随配方导出。
        pass

    def build(self):
        apply_conandata_patches(self)  # patches=[] 时为空操作，预留补丁入口
        # 纯数据包无编译步骤。构建期校验上游文件清单，防止下载内容或
        # 目录结构静默漂移（kicad-demos 先例范式）。
        src = self._src_root()
        missing = [f for f in self._root_files
                   if not os.path.isfile(os.path.join(src, f))]
        if missing:
            raise ConanInvalidConfiguration(
                "ldraw-parts-free 2602 inventory drift: missing files "
                + ", ".join(missing)
            )
        for f in self._aux_files:  # dfsg 归档完整性：mklist.c 必须随档
            if not os.path.isfile(os.path.join(src, f)):
                raise ConanInvalidConfiguration(
                    f"ldraw-parts-free 2602 inventory drift: missing {f}"
                )
        for sub, ext, expected in self._dir_counts:
            d = os.path.join(src, sub)
            actual = sum(1 for f in os.listdir(d)
                         if f.endswith(ext)
                         and os.path.isfile(os.path.join(d, f)))
            if actual != expected:
                raise ConanInvalidConfiguration(
                    f"ldraw-parts-free 2602 {sub}{ext} count {actual} != {expected}"
                )
        for sub, ext, expected in self._aux_dirs:
            d = os.path.join(src, sub)
            actual = sum(1 for f in os.listdir(d)
                         if f.endswith(ext)
                         and os.path.isfile(os.path.join(d, f)))
            if actual != expected:
                raise ConanInvalidConfiguration(
                    f"ldraw-parts-free 2602 {sub}{ext} count {actual} != {expected}"
                )
        # free 子集关键负向断言：textures 目录整类不得出现（DeFi 口径
        # gendfsgsrc.py verbatim 清单不含 parts/textures）；models 下不得
        # 残留 car/pyramid 样例模型（CC-BY-2.0 双许可，被剔除）。
        if os.path.exists(os.path.join(src, "parts", "textures")):
            raise ConanInvalidConfiguration(
                "ldraw-parts-free 2602 drift: parts/textures must not exist"
            )
        for f in ("car.dat", "car.ldr", "pyramid.dat", "pyramid.ldr"):
            if os.path.exists(os.path.join(src, "models", f)):
                raise ConanInvalidConfiguration(
                    f"ldraw-parts-free 2602 drift: models/{f} must be excluded"
                )
        # conan 2 basic_layout 会把源码拷入构建目录并在其中生成
        # conanbuild*.sh 等环境脚本，全量计数会误报；上游 32387 个文件
        # 无一为 .sh 或 conaninfo.txt，排除之即可，防漂移能力不受损
        # （inform6-library 真机实证同款）。
        total = sum(1 for _, _, files in os.walk(src)
                    for f in files
                    if not f.endswith(".sh") and f != "conaninfo.txt")
        if total != self._expected_total:
            raise ConanInvalidConfiguration(
                f"ldraw-parts-free 2602 total file count {total} "
                f"!= {self._expected_total}"
            )

    def package(self):
        # 整树 copy("*") + excludes（ldraw-parts 先例范式）：conan 2 真机
        # 实证目录级 copy(self, dir, ...) 是空操作（2.29.1 包目录仅剩
        # 7 根文件），必须文件匹配式复制。excludes 必须是 pattern 列表
        # （单个逗号串整体当作一个 fnmatch pattern 不生效）；mklist.c 与
        # include/*.h 属 ldraw-mklist 二进制包构建输入，不携带。src 为
        # _src_root()（嵌套顶层目录），conan 环境脚本在 src 之外，无污染。
        src = self._src_root()
        dst = os.path.join(self.package_folder, self._resource_dir)
        copy(self, "*", src=src, dst=dst,
             excludes=["*.sh", "conaninfo.txt", "mklist.c", "include/*"])
        # 两版 CC 法律文本 + 再分发协议进 licenses/（ldraw-parts 同款布局）。
        for f in ("CAlicense.txt", "CAlicense4.txt", "CAreadme.txt"):
            copy(self, f, src=src,
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
