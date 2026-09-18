#!/usr/bin/env python3
"""Conan recipe — libnfc-tools 1.8.0（libnfc 工具集拆分包）.

libnfc-tools 不是独立上游项目，而是 libnfc-1.8.0.tar.bz2 内 utils/ + examples/
命令行工具的拆分包（Alpine libnfc-tools-1.8.0-r2 / SUSE libnfc.spec 同口径）。
本配方只编译 21 个工具，链接制品仓已发布的 libnfc/1.8.0（R36：依赖已发布，
禁止在本配方内重编库本体）；不定义 HAVE_CONFIG_H（工具源码对 config.h 宏
零使用，include 均有 #ifdef HAVE_CONFIG_H 守卫，已核验）。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, save
from conan.tools.gnu import AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout

# 21 个工具与其源文件（相对源码根），与上游 utils/Makefile.am、
# examples/Makefile.am 及 Alpine libnfc-tools-1.8.0 内容一一对应。
# pn53x-tamashell 无 readline 时走 fgets 回退（源码 #if defined(HAVE_READLINE) 守卫）。
TOOLS = {
    "nfc-anticol": ["examples/nfc-anticol.c", "utils/nfc-utils.c"],
    "nfc-barcode": ["utils/nfc-barcode.c", "utils/nfc-utils.c"],
    "nfc-dep-initiator": ["examples/nfc-dep-initiator.c", "utils/nfc-utils.c"],
    "nfc-dep-target": ["examples/nfc-dep-target.c", "utils/nfc-utils.c"],
    "nfc-emulate-forum-tag2": ["examples/nfc-emulate-forum-tag2.c", "utils/nfc-utils.c"],
    "nfc-emulate-forum-tag4": ["utils/nfc-emulate-forum-tag4.c", "utils/nfc-utils.c"],
    "nfc-emulate-tag": ["examples/nfc-emulate-tag.c", "utils/nfc-utils.c"],
    "nfc-emulate-uid": ["examples/nfc-emulate-uid.c", "utils/nfc-utils.c"],
    "nfc-jewel": ["utils/nfc-jewel.c", "utils/jewel.c", "utils/nfc-utils.c"],
    "nfc-list": ["utils/nfc-list.c", "utils/nfc-utils.c"],
    "nfc-mfclassic": ["utils/nfc-mfclassic.c", "utils/mifare.c", "utils/nfc-utils.c"],
    "nfc-mfsetuid": ["examples/nfc-mfsetuid.c", "utils/nfc-utils.c"],
    "nfc-mfultralight": ["utils/nfc-mfultralight.c", "utils/mifare.c", "utils/nfc-utils.c"],
    "nfc-poll": ["examples/nfc-poll.c", "utils/nfc-utils.c"],
    "nfc-read-forum-tag3": ["utils/nfc-read-forum-tag3.c", "utils/nfc-utils.c"],
    "nfc-relay": ["examples/nfc-relay.c", "utils/nfc-utils.c"],
    "nfc-relay-picc": ["utils/nfc-relay-picc.c", "utils/nfc-utils.c"],
    "nfc-scan-device": ["utils/nfc-scan-device.c", "utils/nfc-utils.c"],
    "pn53x-diagnose": ["examples/pn53x-diagnose.c", "utils/nfc-utils.c"],
    "pn53x-sam": ["examples/pn53x-sam.c", "utils/nfc-utils.c"],
    "pn53x-tamashell": ["examples/pn53x-tamashell.c", "utils/nfc-utils.c"],
}


def _objname(srcfile):
    """examples/nfc-anticol.c -> examples_nfc-anticol（避免重名冲突）."""
    return srcfile[:-2].replace("/", "_")


class LibnfctoolsConan(ConanFile):
    name = "libnfc-tools"
    version = "1.8.0"
    description = "NFC command-line utilities (nfc-list, nfc-mfclassic, pn53x-*) from libnfc 1.8.0"
    license = ("LGPL-3.0-or-later", "GPL-2.0-or-later")
    homepage = "https://github.com/nfc-tools/libnfc"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: 判断必须包含 Linux 与 OHOS 两种取值
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("libnfc-tools is supported only on Linux/OHOS")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def requirements(self):
        # 已发布依赖（W0/R36 核验通过：conan download 均 EXIT=0）
        self.requires("libnfc/1.8.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # AutotoolsToolchain 提供 CC/CFLAGS（R33：编译器从 Conan Toolchain 获取，
        # 不依赖未定义 shell 变量）；AutotoolsDeps 注入依赖的 CPPFLAGS/LDFLAGS/LIBS
        # （-lnfc -lusb -lusb-1.0，静态链接顺序正确）。
        tc = AutotoolsToolchain(self)
        # 与上游 examples/utils 构建一致使用 c99
        tc.extra_cflags.append("-std=c99")
        # 等价于上游 configure.ac 的 AC_DEFINE([_XOPEN_SOURCE], 600)（经 config.h
        # 生效）；不启用 HAVE_CONFIG_H 时需在编译期显式提供，否则 musl/OHOS 头文件
        # 不声明 fdopen（nfc-relay-picc.c 实测报隐式声明错误）
        tc.extra_cflags.append("-D_XOPEN_SOURCE=600")
        tc.generate()
        deps = AutotoolsDeps(self)
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        build_dir = self.build_folder
        obj_dir = os.path.join(build_dir, "obj")

        lines = ["SRCDIR = %s" % src, "O = %s" % obj_dir,
                 "all: %s\n" % " ".join(os.path.join("$(O)", t) for t in TOOLS)]

        # 每个工具一条链接规则（对象文件按声明顺序链接）
        for tool, sources in TOOLS.items():
            objs = ["$(O)/%s.o" % _objname(s) for s in sources]
            lines.append("%s: %s\n\t@mkdir -p $(O)\n\t"
                         "$(CC) $(CFLAGS) %s $(LDFLAGS) $(LIBS) -o $@\n"
                         % (os.path.join("$(O)", tool),
                            " ".join(objs), " ".join(objs)))

        # 每个源文件一条编译规则（跨工具共享的 nfc-utils.c/mifare.c 只编一次）
        written = set()
        for sources in TOOLS.values():
            for s in sources:
                if s in written:
                    continue
                written.add(s)
                lines.append("$(O)/%s.o: $(SRCDIR)/%s\n\t@mkdir -p $(O)\n\t"
                             "$(CC) $(CPPFLAGS) $(CFLAGS) -I$(SRCDIR) -I$(SRCDIR)/libnfc -c $< -o $@\n"
                             % (_objname(s), s))

        save(self, os.path.join(build_dir, "Makefile"), "\n".join(lines))

        # R33 关键：手写 Makefile 时 VirtualBuildEnv 只注入 buildenv
        # （PATH/LD_LIBRARY_PATH/SHELL），不会带入 AutotoolsDeps 生成的
        # CPPFLAGS/LDFLAGS/LIBS（依赖的 -I/-L/-lnfc -lusb -lusb-1.0）。
        # 必须把 Toolchain 与 Deps 两个 environment 显式合并后 apply，
        # 否则链接阶段缺依赖库符号（undefined symbol: nfc_init 等）。
        # 见 knowledge/drafts/DRAFT-E2186-autotools-deps-missing-dep-flags.md。
        env = Environment()
        env.compose_env(AutotoolsToolchain(self).environment())
        env.compose_env(AutotoolsDeps(self).environment)
        with env.vars(self).apply():
            self.run("make -j1 -f Makefile", cwd=build_dir)

    def package(self):
        # 可执行文件与对象文件同在 obj/ 目录，拷贝时排除 *.o
        copy(self, "*", src=os.path.join(self.build_folder, "obj"),
             dst=os.path.join(self.package_folder, "bin"),
             excludes=("*.o",))
        copy(self, "*.1", src=os.path.join(self.source_folder, "utils"),
             dst=os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "*.1", src=os.path.join(self.source_folder, "examples"),
             dst=os.path.join(self.package_folder, "share", "man", "man1"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
