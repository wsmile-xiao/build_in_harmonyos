import os
import shutil

from conan import ConanFile
from conan.tools.files import (get, replace_in_file,
                               apply_conandata_patches,
                               export_conandata_patches)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class CdebootstrapConan(ConanFile):
    name = "cdebootstrap"
    version = "0.7.9"
    package_type = "application"
    license = "GPL-2.0"
    homepage = "https://salsa.debian.org/installer-team/cdebootstrap"
    description = ("cdebootstrap — compressed debootstrap (Debian installer "
                   "standalone frontend, static binary — C/autotools)")
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # src/Makefile.am: cdebootstrap_LDADD = frontend_@FRONTEND@.a \
        #   @FRONTEND_LIBS@ -ldebian-installer-extra -ldebian-installer
        #   -lbz2 -llzma -lz（standalone frontend 免 libcurl——configure.ac
        #   L42：enable_static=no 时才 PKG_CHECK_MODULES(libcurl)）
        self.requires("libdebian-installer/0.121")
        self.requires("bzip2/1.0.8")
        self.requires("liblzma/5.8.1")
        self.requires("zlib/1.3.2")

    def build_requirements(self):
        # automake：autoreconf 需要 aclocal/automake——系统
        # /storage/Users/currentUser/usr/local/bin 下的是属主 20001006:
        # file_manager 权限 770，CI worker（uid 100）无读/执行权限
        # （'Can't exec "aclocal"' 实测——同 libdi）——用 ohpcd
        # automake/1.18 包（conan 自装、当前用户可读可执行）。
        # cdebootstrap 无 AC_PROG_LIBTOOL（configure.ac 纯 .c → .o 静态
        # 构建，无 .lo/libtool——实测）——不需要 libtool tool_requirement
        self.tool_requires("automake/1.18")

    def layout(self):
        basic_layout(self)

    def source(self):
        # tar 单一顶层目录 cdebootstrap/（实测）——strip_root 去掉
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.host = "aarch64-unknown-linux-ohos"
        # --build 必须显式传：conan automake 的 config.guess（新版）无法识别
        # HarmonyOS（cannot guess build type 实测——同 libdi）
        # --enable-static：静态链接（configure.ac L15-17 加 -static）——
        #   同时 standalone frontend 免 libcurl（L42 仅 enable_static=no 时
        #   才探测 libcurl）
        # --with-dpkg-arch=arm64：OHOS aarch64 对应 dpkg 架构 arm64
        # --with-frontend=standalone：独立前端（免 libcurl/debconfclient）
        tc.configure_args.extend([
            "--build=aarch64-unknown-linux-ohos",
            "--enable-static",
            "--with-dpkg-arch=arm64",
            "--with-frontend=standalone",
        ])
        tc.generate()
        # 依赖 -I/-L 注入（libdi include + 4 依赖 lib 路径）——缺它
        # 'debian-installer.h' file not found 实测
        deps = AutotoolsDeps(self)
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        # configure.ac 的 AC_INIT 用 m4_esyscmd(dpkg-parsechangelog) 取版本
        # （环境无 dpkg——'AC_INIT should be called' 实测——同 libdi）——
        # 硬编码 0.7.9
        replace_in_file(self, os.path.join(self.source_folder, "configure.ac"),
                        "m4_esyscmd(dpkg-parsechangelog | perl -ne "
                        "'print $1 if m/^Version: (.*)$/;')", "0.7.9")
        # 无现成 configure（只有 configure.ac——Debian native 包未预生成）——
        # autoreconf -i 生成；aclocal/automake 用 ohpcd automake/1.18 包
        # （tool_requires——系统 /usr/local/bin 属主 20001006 权限 770，CI
        # worker uid 100 无读/执行权限，'Can't exec "aclocal"' 实测）；
        # autoconf 用 AUTOCONF 环境变量指向有效路径（系统
        # /usr/local/bin/autoconf exit 127 命令找不到实测）；
        # PERL5LIB 指向 automake-1.18 包内 share（含 Automake/Config.pm）
        am_pkg = self.dependencies.build["automake"].package_folder
        self.run(
            "AUTOCONF=/data/service/hnp/autoconf.org/autoconf_2.72/"
            "bin/autoconf PATH=%s/bin:/data/service/hnp/"
            "autoconf.org/autoconf_2.72/bin:$PATH PERL5LIB=%s/share/"
            "automake-1.18 autoreconf -i" % (am_pkg, am_pkg),
            cwd=self.source_folder)
        # config.status 的 mktemp 相对路径 ./confXXXXXX（subs1.awk 写入
        # Permission denied 实测——同 libdi/dpkg）——SKILL 步骤 2：configure
        # 执行前替换 mktemp 模板（configure 尾部自动执行 config.status——
        # 事后改 config.status 的 ac_tmp 已来不及）
        cfg = os.path.join(self.source_folder, "configure")
        if os.path.isfile(cfg):
            src = open(cfg).read()
            if "TMPDIR/confXXXXXX" not in src:
                src = src.replace(
                    'mktemp -d "./confXXXXXX"',
                    'mktemp -d "${TMPDIR}/confXXXXXX"')
                open(cfg, "w").write(src)
        # configure + make（in-source——产物在 source_folder/src/）
        # TMPDIR 指可写目录（沙箱 /tmp 只读 + config.status mktemp 需可写
        # 临时目录——同 libdi）
        os.environ["TMPDIR"] = "/data/storage/el2/base/cache"
        tc = Autotools(self)
        tc.configure()
        tc.make(args=["-j4"])

    def package(self):
        # 静态二进制 → bin/。Autotools helper 的 configure/make 在
        # build_folder（basic_layout 下 = build-release，out-of-source）运行，
        # 产物在 build_folder/src/cdebootstrap（实测——source_folder/src/
        # 下无产物，conan create package() FileNotFoundError 实测）
        # ——shutil 显式拷贝最可靠（同 libdi）
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        shutil.copy(os.path.join(self.build_folder, "src", "cdebootstrap"),
                    bin_dir)
        # config data → share/cdebootstrap/（suites 文件 + generic/{action,
        # packages,sections} 子目录）。这些是源数据文件，out-of-source 构建里
        # 留在 source 树（build 树 config/ 只有生成的 Makefile——实测核实），
        # 从 source_folder 取。helper/*.deb（dpkg-deb 打包脚本，OHOS 无
        # dpkg-deb——make install 在 helper 段失败实测）不打包
        cfg_dst = os.path.join(self.package_folder, "share", "cdebootstrap")
        os.makedirs(cfg_dst, exist_ok=True)
        shutil.copy(os.path.join(self.source_folder, "config", "suites"),
                    cfg_dst)
        shutil.copytree(os.path.join(self.source_folder, "config", "generic"),
                        os.path.join(cfg_dst, "generic"), dirs_exist_ok=True)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
