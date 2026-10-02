#!/usr/bin/env python3
"""Conan recipe — gift 0.1.9 (GNU Image Finding Tool, autotools)

gift 是 GNU 图像检索工具：C++ 服务端（GIFTServer/gift 守护进程）+ 9 个
libGIFT*/libMRML 共享库 + Perl 客户端脚本。依赖 expat（MRML XML 消息解析）
与 libuuid。内嵌 perl 解释器（-Wl,-E 导出 Perl_* 符号供 libGIFTQuPerl/
libGIFTAcPerl 使用）。

鸿蒙 PC (aarch64-linux-ohos) 适配要点见 patches/ 与 notes.md。
"""
import os
import time

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class GiftConan(ConanFile):
    name = "gift"
    version = "0.1.9"
    description = "GNU Image Finding Tool — open source content based image retrieval system (MRML C++ server, 9 shared libraries, Perl clients)"
    license = "GPL-2.0-or-later"
    homepage = "https://www.gnu.org/software/gift/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "compiler", "build_type", "arch"

    # 上游 2002 年 autotools：libtool 1.4 同时产出 .a/.so（shared+static），
    # 包内容以 shared 库 + 可执行程序为主；无 option（libperl.a 非 PIC 使纯
    # 静态链接不可行），故不声明 package_type/shared option。

    def export_sources(self):
        export_conandata_patches(self)
        # 确定性 config.status CONFIG_FILES 生成脚本（HMDFS 替代方案，见脚本头注释）
        copy(self, "gift-regen-config-files.sh", self.recipe_folder, self.export_sources_folder)

    def requirements(self):
        self.requires("expat/2.8.4")
        self.requires("libuuid/2.42.2")

    def layout(self):
        # 上游 2002 年 configure 硬编码相对路径（如 `perl
        # gift-check-perl-config.pl`），必须做 in-source 构建（src==build）。
        basic_layout(self, src_folder=".", build_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # 上游 configure 不提供 --with-expat/--with-libuuid；
        # include 走 CPPFLAGS 环境变量，lib 走 LDFLAGS（extra_ldflags）。
        expat_cpp = self.dependencies["expat"].cpp_info
        uuid_cpp = self.dependencies["libuuid"].cpp_info
        incs = [f"-I{p}" for p in expat_cpp.includedirs + uuid_cpp.includedirs]
        tc.extra_ldflags.extend(f"-L{p}" for p in expat_cpp.libdirs + uuid_cpp.libdirs)
        env = tc.environment()
        env.append("CPPFLAGS", incs)
        # gift-check-perl-config.pl（补丁后）通过 PATH 中的 perl 取
        # PERL_LD_ADD（-Wl,-E 及 libperl 链接参数）；perl 与 GNU sed 均由
        # profile buildenv PATH 前置提供（/data/service/hnp/bin、~/usr/local/bin）。
        tc.generate(env=env)

    def build(self):
        apply_conandata_patches(self)
        if self.settings.os == "OHOS":
            os.environ["CONFIG_SHELL"] = "/data/service/hnp/bin/bash"
            os.environ["SHELL"] = "/data/service/hnp/bin/bash"
            os.environ.setdefault("TMPDIR", os.path.expanduser("~/tmp"))
            # configure/config.status 生成的 Makefile 依赖 sed 文件交接补丁
            # （0001），该补丁同时把 sed 缓冲上限提到 100000 行；GNU sed 由
            # profile buildenv PATH 前置提供，此处兜底再前置一次。
            sed_path = os.path.expanduser("~/usr/local/bin")
            if os.path.isdir(sed_path):
                os.environ["PATH"] = sed_path + os.pathsep + os.environ.get("PATH", "")

        # ── 防止 maintainer-mode 重建链：0001 补丁使 configure 比 Makefile.in 新，
        # 会触发 `missing --run automake`（perl 脚本 exec 被平台拒绝）。按
        # automake 1.6 的依赖序 touch（旧→新：configure.in < aclocal.m4 <
        # Makefile.in/stamp-h.in/config.h.in < configure）。注意只 touch
        # 已存在的文件（touch 不存在的 configure.ac 会创建空文件，随后
        # autoheader 报 AC_CONFIG_HEADERS not found）。
        self.run("touch configure.in")
        self.run("touch aclocal.m4")
        self.run("find . -name Makefile.in -exec touch {} +")
        self.run("touch stamp-h.in config.h.in")
        self.run("touch configure")
        # HMDFS mtime 回写有延迟，touch 序列间给文件系统落盘时间
        time.sleep(2)

        # ── configure 打补丁（构建时内联，同 4ti2 的 mktemp 内联补丁模式）：
        # config.status 的 CONFIG_FILES 阶段（多进程 sed 管道）在 HMDFS 上
        # 有死锁/写后读损坏/替换值污染（`&` 自引用使 sed 死循环）风险，
        # 故跳过该阶段（CONFIG_FILES= 置空只生成 config.h/gift-config.h），
        # Makefile 由确定性脚本 gift-regen-config-files.sh 代替生成
        # （单进程 sed + 文件交接，Linux CI 上行为等价）。
        _configure = os.path.join(self.source_folder, "configure")
        with open(_configure, "r", encoding="utf-8", errors="ignore") as f:
            _text = f.read()
        _old = "$SHELL $CONFIG_STATUS || ac_cs_success=false"
        _new = "CONFIG_FILES= $SHELL $CONFIG_STATUS || ac_cs_success=false"
        if _old in _text:
            _text = _text.replace(_old, _new)
            with open(_configure, "w", encoding="utf-8") as f:
                f.write(_text)
        else:
            self.output.warn("OHOS config.status bypass: pattern not found in "
                             "configure (upstream text may have changed)")

        # ── HMDFS 信任机制拒绝 exec 由 tarball 解压出的 configure 脚本
        # （Permission denied）；改用 bash 解释执行（config.status 同理，
        # 由 configure 内部 $SHELL 调用）。参数复用 AutotoolsToolchain 生成的
        # conanbuild.conf 中的 configure_args（含 --prefix/--host 等）。
        autotools = Autotools(self)
        self.run(f'bash "{self.source_folder}/configure" '
                 f'{getattr(autotools, "_configure_args", "")}')

        # ── 确定性生成 39 个 Makefile（替代 config.status 的 CONFIG_FILES 阶段）
        self.run("bash gift-regen-config-files.sh")

        # ── HMDFS mtime 粒度/回写乱序：生成的 Makefile 时间戳可能不晚于
        # config.status/Makefile.in，导致 make 反复重跑 automake/config.status
        # 重建链。等待落盘后将 Makefile 统一 touch 为最新，锁死时间戳序
        # （Makefile > config.status > Makefile.in > m4/am）。
        time.sleep(2)
        self.run("find . -name Makefile -exec touch {} +")
        time.sleep(1)

        # R9：HMDFS 下 make -j 会因 jobserver mkfifo 失败，必须串行
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        # 源码根自带 install-sh（AC_PROG_INSTALL 优先选中），其 `#!/bin/sh`
        # shebang exec 被平台信任机制拒绝；显式覆盖为系统核心工具 install。
        autotools.install(args=["INSTALL=/system/bin/install"])

    def package_info(self):
        self.cpp_info.libs = [
            "MRML", "GIFTQuPerl", "GIFTAcPerl", "GIFTQuInvertedFile",
            "GIFTQuHierarchy", "GIFTAcInvertedFile", "GIFTAcHierarchy",
            "GIFTAcDistanceMatrix", "GIFTAcURL2FTS",
        ]
        # libGIFTQuBayesian 为 header-only（无 .lo/.o 产物，不产库）。
        # 头文件嵌套布局（autotools 原样）：include/<lib>/include/*.h，
        # 与上游 #include <CXMLElement.h> 的扁平写法配合，需把每个
        # include/<lib>/include 子目录都加入 include 路径。
        import glob
        nested = sorted(
            os.path.relpath(p, self.package_folder).replace("\\", "/")
            for p in glob.glob(os.path.join(self.package_folder, "include", "*", "include"))
            if os.path.isdir(p)
        )
        self.cpp_info.includedirs = ["include"] + nested
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.system_libs = ["m", "pthread", "dl"]
        # 运行时数据文件：share/gift-config.mrml、gift-ihandshake.mrml、
        # gift-iconfigure.mrml 随包安装；bin/ 下另有 24 个 Perl 客户端脚本。
