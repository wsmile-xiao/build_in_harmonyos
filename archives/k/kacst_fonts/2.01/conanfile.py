#!/usr/bin/env python3
"""Conan recipe for kacst_fonts 2.01 — KACST 阿拉伯字体集（纯数据）。

上游: KACST（King Abdulaziz City for Science and Technology）字体集 2.01
源码分发: https://deb.debian.org/debian/pool/main/f/fonts-kacst/fonts-kacst_2.01+mry.orig.tar.bz2
（本配方走清华 TUNA 镜像同一份文件；"mry" 是 Debian 维护者的重打包标记，字体未改）

交付 14 套 TrueType 字体（阿拉伯文/波斯文 + 拉丁/数字装饰体），按 freedesktop 字体
约定装进 share/fonts/truetype/kacst/，并把 share/ 前置进 XDG_DATA_DIRS，
消费方（fontconfig / 文本栈）能直接按规范找到它们：

    share/fonts/truetype/kacst/*.ttf        14 个 TTF（KacstArt/Book/…/Qurn/TitleL）
    share/doc/kacst_fonts/{README,Copyright}
    licenses/LICENSE

**纯数据包，无编译步骤**：`build()` 只做本体自检（字体齐备、每个都可解析出
sfnt 头与表目录）；字体的**真实消费链**（表解析 → 码点覆盖 → 字体选择）由
消费者用例 `test_package/consumer_fonts.py` 执行。

License: 见 LICENSE / Copyright
"""

import os
import struct

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import copy, export_conandata_patches, apply_conandata_patches, get
from conan.tools.layout import basic_layout

SFNT_TAGS = (b"\x00\x01\x00\x00", b"true", b"ttcf", b"OTTO")


class KacstFontsConan(ConanFile):
    name = "kacst_fonts"
    version = "2.01"
    description = "KACST Arabic TrueType font collection (14 families)"
    license = "KACST-Fonts"
    homepage = "https://tracker.debian.org/pkg/fonts-kacst"
    url = "https://tracker.debian.org/pkg/fonts-kacst"
    package_type = "unknown"          # 纯数据包：不含编译器产物

    _fontdir = os.path.join("share", "fonts", "truetype", "kacst")

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        # 没有编译器参与；这里只做本体自检：字体目录必须存在，且每个 *.ttf
        # 都要有合法的 sfnt 头与表目录 —— 否则交付的是残包/坏字体。
        font_src = os.path.join(self.source_folder, "kacst")
        if not os.path.isdir(font_src):
            raise ConanException("upstream kacst/ directory missing")
        fonts = sorted(f for f in os.listdir(font_src) if f.lower().endswith(".ttf"))
        if not fonts:
            raise ConanException("upstream kacst/ contains no *.ttf")
        for name in fonts:
            path = os.path.join(font_src, name)
            with open(path, "rb") as handle:
                head = handle.read(12)
            if len(head) < 12 or head[:4] not in SFNT_TAGS:
                raise ConanException(f"{name}: not a valid sfnt/TrueType font")
            num_tables = struct.unpack(">H", head[4:6])[0]
            if num_tables == 0:
                raise ConanException(f"{name}: empty table directory")
        self.output.info(f"{self.name}: {len(fonts)} TrueType fonts validated")

    def package(self):
        copy(self, "*.ttf", src=os.path.join(self.source_folder, "kacst"),
             dst=os.path.join(self.package_folder, self._fontdir))
        for name in ("README", "Copyright"):
            copy(self, name, src=os.path.join(self.source_folder, "kacst"),
                 dst=os.path.join(self.package_folder, "share", "doc", self.name))
        copy(self, "LICENSE", src=os.path.join(self.source_folder, "kacst"),
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # 纯数据包：清空默认目录，只暴露 XDG 字体目录契约
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = [os.path.join("share", "fonts")]
        share_dir = os.path.join(self.package_folder, "share")
        existing = os.environ.get("XDG_DATA_DIRS", "/usr/local/share:/usr/share")
        for env in (self.buildenv_info, self.runenv_info):
            env.define("XDG_DATA_DIRS", f"{share_dir}:{existing}")
        self.output.info(f"fonts: {self._fontdir} (share/ prepended to XDG_DATA_DIRS)")
