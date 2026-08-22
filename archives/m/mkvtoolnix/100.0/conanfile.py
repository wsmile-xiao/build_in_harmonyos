#!/usr/bin/env python3
"""Conan recipe for mkvtoolnix 100.0 on HarmonyOS PC.

构建系统：autoconf ./configure（生成 build-config）+ rake 编译 + rake install。
本 recipe 只声明 ohpcd 制品仓已发布的强制依赖；libebml/libmatroska/fmt/pugixml/
nlohmann-json/utf8cpp/librmff 使用源码自带 bundled fallback（README 2.1.2），
configure 找不到系统版本时自动回退，因此不单独 requires（R36：未发布依赖不声明）。

Qt6 (>= 6.2.0) 为强制依赖（ac/qt6.m4 缺失即 AC_MSG_ERROR），即使 --disable-gui。
C++20 为上游硬性要求（README 2.1.1），CI profile 默认 cppstd=17，须覆盖为 20。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class MkvtoolnixConan(ConanFile):
    name = "mkvtoolnix"
    version = "100.0"
    description = "MKVToolNix — Matroska 工具集（mkvmerge/mkvinfo/mkvextract/mkvpropedit）"
    license = "GPL-2.0-only"
    homepage = "https://mkvtoolnix.download/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 已确认发布到 ohpcd 的强制依赖（R35/R36：conan download --only-recipe 验证）
        # libogg/1.3.6：libvorbis/1.3.7 依赖 libogg/1.3.6，版本必须一致（首错修复）
        # gmp：ac/boost.m4 要求 Boost multi-precision GMP 后端（LIBS=-lgmp，缺失 exit 1）
        self.requires("zlib/1.3.1")
        self.requires("libogg/1.3.6")
        self.requires("libvorbis/1.3.7")
        self.requires("gmp/6.3.0.1")
        self.requires("boost/1.84.0")
        self.requires("qtbase/6.11.1", transitive_headers=True, transitive_libs=True)

    def configure(self):
        # mkvtoolnix 100.0 要求 C++20（README 2.1.1）；CI profile 默认 cppstd=17，必须覆盖。
        self.settings.compiler.cppstd = "20"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "mkvtoolnix supports Linux-compatible targets only"
            )

    def layout(self):
        basic_layout(self)
        # mkvtoolnix 是源码内构建（configure 生成 build-config、rake 编译均依赖
        # 源码根目录的 lib/ 相对路径与 bundled 子模块），必须把 build 目录指回源码根，
        # 否则 configure 在 build-release/ 下运行找不到 lib/libebml 等。
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # release tarball 不含 libebml/libmatroska 子模块，且二者未发布 ohpcd；
        # matroska.m4 找不到 pkg-config 版本时回退 internal bundled，需要 vendored 到 lib/。
        # codeload URL 无扩展名，get() 需显式 filename 才能识别 tar.gz 格式。
        get(self, url=self.conan_data["libebml"]["url"],
            sha256=self.conan_data["libebml"]["sha256"],
            filename="libebml-release-1.4.5.tar.gz",
            strip_root=True,
            destination=os.path.join(self.source_folder, "lib", "libebml"))
        get(self, url=self.conan_data["libmatroska"]["url"],
            sha256=self.conan_data["libmatroska"]["sha256"],
            filename="libmatroska-release-1.7.1.tar.gz",
            strip_root=True,
            destination=os.path.join(self.source_folder, "lib", "libmatroska"))

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--prefix=/",
            "--disable-gui",           # 首轮仅构建 CLI 工具，降低 Qt 表面积
            "--disable-update-check",
            "--disable-mkvtoolnix",    # wrapper 二进制非必需
        ])
        # Qt6：configure 通过 --with-qmake6 或 PATH 中的 qmake6 定位（ac/qt6.m4）
        qtbase = self.dependencies["qtbase"]
        qt_bin = os.path.join(qtbase.package_folder, "bin").replace("\\", "/")
        tc.configure_args.append("--with-qmake6={}/qmake6".format(qt_bin))
        # Boost：AX_BOOST_BASE 需显式 --with-boost/--with-boost-libdir 才能设置
        # BOOST_CPPFLAGS/BOOST_LDFLAGS（conan 包路径不在默认搜索范围）；
        # 否则 ax_boost_filesystem 的 $BOOSTLIBDIR/libboost_filesystem* 为空 → "Could not find a version of the library!"。
        boost_dep = self.dependencies["boost"]
        boost_pf = boost_dep.package_folder.replace("\\", "/")
        tc.configure_args.append("--with-boost={}".format(boost_pf))
        tc.configure_args.append("--with-boost-libdir={}/lib".format(boost_pf))
        # 收集依赖 include/lib 路径（AutotoolsToolchain 不自动注入，实测 CPPFLAGS/LDFLAGS 为空）。
        # 注意：lib 路径必须在 tc.environment() 之前写入 extra_ldflags，
        # 因为 environment() 会立即把 self.ldflags 捕获进 LDFLAGS。
        include_flags = []
        lib_flags = []
        for dep_name, dep in self.dependencies.items():
            dep_pf = dep.package_folder
            if not dep_pf:
                continue
            dep_pf = dep_pf.replace("\\", "/")
            include_flags.append("-I{}/include".format(dep_pf))
            lib_flags.append("-L{}/lib".format(dep_pf))
        # qt6.m4 的测试程序 #include <QtCore> / <QCoreApplication>，
        # 仅 -I<qtbase>/include 不够（QtCore 在 include/QtCore/ 子目录），
        # 需额外注入 QtCore 模块 include（最小复现验证：加 -I.../include/QtCore 后编译通过）。
        # 注意：dependencies.items() 的 key 是 Requirement 对象，不能与字符串 == 比较。
        qt_pf = qtbase.package_folder.replace("\\", "/")
        include_flags.append("-I{}/include/QtCore".format(qt_pf))
        tc.extra_ldflags.extend(lib_flags)
        env = tc.environment()
        env.prepend_path("PATH", qt_bin)
        if include_flags:
            env.append("CPPFLAGS", include_flags)
        # 把修改后的 env 显式传给 generate()，避免内部重建丢失注入
        tc.generate(env=env)

    def build(self):
        apply_conandata_patches(self)
        # INSTALL 文档：./configure → rake → rake install
        autotools = Autotools(self)
        autotools.configure()
        # R9 首错诊断用 -j1；常规门禁按任务 parallelism 提速：
        # 通过 tools.build:jobs conf 控制（默认 1 保持保守，命令行 -c:h tools.build:jobs=N 覆盖）。
        jobs = self.conf.get("tools.build:jobs", default=1, check_type=int)
        self.run("rake -j{}".format(jobs), env="conanbuild")

    def package(self):
        # rake installer 支持 DESTDIR（rake.d/helpers.rb: install_dir 使用 c(:DESTDIR)）
        self.run("rake install DESTDIR={}".format(self.package_folder), env="conanbuild")

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
