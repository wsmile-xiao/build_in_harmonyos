from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, save
from conan.tools.layout import basic_layout
import os
import textwrap


class CmigemoConan(ConanFile):
    name = "cmigemo"
    version = "1.2-gh0.20220623"
    description = "C/Migemo - incremental search romaji-to-Japanese conversion library"
    license = "MIT"
    url = "https://github.com/koron/cmigemo"
    homepage = "https://github.com/koron/cmigemo"
    topics = ("migemo", "japanese", "input", "search")
    package_type = "shared-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # 顶层 Makefile/configure 依赖 nkf；本配方只构建库与工具，不构建字典，
        # 保持工具链声明完整以便上游 gcc 目标可用。
        self.tool_requires("nkf/2.1.5")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        exe = self.conf.get("tools.build:compiler_executables") or {}
        cc = exe.get("c", "clang")
        src = self.source_folder
        # 上游 configure 仅展开 config.mk 模板并硬性要求 nkf/qkc（字典构建用）；
        # 库与工具构建不依赖字典，这里生成等价 config.mk（沿用上游默认相对路径，
        # 产物落在源码树 build/ 下），不做网络与工具硬检查。
        config_mk = textwrap.dedent("""\
            srcdir = ./src/
            objdir = ./build/object/
            outdir = ./build/
            RM = rm -f
            CP = cp
            MKDIR = mkdir -p
            RMDIR = rm -rf
            CTAGS = ctags
            HTTP = curl -O
            PERL = perl
            BUNZIP2 = bzip2 -d
            GUNZIP = gzip -d
            FILTER_CP932 = nkf -s
            FILTER_EUCJP = nkf -e
            FILTER_UTF8 = iconv -t utf-8 -f cp932
            INSTALL = install -c
            O = o
            EXE =
            CONFIG_DEFAULT = compile/config_default.mk
            CONFIG_IN = compile/config.mk.in
            """)
        save(self, os.path.join(src, "config.mk"), config_mk)
        # CC/cflags 用 make 命令行变量覆盖（命令行优先级高于 makefile 内定义）；
        # 清空上游写死的 -rpath /usr/local/lib。
        self.run(
            f"make -f compile/Make_gcc.mak CC={cc} CFLAGS_MIGEMO='-fPIC -O2' LDFLAGS_MIGEMO=",
            cwd=src,
        )

    def package(self):
        src = self.source_folder
        # Make_gcc.mak 中库目标无 outdir 前缀：libmigemo.so* 落在源码根，
        # cmigemo 工具落在 $(outdir)（build/）下。
        copy(self, "libmigemo.so*", src,
             os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "cmigemo", os.path.join(src, "build"),
             os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "src/migemo.h", src, os.path.join(self.package_folder, "include"), keep_path=False)
        copy(self, "doc/README_j.txt", src, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["migemo"]
