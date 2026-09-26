#!/usr/bin/env python3
"""Conan recipe — jimtcl 0.83 (The Jim Interpreter, small-footprint Tcl).

构建链：autosetup 风格 `./configure`（仓库自带预生成 configure，无需 autoreconf）+ make。
OHOS 适配要点（详见同目录 notes.md 与两份补丁）：
  1. 上游自带的 autosetup-config.{guess,sub}（2021-06-03）不认识 HarmonyOS/ohos
     ⇒ 注入 HarmonyOS 分支与 ohos 接受分支（patches/0001、0002），默认无参
     `./configure` 即可通过。
  2. 设备无 cc/gcc，autosetup 自举 jimsh0 需要 CC_FOR_BUILD（profile 的
     tools.build:compiler_executables）。
  3. 层1上游测试（`make check` = tests/*.test 的 tcltest 套件）在 build() 内执行；
     21 项 OHOS 环境类非 PASS 按 TEST_QUALITY_SPEC §3.3 声明豁免
     （test_package/MANIFEST.yml 的 upstream_test_run + reports/test-report.md），
     真实通过率不改写。
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class JimtclConan(ConanFile):
    name = "jimtcl"
    version = "0.83"
    description = "Jim Tcl - a small footprint implementation of the Tcl programming language"
    license = "MIT"
    homepage = "https://jim.tcl-lang.org/"
    url = ""  # CI fills this

    # 只发行静态库 + jimsh（不声明 shared 选项：conan 对 package_type="library"
    # 强制要求 shared 选项，而本包不提供共享变体，故用 static_library 如实声明；
    # 上游默认即静态，`--shared` 变体本包不发行）。
    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        # jim-zlib 扩展链系统 zlib（jimtcl.pc 的 Libs.private: -lz）；conan zlib 静态
        # -fPIC 内链（R26），不引入运行期 libz.so。
        self.requires("zlib/1.3.1.1")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # static_library 会让 AutotoolsToolchain 注入 autotools 风格的
        # --enable-static/--disable-shared（autosetup 实测报 "Unknown option --static"），
        # 默认安装目录参数里 --oldincludedir/--datarootdir 也不在 autosetup 的
        # 兼容选项表（autosetup/system.tcl 只认 bindir/sbindir/includedir/libdir 等，
        # 实测 "Error: Unknown option --oldincludedir"）。
        # 本包固定静态发行、上游默认即静态 ⇒ 这些注入参数必须剔除。
        _autosetup_reject = ("--enable-static", "--disable-shared",
                             "--oldincludedir", "--datarootdir")
        tc.configure_args = [a for a in tc.configure_args
                             if not a.startswith(_autosetup_reject)]
        # autosetup 自举 jimsh0（autosetup/autosetup-find-tclsh）读 CC_FOR_BUILD，
        # 设备无 cc/gcc/c89/c99 ⇒ 必须显式给出，否则 configure 直接失败：
        #   "No working C compiler found. Tried cc and gcc."
        env = tc.environment()
        compilers = self.conf.get("tools.build:compiler_executables", default={},
                                  check_type=dict) or {}
        cc = compilers.get("c")
        if cc:
            env.define("CC_FOR_BUILD", cc)
        tc.generate(env=env)

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()
        # ── 层1：上游官方测试套件（tests/*.test，tcltest；`make check` 是 `make test` 的别名）──
        # 本包是 out-of-source 构建（conan 复制源码到 build-release，Makefile 生成在那里），
        # 必须在 build_folder 跑；失败不阻断构建：21 项为 OHOS 环境类失败（musl 无 ualarm、
        # 无 tty、HMDFS 禁硬链接、/tmp 只读、无 id、SELinux 禁 AF_UNIX bind、信号语义差异），
        # 逐条豁免与取数见 test_package/MANIFEST.yml 与 reports/test-report.md；真实统计不改写。
        self.run("make -j1 check", cwd=self.build_folder, ignore_errors=True)

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["jim"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        # musl 数学库（expr 的 pow/floor 等）
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.set_property("pkg_config_name", "jimtcl")
        self.cpp_info.set_property("cmake_file_name", "jimtcl")
        self.cpp_info.set_property("cmake_target_name", "jimtcl::jimtcl")
