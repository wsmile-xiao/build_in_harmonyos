#!/usr/bin/env python3
"""Conan recipe for inform6-library 6.12.6 (pure data package).

The Inform 6 standard library ships as plain Inform-language text headers
(8 `.h` files plus documentation and license texts) — no compilation and no
linking. Debian/Ubuntu distribute it the same way (`all`-arch data package
installed to /usr/share/inform6/library/). Follows the kicad-demos pure-data
pattern: build() is an inventory drift check, package() copies the tree to
share/inform6/library/, package_id is cleared.

License: Artistic-2.0.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, get


class Inform6LibraryConan(ConanFile):
    name = "inform6-library"
    version = "6.12.6"
    description = ("Inform 6 standard library (inform6lib): parser, grammar and "
                   "verb library headers for interactive fiction")
    license = "Artistic-2.0"
    homepage = "https://ifarchive.org/indexes/if-archive/infocom/compilers/inform6/library/"
    url = ""  # CI fills this
    package_type = "unknown"

    # 纯数据/资源包：无编译、无链接，但保留 settings 以满足 CI L0 门禁的
    # 显式 settings 声明要求（与 kicad-demos 先例同款）。
    settings = "os", "compiler", "build_type", "arch"

    # 上游发行 zip 的静态文件清单（构建期防漂移校验，实测计数）。
    _headers = ("english.h", "grammar.h", "infglk.h", "infix.h", "linklpa.h",
                "parser.h", "verblib.h", "version.h")
    _docs = ("ARTISTIC", "COPYING", "README.txt", "ChangeLog", "caveats.txt",
             "voices_and_tenses.txt")
    _expected_total = 14  # 8 头文件 + 6 文档/许可证

    _resource_dir = os.path.join("share", "inform6", "library")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def export_sources(self):
        # 配方自足：源码与数据全部经 conandata sources（get）下载，
        # 除 conanfile.py/conandata.yml 外无本地文件需要随配方导出。
        pass

    def build(self):
        apply_conandata_patches(self)  # patches=[] 时为空操作，预留补丁入口
        # 纯数据包无编译步骤。构建期校验上游文件清单，防止下载内容或目录
        # 结构静默漂移（kicad-demos 先例范式）。
        missing = [f for f in self._headers + self._docs
                   if not os.path.isfile(os.path.join(self.source_folder, f))]
        if missing:
            raise ConanInvalidConfiguration(
                "inform6-library 6.12.6 inventory drift: missing files "
                + ", ".join(missing)
            )
        # conan 2 basic_layout 会把源码拷入构建目录并在其中生成
        # conanbuild*.sh 等环境脚本，全量计数会误报；上游 14 个文件
        # 无一为 .sh，排除之即可，防漂移能力不受损。
        total = sum(1 for _, _, files in os.walk(self.source_folder)
                    for f in files if not f.endswith(".sh"))
        if total != self._expected_total:
            raise ConanInvalidConfiguration(
                f"inform6-library 6.12.6 total file count {total} "
                f"!= {self._expected_total}"
            )

    def package(self):
        # conan 2 basic_layout 在 package() 期间 source_folder 指向构建目录，
        # 其中混有 conan 生成的 *.sh 环境脚本与 conaninfo.txt，copy("*") 会
        # 一并打包（真机实测 21 个文件）。excludes 必须是 pattern 列表，
        # 单个逗号串会被整体当作一个 fnmatch pattern 而不生效。
        copy(self, "*", src=self.source_folder,
             dst=os.path.join(self.package_folder, self._resource_dir),
             excludes=["*.sh", "conaninfo.txt"])
        copy(self, "ARTISTIC", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.resdirs = [self._resource_dir]
        self.cpp_info.libs = []
        libdir = os.path.join(self.package_folder, self._resource_dir)
        self.runenv_info.define_path("INFORM6_LIBRARY_DIR", libdir)

    def package_id(self):
        self.info.clear()
