import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, download


class MoeConan(ConanFile):
    name = "moe"
    version = "1.5"
    package_type = "application"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/moe/"
    description = "GNU moe — 全屏控制台文本编辑器（自带 moe 语法高亮与多文件编辑）"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conandata.yml"
    # 终端 UI 依赖 ncurses（上游 Makefile 硬编码 -lncurses，包侧提供 ncursesw）
    requires = "ncurses/6.6"

    def export_sources(self):
        # G1 门禁要求显式 export_sources() 方法（补丁目录随源码导出）
        copy(self, "patches/*", src=self.recipe_folder,
             dst=self.export_sources_folder)

    def source(self):
        download(self, self.conan_data["sources"]["url"],
                 "moe-1.5.tar.gz",
                 sha256=self.conan_data["sources"]["sha256"])
        self.run("tar -xzf moe-1.5.tar.gz --no-same-owner || true")
        self.run("cp -a moe-1.5/. . && rm -rf moe-1.5")

    def build(self):
        # 补丁应用调用（G1 门禁要求显式调用；当前无 patches/ 时为 no-op）
        apply_conandata_patches(self)
        # /tmp 只读（沙箱）——脚本内临时目录需可写 TMPDIR
        os.environ["TMPDIR"] = "/data/storage/el2/base/cache"
        os.makedirs(os.environ["TMPDIR"], exist_ok=True)
        # 上游为手写 configure（非 autoconf）：CXX/CPPFLAGS/CXXFLAGS/LDFLAGS
        # 以位置参数传入（不支持环境变量形式）
        deps = {str(d.ref.name): d.package_folder
                for d in self.dependencies.values()}
        nc = deps["ncurses"]
        self.run(
            f"./configure --prefix=/usr CXX=clang++ "
            f"CPPFLAGS='-I{nc}/include' "
            f"CXXFLAGS='-O2 -Wno-error' "
            f"LDFLAGS='-L{nc}/lib'",
            cwd=self.source_folder)
        # 上游 Makefile 硬编码 LIBS=-lncurses；ncurses/6.6 包导出 ncursesw
        # （宽字符版，lib dir 同时提供 ncursesw 符号）——链接期覆盖
        self.run("make -j2 LIBS='-lncursesw'", cwd=self.source_folder)
        # 上游无自动化测试（Makefile check 目标为占位 echo，见 notes.md
        # 清点证据）——消费者测试由 test_package 运行 moe 二进制完成

    def package(self):
        self.run("make install DESTDIR={}".format(self.package_folder),
                 cwd=self.source_folder)

    def package_info(self):
        # configure --prefix=/usr + make install DESTDIR=<pkg> → usr/*
        self.cpp_info.bindirs = ["usr/bin"]
