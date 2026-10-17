#!/usr/bin/env python3
"""Conan recipe — metar 20190227.1 (Autotools with pre-generated configure, CLI tool).

metar 是航空气象报文（METAR）取数 + 解码命令行工具：从 NOAA 站点抓取报文并解码成
可读字段。唯一外部依赖 libcurl（configure.ac: AC_CHECK_LIB([curl],[curl_easy_init])）。
"""

import json
import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class MetarConan(ConanFile):
    name = "metar"
    version = "20190227.1"
    description = ("Command line METAR decoder: fetches an aviation routine weather "
                   "report from NOAA and decodes station, wind, visibility, "
                   "temperature, dewpoint, pressure and clouds")
    license = "GPL-2.0"
    homepage = "https://metadata.ftp-master.debian.org/changelogs/main/m/metar/metar_20190227.1_changelog"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 唯一必需依赖 = libcurl（configure.ac 里 AC_CHECK_LIB([curl],[curl_easy_init])，
        # 探不到就 AC_MSG_ERROR(Unable to find required library libcurl)）。
        # curl/8.15.0 与制品仓已发布二进制对齐（实测 conan install --build=never 命中
        # package_id df2856b724fa5aed00dc7f60cec6755df39cf2b6）。
        self.requires("curl/8.15.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # 上游 tarball 的 configure 由 autoconf 2.59 + AM_INIT_AUTOMAKE 生成，
        # maintainer 模式默认开启 ⇒ Makefile 里带 `aclocal.m4: configure.ac` /
        # `configure: aclocal.m4` / `config.status: configure` 再生成规则。设备/CI 上
        # 的 autoconf 是 2.72（与 2.59 生成的脚本不同构）、automake 可执行文件的
        # shebang 解释器缺失，一旦触发再生成就变成"用新工具链重造老脚本"，
        # 并把 E011 修好的 umask 段落原样写回去。关掉 maintainer 模式即从根上不走再生成。
        tc.configure_args.append("--disable-maintainer-mode")
        tc.generate()
        # AC_CHECK_LIB 只做链接探测，不会注入 -I/-L（E2186 同族：探测"探绿但编译找不到头"）。
        # AutotoolsDeps 把 curl 的 CPPFLAGS/LDFLAGS 注入环境，configure 的 conftest 与
        # 后续 src/Makefile 的编译命令都从这两个变量取值。
        AutotoolsDeps(self).generate()
        # 第四道墙（本轮实拍，G2 首错）：AutotoolsDeps 除了 -I/-L 还会把 host 依赖的
        # libs 导成环境变量 LIBS=-lcurl，于是 autoconf 最早的那个运行探测
        # 「checking whether the C compiler works」编出来的 a.out 已经动态依赖
        # libcurl.so；OHOS 动态加载器的默认搜索路径不含 conan 缓存包目录，a.out 一执行
        # 就报「Error loading shared library libcurl.so: (needed by ./a.out)」（rc=127），
        # autoconf 把它误写成「cannot run C compiled programs / If you meant to cross
        # compile, use --host」。探针三态实证（日志 ~/tmp/uc2/z75m2/probe.log 的
        # RUN1/RUN2/RUN3）：注入依赖 libdir 前 127、注入后 0、不链共享依赖的对照件
        # 恒 0 ⇒ 与交叉不可执行、exec 位、umask、陈旧 CWD 都无关。
        # 处方按 knowledge/drafts/DRAFT-conan-dep-shared-libs-break-configure-conftest
        # 的 rec（inject-dep-libdirs-ld-library-path）：在 generate() 里把 host 依赖
        # libdirs 前置进 LD_LIBRARY_PATH，落 conanbuild 环境，供 conftest 与 make 使用。
        # 同法先例：archives/a/aaphoto/0.45、archives/d/dirb/2.22。
        # 草稿的另一半 bindirs→PATH 本包不需要（curl-config 在 configure 全文 0 命中，
        # 见 notes.md 第九节）。草稿 forbid 项一并遵守：不用 --host/--build 绕过，
        # 那会让全部检测走假设值。
        env = Environment()
        for dep in self.dependencies.host.values():
            for libdir in dep.cpp_info.libdirs:
                env.prepend_path("LD_LIBRARY_PATH", libdir)
        env.vars(self).save_script("dep_libdirs_runpath")

    def build(self):
        apply_conandata_patches(self)

        # conan 解包后 configure 的执行位可能丢失（同款问题与手法见
        # archives/d/dirb/2.22/conanfile.py：can't execute: Permission denied, Error 126）。
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure_path):
            os.chmod(configure_path, 0o755)

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

        # ── 上游测试门禁：NO_UPSTREAM_TESTS 证据（详见 notes.md 五维账本）──
        # 上游 3 个 Makefile.am（顶层/src/doc）与 configure.ac 全文无 TESTS、无 check:
        # 目标，tarball 无 test/ 目录 ⇒ 上游测试静态总数 = 0。
        # command 用 "none"：CI L1c 会 grep 日志中的 make check/ctest 字样，
        # 避免对"无上游测试"的包误报 upstream tests executed。
        marker = {
            "status": "no_tests",
            "framework": "none",
            "command": "none (no upstream test suite)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False))

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # CLI 工具（metar），无库产物
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
