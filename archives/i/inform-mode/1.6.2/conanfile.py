#!/usr/bin/env python3
"""Conan recipe for inform-mode 1.6.2 (interpreted-source package: Emacs Lisp).

inform-mode is the Emacs major mode for Inform 6 interactive fiction source
(syntax highlighting, indentation, function navigation and compiler/interpreter
invocation). It ships as a single Emacs Lisp file (contrib/inform-mode.el)
inside the inform6 Unix distribution tarball; Debian builds its inform-mode
binary package from the same source lineage. Emacs is not ported to OHOS PC,
so this is a "no-native-runtime" package: build() is a drift check, package()
installs the elisp to share/emacs/site-lisp/ plus the GPL-3.0 text to
licenses/, package_id is cleared.

License: GPL-3.0-or-later (inform-mode.el header: "version 3, or any later").
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, get


class InformModeConan(ConanFile):
    name = "inform-mode"
    version = "1.6.2"
    description = ("Emacs major mode for Inform 6 interactive fiction source "
                   "(syntax highlighting, indentation and compiler invocation)")
    license = "GPL-3.0-or-later"
    homepage = "https://ifarchive.org/indexes/if-archive/infocom/compilers/inform6/source/"
    url = ""  # CI fills this
    package_type = "unknown"

    # 解释型源码包：无编译无链接，但保留 settings 以满足 CI L0 门禁的
    # 显式 settings 声明要求（与 inform6-library/kicad-demos 先例同款）。
    settings = "os", "compiler", "build_type", "arch"

    # 上游 contrib/inform-mode.el 实测字节数（构建期防漂移，与消费者
    # 探针的尺寸断言双保险）。6.44-r7 发行包内同文件 md5 一致
    # （316fd248c86e76fe61ea67a8dcc27058），上游 6.42→6.44 未更新该文件。
    _elisp = "inform-mode.el"
    _elisp_bytes = 63201
    _site_lisp_dir = os.path.join("share", "emacs", "site-lisp")

    def source(self):
        # 上游发行包 COPYING 只覆盖编译器/库（Inform DM4/Artistic 双许可），
        # elisp 自身头声明 GPL-3.0+；正文本地经 export_sources 提供，
        # 文件名避开上游 COPYING 防 get() 覆盖。
        get(self, **self.conan_data["sources"], strip_root=True)

    def export_sources(self):
        copy(self, "LICENSE-GPL-3.0.txt", src=self.recipe_folder,
             dst=self.export_sources_folder)

    def build(self):
        apply_conandata_patches(self)  # patches=[] 时为空操作，预留补丁入口
        # 无编译步骤。构建期校验上游文件，防止下载内容或目录结构静默
        # 漂移（inform6-library 同款范式）。
        path = os.path.join(self.source_folder, "contrib", self._elisp)
        if not os.path.isfile(path):
            raise ConanInvalidConfiguration(
                f"inform-mode 1.6.2 inventory drift: missing contrib/{self._elisp}"
            )
        size = os.path.getsize(path)
        if size != self._elisp_bytes:
            raise ConanInvalidConfiguration(
                f"inform-mode 1.6.2 size drift: {size} != {self._elisp_bytes}"
            )

    def package(self):
        # conan 2 basic_layout 在 package() 期间 source_folder 指向构建目录，
        # 其中混有 conan 生成的 *.sh 环境脚本与 conaninfo.txt——按指定
        # 文件名复制，天然规避（inform6-library 同款教训）。
        copy(self, self._elisp, src=os.path.join(self.source_folder, "contrib"),
             dst=os.path.join(self.package_folder, self._site_lisp_dir),
             keep_path=False)
        # 许可证：elisp 头声明 GPL v3 或更新；全文来自 export_sources
        # 本地文件（上游 COPYING 不覆盖本文件，故独立随包）。
        copy(self, "LICENSE-GPL-3.0.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.resdirs = [self._site_lisp_dir]
        self.cpp_info.libs = []
        self.runenv_info.define_path(
            "INFORMMODE_ELISP_DIR",
            os.path.join(self.package_folder, self._site_lisp_dir))

    def package_id(self):
        self.info.clear()
