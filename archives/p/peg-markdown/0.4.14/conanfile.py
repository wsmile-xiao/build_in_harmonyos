import os

from conan import ConanFile
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.gnu import PkgConfigDeps, AutotoolsToolchain


class PegMarkdownConan(ConanFile):
    name = "peg-markdown"
    version = "0.4.14"
    description = ("PEG-based implementation of John Gruber's Markdown in C; "
                   "converts Markdown files (or stdin) to HTML, LaTeX, groff_mm "
                   "or ODF")
    license = ("MIT", "GPL-2.0-or-later")
    homepage = "https://github.com/jgm/peg-markdown"
    url = ""  # CI fills this
    topics = ("markdown", "peg", "converter", "cli")

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    # 上游 Makefile 用 `pkg-config --cflags/--libs glib-2.0` 取依赖，所以必须让
    # pkg-config 能找到 glib-2.0.pc：conan 生成的 .pc 指向包内真实路径，而制品
    # 自带的 glib-2.0.pc 里 prefix=/，直接用会得到 -I/include/... 这种废路径。
    generators = "PkgConfigDeps", "AutotoolsToolchain"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("glib/2.84.0.2")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: 编译器取自 Conan conf，不依赖 shell 环境变量。
        # tools.build:compiler_executables 是 dict，不能按 "...:c" 子键查询。
        cc = self.conf.get("tools.build:compiler_executables",
                           default={}, check_type=dict).get("c", "clang")

        # 上游 Makefile 是 in-tree 构建（无 out-of-tree 支持），三条命令都在
        # source_folder 里跑。
        src = self.source_folder

        # 1) 触发上游 $(PEGDIR) 规则：cp -r peg-0.1.4 peg 并应用上游自带的两个
        #    peg 补丁（目录已存在时该规则会被跳过，所以显式跑一次）。
        self.run("make peg", cwd=src, env=["conanbuild"])

        # 2) 构建内嵌的 PEG 解析器生成器 leg（构建期主机工具）。上游顶层 Makefile
        #    这一步硬编码 `CC=gcc`，而鸿蒙 worker 只有 clang（gcc → exit 127），
        #    所以先用 conan 的 C 编译器把它建好；这样第 3 步里 `CC=gcc make -C peg`
        #    只会看到 "Nothing to be done"，不会真的调用 gcc。
        self.run(f'make -C peg CC="{cc}" -j1', cwd=src, env=["conanbuild"])

        # 3) 生成 markdown_parser.c 并编译链接出 markdown。
        self.run(f'make CC="{cc}" PKG_CONFIG=pkg-config -j1', cwd=src,
                 env=["conanbuild"])

    def package(self):
        copy(self, "markdown", self.source_folder,
             os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        # 上游 0.4.14 的 Makefile 没有 install 目标，也不产出库文件，
        # 因此本包只交付 CLI 可执行文件。
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
