#!/usr/bin/env python3
"""Conan recipe — dynamite 0.1.1 (Autotools).

Adaptation notes:
- 上游 0.1.1（commit ccf573ad71ce）源码包不含预生成 configure（仅 configure.ac.in +
  bootstrap，E058 场景），且 bootstrap 依赖 host autotools（aclocal-1.16/automake-
  1.16/libtoolize，afflib CI #28005/#28408 教训：CI worker 权限不可用）。
  随配方导出本机正常构建的 generated/（configure + config.guess/config.sub +
  libtool 等），build() 复制进 source_folder 跳过 bootstrap。
- E007: config.guess/config.sub 已补 HarmonyOS 识别分支，configure 可生成
  aarch64-unknown-linux-ohos 三元组。
- E011/E112: 预生成 configure 的 config.status 临时目录已改为普通 mkdir
  （umask 077 + mktemp 在 HMDFS 受限环境不可写）。
- libtool 1.5.22 生成脚本的 $echo 未定义、$tool_oldlib 空引用 → 在 configure
  重新生成 libtool 后，用预生成修复版覆盖（echo 定义 + old_archive_cmds 用
  $oldlib）。
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class DynamiteConan(ConanFile):
    name = "dynamite"
    version = "0.1.1"
    description = "PKWARE Data Compression decompressor tool and library"
    license = "BSD-3-Clause"
    homepage = "https://github.com/twogood/dynamite"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)
        # 随配方导出本地生成的 configure 及 autotools 辅助文件（config.guess /
        # config.sub / install-sh / aclocal.m4 / Makefile.in / ltmain.sh 等），
        # 使 CI 无需执行 host autotools（见 build() 注释）。
        # 与 afflib 3.7.22 先例一致：pattern "generated/*" 保留子目录结构，
        # 导出到 export_sources_folder/generated/ 下（build() 内同名路径读取）。
        copy(self, "generated/*", self.recipe_folder, self.export_sources_folder)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        # 复制预生成 configure 及 autotools 辅助文件 → 跳过 bootstrap
        generated = os.path.join(self.export_sources_folder, "generated")
        if os.path.isdir(generated):
            copy(self, "*", generated, self.source_folder)
        configure_path = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(configure_path):
            self.run("sh bootstrap", cwd=self.source_folder, env="conanbuild")
        autotools.configure()
        # configure 会重新生成 libtool（1.5.22），其脚本缺 $echo 定义且
        # $tool_oldlib 空引用，否则 make 报 "X--tag=CC: inaccessible or not
        # found" / ranlib 无参数。
        # 注意：不能把本机预生成的 generated/libtool 整体覆盖过来——该副本
        # 带本机绝对路径（SED=/storage/Users/currentUser/usr/local/bin/sed
        # 等），CI 环境无此路径（实测 #62698 报
        # "../libtool: line 542: .../sed: No such file or directory"）。
        # 改为对 configure 在 build 树内实际生成的 libtool 做原位最小修复，
        # 保留该环境自身探测到的工具路径。
        for root in (self.build_folder, self.source_folder):
            for dirpath, _dirnames, filenames in os.walk(root):
                if "libtool" not in filenames:
                    continue
                target = os.path.join(dirpath, "libtool")
                with open(target, "r", encoding="utf-8", errors="replace") as fh:
                    lines = fh.readlines()
                out = []
                fixed_flag = False
                saw_echo_def = False
                for line in lines:
                    out.append(line)
                    if line.startswith("ECHO="):
                        saw_echo_def = True
                        # 紧跟 ECHO= 之后补小写 echo 定义（bash 环境无 ksh print 内建）
                        out.append("echo='echo'\n")
                    # 1.5.22 的 old_postinstall/old_archive 引用空变量
                    out[-1] = out[-1].replace("$tool_oldlib", "$oldlib")
                if saw_echo_def and "echo='echo'" not in "".join(out):
                    fixed_flag = False
                else:
                    fixed_flag = saw_echo_def
                if fixed_flag or "tool_oldlib" in "".join(out):
                    with open(target, "w", encoding="utf-8") as fh:
                        fh.writelines(out)
                    self.output.info(
                        "FIXED libtool in place: {}".format(target))
                else:
                    self.output.info(
                        "libtool already fixed, skipped: {}".format(target))
        # 刷新预生成文件的 mtime，阻止 automake 维护规则重生成：
        # configure.ac 的 AC_LIB_RPATH 宏未定义，干净 autoconf 重生成会报
        # "possibly undefined macro" hard error（E058 场景）。
        # 必须同时 touch config.status/Makefile：若 configure 新于
        # config.status，make 会触发 config.status --recheck 二次 configure，
        # 重新生成 libtool 覆盖上方补丁（第 10 轮实测）。
        # 对 build 与 source 两棵树统一 touch 到同一时刻，保证任何
        # $(srcdir) 解析下依赖都不新于目标（make 的 > 比较不触发）。
        now = __import__("time").time()
        for base in (self.build_folder, self.source_folder):
            for rel in ("configure", "configure.ac", "aclocal.m4", "config.h.in",
                        "config.status", "Makefile", "lib/Makefile",
                        "src/Makefile", "man/Makefile", "Makefile.in",
                        "lib/Makefile.in", "src/Makefile.in", "man/Makefile.in",
                        "libtool", "config.guess", "config.sub", "stamp-h1"):
                p = os.path.join(base, rel)
                if os.path.isfile(p):
                    os.utime(p, (now, now))
        autotools.make(args=["-j1"])
        autotools.make(args=["check"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # R26 口径：shared=False（默认）时包内只保留静态库。
        # libtool 1.5.22 在 arch 探测阶段仍会生成 .so 产物，CMakeDeps 的
        # find_library 会优先选中 .so，而 conanrun 对静态依赖不注入
        # LD_LIBRARY_PATH → test_package 运行时报 "Error loading shared
        # library libdynamite.so.0 / symbol not found"。移除 .so 使消费者
        # 确定性链接 .a，无运行时依赖。
        if not self.options.shared:
            libdir = os.path.join(self.package_folder, "lib")
            if os.path.isdir(libdir):
                for name in os.listdir(libdir):
                    if name.startswith("libdynamite.so"):
                        p = os.path.join(libdir, name)
                        if os.path.islink(p) or os.path.isfile(p):
                            os.unlink(p)

    def package_info(self):
        self.cpp_info.libs = ["dynamite"]
