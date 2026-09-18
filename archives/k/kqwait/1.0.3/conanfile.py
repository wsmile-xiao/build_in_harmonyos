#!/usr/bin/env python3
import os
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.build import can_run


class KqwaitConan(ConanFile):
    name = "kqwait"
    version = "1.0.3"
    license = "BSD-2-Clause"
    homepage = "https://github.com/sschober/kqwait"
    url = "https://github.com/sschober/kqwait"
    description = (
        "kqwait waits for write events on files or directories. "
        "OHOS port: BSD kqueue replaced by inotify."
    )
    topics = ("kqueue", "inotify", "filesystem", "monitoring", "wait")

    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "t/run_upstream_tests.sh", "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        # R39: 仅用官方源（github.com/sschober/kqwait tag kqwait-v1.0.3）
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        from conan.tools.env import VirtualBuildEnv
        VirtualBuildEnv(self).generate()

    def build(self):
        apply_conandata_patches(self)
        # 上游 Makefile 是 BSD 风格（kqwait: kqwait.c dirinfo.c + version.h 生成），
        # 其中 version.h 由 git describe 生成；tarball 无 .git → 手写 version.h。
        # tarball 内置 version.h 内容为 "v1.0.2-1-g0425-dirty"（tag 打包失误），
        # 上游 tag kqwait-v1.0.3 对应声明版本 v1.0.3。
        version_h = os.path.join(self.source_folder, "version.h")
        with open(version_h, "w") as f:
            f.write('#ifndef VERSION_H\n')
            f.write('#define VERSION_H\n')
            f.write('#define VERSION "v1.0.3"\n')
            f.write('#endif\n')
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c") or "clang"
        src = self.source_folder
        # 直接编译（上游 Makefile 仅一行 clang -Wall kqwait.c dirinfo.c -o kqwait，
        # 交叉构建下 Makefile 无 CC/CFLAGS 变量、写死 clang 路径意义不大，等价直呼 cc）
        self.run(f'"{cc}" -std=c99 -Wall -O2 '
                 f'-o "{src}/kqwait" "{src}/kqwait.c" "{src}/dirinfo.c"', cwd=src)

        # ── 上游正式测试（make test = prove -v t/*.pl，15 项断言）──
        # 上游测试 t/kqwait.pl 依赖 perl IPC::Run，本机 perl 无该模块且不可安装
        # （"Can't locate IPC/Run.pm in @INC"），prove 不可用 → 按 SPEC 3.3 声明豁免，
        # 断言 1:1 移植为 t/run_upstream_tests.sh（POSIX sh），在 build() 内执行。
        # 测试脚本置于源码树 t/ 下，与上游目录结构一致。
        if can_run(self):
            test_sh = os.path.join(src, "t", "run_upstream_tests.sh")
            if not os.path.exists(test_sh):
                # exports_sources 将 t/run_upstream_tests.sh 导出到 build 树
                exported = os.path.join(self.source_folder, "t", "run_upstream_tests.sh")
                if os.path.exists(exported):
                    test_sh = exported
            ret = self.run(f'sh "{test_sh}"', cwd=src, ignore_errors=True)
            if ret != 0:
                raise ConanException(
                    f"upstream test suite (ported) failed with exit code {ret} — "
                    "15 upstream assertions must pass (see t/run_upstream_tests.sh)")

    def package(self):
        copy(self, "kqwait", dst=os.path.join(self.package_folder, "bin"),
             src=self.source_folder, keep_path=False)
        # 许可证内嵌于 README.md（BSD 2-Clause, Sven Schober 2013），整文件归档
        copy(self, "README.md", dst=os.path.join(self.package_folder, "licenses"),
             src=self.source_folder, keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []  # headerless CLI tool, no library
