#!/usr/bin/env python3
"""Conan recipe for libbfio — libyal Autotools (configure + make), 纯 C 静态库.

平台适配在 build() 内联完成（家族先例 archives/l/libesedb/20240420，无 patches/ 文件）：
- E007: config.guess 识别 HarmonyOS；config.sub 接受 linux-ohos 三元组。
  2017 版 config.sub 与 2024 结构不同（无 android/basic_os 分支），
  锚点按本包源文件定制：maybe_os 列表与 os 合法性列表各一处。
- E011: configure/config.status 的 umask 077 → 022。HMDFS 上 mktemp -d
  建出的 0700 目录连创建者都无法写入（实测 config.status 建目录 Permission denied）。
- E027: --disable-nls。库的 NLS 只影响 message 翻译，关闭后不引入
  gettext/libintl 外部依赖（档案 aide 0.19.3 同口径）。
"""
import os

from conan import ConanFile
from conan.tools.build import build_jobs, cmd_args_to_string
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain


class LibbfioConan(ConanFile):
    name = "libbfio"
    version = "20170123"
    description = "Library for basic file input/output (abstract layer with file, pool and range IO)"
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/libyal/libbfio"
    url = ""
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        # 树内构建（source == build）。2017 版 libyal 内嵌子库（libcthreads 等）
        # 引用兄弟子库的生成头（libcerror_definitions.h）时只认源码树内路径，
        # VPATH/树外构建该头生成在 build 子树、不在 include 路径 → fatal error；
        # 设备原生探索同样复现，树内构建成功（与 makefile 类包同型）。
        self.folders.source = "."
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _toolchain(self):
        # generate() 与 build() 必须使用同一组 configure 参数；两处各自
        # 实例化时遗漏追加项会让 configure 退回默认（shared+static 都建）。
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--enable-static")
        tc.configure_args.append("--disable-shared")
        tc.configure_args.append("--disable-nls")
        return tc

    def generate(self):
        self._toolchain().generate()

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder

        # E007: 让 2017 版 config.guess 识别 HarmonyOS（uname -s = HarmonyOS）。
        # 2015-01-01 版分支用旧式 `echo <三元组>; exit ;;`（无 GUESS 变量，
        # GUESS 风格 2016+ 才引入）；若用 GUESS= 赋值，分支只赋值不出口，
        # esac 后落入无条件失败 dump。家族先例（libesedb 20240420）的
        # config.guess 较新，其 GUESS 写法在本包不可用。
        cg = os.path.join(src, "config.guess")
        if os.path.exists(cg) and "HarmonyOS" not in open(cg).read():
            with open(cg, "r") as f:
                content = f.read()
            insertion = (
                '    *:HarmonyOS:*:*)\n'
                '\tcase "$UNAME_MACHINE" in\n'
                '\t    aarch64|arm64) MACHINE=aarch64 ;;\n'
                '\t    armv7*|armv8*) MACHINE=arm ;;\n'
                '\t    x86_64|amd64)  MACHINE=x86_64 ;;\n'
                '\t    i?86)         MACHINE=i686 ;;\n'
                '\t    *)            MACHINE="$UNAME_MACHINE" ;;\n'
                '\tesac\n'
                '\techo ${MACHINE}-unknown-linux-ohos\n'
                '\texit ;;\n'
                '\n'
            )
            marker = "    *:NetBSD:*:*)"
            content = content.replace(marker, insertion + marker, 1)
            with open(cg, "w") as f:
                f.write(content)
            self.output.info("Patched config.guess for HarmonyOS")

        # E007: 让 2017 版 config.sub 接受 linux-ohos（Conan OHOS 三元组 aarch64-linux-ohos）
        cs = os.path.join(src, "config.sub")
        if os.path.exists(cs) and "linux-ohos" not in open(cs).read():
            with open(cs, "r") as f:
                content = f.read()
            # KERNEL-OS 拆分分支：aarch64-linux-ohos 的 maybe_os 是 linux-ohos
            old = "linux-android* | linux-dietlibc"
            new = "linux-android* | linux-ohos* | linux-dietlibc"
            if old in content:
                content = content.replace(old, new, 1)
            # os 合法性列表
            old = "| -linux-newlib* | -linux-musl* | -linux-uclibc* \\"
            new = "| -linux-newlib* | -linux-musl* | -linux-uclibc* | -linux-ohos* \\"
            if old in content:
                content = content.replace(old, new, 1)
            with open(cs, "w") as f:
                f.write(content)
            self.output.info("Patched config.sub for linux-ohos")

        # E011: umask 077 → 022（HMDFS 0700 临时目录写入受限）
        cf = os.path.join(src, "configure")
        if os.path.exists(cf):
            with open(cf, "r") as f:
                content = f.read()
            if "umask 077" in content:
                content = content.replace("umask 077", "umask 022")
                with open(cf, "w") as f:
                    f.write(content)
                self.output.info("Patched configure umask 077->022")

        # E386（知识 DRAFT-classads-1.0.10 实证方案）：profile [buildenv] 注入的
        # hnp bash 在 HMDFS 上 getcwd 失败（libtool 链接期 pwd 得到
        # /../libcerror/... 类坏路径）；聚合 env 中 profile 优先级最高，
        # tc.environment() 与 configure 命令行参数均无法覆盖，只能用 run
        # 命令的内联前缀就近覆盖。工具链环境（CC/CFLAGS 等）由 conanbuild
        # 脚本先于命令执行提供，内联赋值在其后生效。
        e386_shell = "CONFIG_SHELL=/bin/sh SHELL=/bin/sh"
        tc = self._toolchain()
        self.run('{} "./configure" {}'.format(
            e386_shell, cmd_args_to_string(tc.configure_args)))
        self.run("{} make -j{}".format(e386_shell, build_jobs(self)))

    def package(self):
        # configure 期 CONFIG_SHELL=/bin/sh 已被 config.status 固化进 Makefile，
        # 安装期 libtool 随之走 /bin/sh；DESTDIR 由 Autotools.install 注入。
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["bfio"]
