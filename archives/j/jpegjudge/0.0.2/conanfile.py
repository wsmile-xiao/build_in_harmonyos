#!/usr/bin/env python3
"""Conan recipe — jpegjudge 0.0.2（命令行工具，上游可执行文件名 judge）。

jpegjudge 读取 JPEG 文件、按解码后的块内 DCT 活跃程度给出 0~1000 的质量
指示值，用于按编码参数判重/比较（上游主页 https://oldhome.schmorp.de/marc/judge.html）。

构建系统判定（实测，非台账转述）：
  随包 `configure` 头部写着 "Generated automatically using autoconf version 2.13"，
  输入文件叫 `configure.in`（不是 configure.ac），另有 acconfig.h / config.h.bot /
  stamp-h.in 这一套 2.13 专属机制；`Makefile.in` 由 automake 1.4 生成
  （`$(srcdir)/Makefile.in: Makefile.am configure.in` 会回调 $(AUTOMAKE)）。
  包内既无 autogen.sh 也无 config.guess/config.sub。
  ⇒ 不使用 autoreconf 重新生成（新版 autoconf 不再识别 configure.in/acconfig.h
    组合，重生成会覆盖随包产物并打断 config.h 的 @...@ 占位流程），
    直接使用随包 configure + Makefile.in。

依赖：libjpeg —— 实测该归档的 jpeglib.h 仍保留 trace_level 字段，
judge.c 的 `cinfo.err->trace_level = 0;` 无需为新版 jpeglib 改动。
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (apply_conandata_patches, export_conandata_patches,
                               get)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class JpegjudgeConan(ConanFile):
    name = "jpegjudge"
    version = "0.0.2"
    description = ("Guess the JPEG coding quality indicator (0-1000) of picture "
                   "files, for comparing JPEGs by encoding parameters")
    license = "IJG"
    homepage = "https://oldhome.schmorp.de/marc/judge.html"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # W0 已实测制品可取（两条口径均 rc=0，见 archives/j/jpegjudge/0.0.2/notes.md）：
        #   conan download libjpeg/10 --only-recipe（remote 由 CI 环境注入，实测口径见 notes.md）
        #   conan install --requires=libjpeg/10 --build=never
        # 引用形态与归档一致：不带 user/channel（同 archives/j/jpeginfo/1.7.1）。
        self.requires("libjpeg/10")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "jpegjudge is only supported on Linux/OHOS, not "
                f"{self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        deps = AutotoolsDeps(self)
        deps.generate()
        tc = AutotoolsToolchain(self)
        # 随包 configure 只接受 autoconf 2.13 的选项面（`../configure --help` 实测清单：
        # --prefix/--exec-prefix/--{bindir,sbindir,libexecdir,datadir,sysconfdir,
        # sharedstatedir,localstatedir,libdir,includedir,oldincludedir,infodir,mandir}
        # /--program-*/--{build,host,target}/--x-*），conan 默认注入的 --datarootdir
        # 会命中 configure:379 的 "invalid option ... exit 1" 分支。
        # ⇒ 参数最少化（R1）：只给 --prefix，其余目录沿用 2.13 默认值，
        #   package() 以 make install DESTDIR=<package_folder> 落盘。
        tc.configure_args = ["--prefix=/"]
        tc.generate()
        # libjpeg/10 在本仓为静态制品（libjpeg.a），此段只是共享形态兜底，
        # 保证未来依赖换成 .so 时 judge 运行期仍可解析。
        env = Environment()
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                env.prepend_path("LD_LIBRARY_PATH", libdir)
        env.vars(self, scope="build").save_script("conanbuild_runpath")

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # R51 上游测试三步之二：真实执行上游唯一存在的测试入口。
        # 实测 Makefile.in:323-324 为 `check-am: all-am` / `check: check-am`，
        # 无 TESTS / check_PROGRAMS 注册 ⇒ 本步退出码 0、执行 0 个用例
        # （上游确无自动化测试，清点证据见 notes.md 与 reports/）。
        autotools.make(target="check", args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # 纯命令行工具，不导出库；bindirs 非空 ⇒ R38/L0k 要求软件级 commands.json
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
