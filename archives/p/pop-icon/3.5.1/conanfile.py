#!/usr/bin/env python3
"""Conan recipe for pop-icon 3.5.1 — Pop 图标主题（纯资源包）。

上游: https://github.com/pop-os/icon-theme （tag v3.5.1）
源码分发: https://github.com/pop-os/icon-theme/archive/refs/tags/v3.5.1.tar.gz

Pop 是 System76 为 Pop!_OS / GNOME 设计的图标主题，上游 meson 只做一件事：
`install_subdir('Pop', install_dir: <prefix>/share/icons)`，没有任何编译步骤。
本配方照此安装两套主题：

    share/icons/Pop/           主图标集（6228 SVG + 140 .cur + 8 .ani + 148 无扩展名光标
                               + index.theme + cursor.theme，共 6526 个条目）
    share/icons/Pop-Dark/      暗色图标集（2261 SVG + index.theme，共 2262 个条目）

上游的 `src/`（1226 个 SVG 源稿）、`master-render.py`、`meson.build`、`debian/`
是**渲染流水线**，不是主题本体，本包不安装（与已合入的 papirus-icon 同形态：
只交付可直接使用的 index.theme + 图标树）。

注意（OHOS 平台差异）：上游 tarball 共 **8 组「大小写折叠后同名」的条目** ——
7 个 `Pop/<N>x<N>/mimetypes/` 目录下各含实体 `text-x-r.svg` 与别名符号链接
`text-x-R.svg -> text-x-r.svg`；`Pop/scalable/apps/` 下含两条互为大小写变体的
别名链接 `org.gnome.weather-symbolic.svg` 与 `org.gnome.Weather-symbolic.svg`
（均指向实体 `weather-symbolic.svg`）。OHOS /storage 用户区大小写不敏感：前 7 个
别名退化为**自指链接**，直接 `get(..., strip_root=True)` 解包会以
`Errno 40 Symbolic link loop` 失败；后两条 GNOME 别名链接也只能落成 1 个目录项。
因此 `source()` 改为逐条目解包、把自指别名按实体文件写出，交付条目数为上游
6534 − 8 = **6526**；`test_package` 里逐组断言每个别名名字仍可被大小写不敏感地
解析到、且内容与实体文件一致（别名代表的那张图标没有丢）。

License: CC-BY-SA-4.0
"""

import os
import shutil
import tarfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import copy, download, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class PopIconConan(ConanFile):
    name = "pop-icon"
    version = "3.5.1"
    description = ("Pop icon theme — SVG icon set for Pop!_OS / GNOME "
                   "(Pop and Pop-Dark, with cursors and index.theme)")
    license = "CC-BY-SA-4.0"
    homepage = "https://github.com/pop-os/icon-theme"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # 纯资源包：无编译、无 settings，产物与架构无关（与 papirus-icon /
    # adwaita-fonts-mono 同形态）。
    package_type = "unknown"

    no_copy_source = True

    _themes = ("Pop", "Pop-Dark")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    @staticmethod
    def _self_referential_aliases(members):
        """挑出「大小写折叠后与自身同名」的符号链接。

        上游在 Pop/<N>x<N>/mimetypes/ 下同时放了实体 `text-x-r.svg` 和别名链接
        `text-x-R.svg -> text-x-r.svg`。Linux 上大小写敏感，两者是不同的名字，
        `tarfile` 建链接、chmod 都正常；OHOS 的 /storage 用户区大小写不敏感，
        两个名字指向同一个条目，别名链接退化成**自指链接**，`tarfile` 在链接后
        做 chmod/utime 时会拿到 `OSError: [Errno 40] Symbolic link loop`，整个
        源码解包当场失败（本包本地 Linux 校验全绿、CI 必挂，正是这个原因）。
        """
        aliases = {}
        for m in members:
            if m.issym() and "/" not in m.linkname \
                    and m.linkname.lower() == os.path.basename(m.name).lower():
                aliases[m.name] = m.linkname
        return aliases

    def source(self):
        src = self.conan_data["sources"][self.version]
        archive_path = os.path.join(self.source_folder, "pop-icon-3.5.1.tar.gz")
        download(self, src["url"], archive_path, sha256=src.get("sha256"))

        extract_to = os.path.join(self.source_folder, "_extracted")
        os.makedirs(extract_to, exist_ok=True)
        with tarfile.open(archive_path, "r:gz", errorlevel=0) as tf:
            members = tf.getmembers()
            # 手工剥离顶层目录（等价 strip_root=True），便于逐条目解包
            for m in members:
                if "/" in m.name:
                    m.name = m.path = m.name.split("/", 1)[1]
                else:
                    m.name = m.path = ""
            aliases = self._self_referential_aliases(members)

            for m in members:
                if not m.name or m.name in aliases:
                    continue  # 自指链接先跳过，稍后按实体文件补回
                tf.extract(m, path=extract_to, filter="data")

            # 用目标文件的内容补回别名：大小写敏感的文件系统上得到与上游等价的
            # 别名文件；大小写不敏感的文件系统上写的就是同一个文件（内容一致），
            # 不会再有自指链接。两条路径都不会触发 ELOOP。
            for name, target in aliases.items():
                target_path = os.path.join(extract_to, os.path.dirname(name), target)
                with open(target_path, "rb") as fh:
                    data = fh.read()
                with open(os.path.join(extract_to, name), "wb") as fh:
                    fh.write(data)

        for entry in os.listdir(extract_to):
            os.rename(os.path.join(extract_to, entry),
                      os.path.join(self.source_folder, entry))
        os.remove(archive_path)
        shutil.rmtree(extract_to, ignore_errors=True)

        apply_conandata_patches(self)

    def build(self):
        # 上游 meson 的 install_subdir('Pop') 不涉及编译器；这里只做本体自检：
        # 两套主题目录与各自的 index.theme 必须存在，否则装出来的"主题"不会被
        # 图标查找机制识别（比构建失败更隐蔽）。
        for theme in self._themes:
            theme_dir = os.path.join(self.source_folder, theme)
            if not os.path.isdir(theme_dir):
                raise ConanException(f"upstream theme directory missing: {theme}")
            index_theme = os.path.join(theme_dir, "index.theme")
            if not os.path.isfile(index_theme):
                raise ConanException(f"{theme}/index.theme missing from upstream")

        icons = sum(len(files) for theme in self._themes
                    for _root, _dirs, files in os.walk(
                        os.path.join(self.source_folder, theme)))
        self.output.info(f"pop-icon: {icons} files across {len(self._themes)} themes")

    def package(self):
        icons_root = os.path.join(self.package_folder, "share", "icons")

        for theme in self._themes:
            copy(self, "*", src=os.path.join(self.source_folder, theme),
                 dst=os.path.join(icons_root, theme))

        lic_dir = os.path.join(self.package_folder, "licenses")
        for name in ("COPYING", "LICENSE", "AUTHORS"):
            copy(self, name, src=self.source_folder, dst=lic_dir)

    def package_info(self):
        # 资源包：没有库、没有可执行文件、没有头文件（E255 的 forbid_1：
        # 不创建 commands.json、不伪造二进制测试）。
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []

        icons_root = os.path.join(self.package_folder, "share", "icons")
        self.cpp_info.resdirs = [os.path.join("share", "icons")]

        self.buildenv_info.define("POP_ICON_THEME_DIR", icons_root)
        self.runenv_info.define("POP_ICON_THEME_DIR", icons_root)

        # 与 papirus-icon 一致：把 share/ 前置进 XDG_DATA_DIRS，图标查找机制
        # （gtk-update-icon-cache / icon lookup）才能发现这两套主题。
        share_dir = os.path.join(self.package_folder, "share")
        existing = os.environ.get("XDG_DATA_DIRS", "/usr/local/share:/usr/share")
        self.buildenv_info.define("XDG_DATA_DIRS", f"{share_dir}:{existing}")
        self.runenv_info.define("XDG_DATA_DIRS", f"{share_dir}:{existing}")
        self.output.info(f"POP_ICON_THEME_DIR={icons_root}")
