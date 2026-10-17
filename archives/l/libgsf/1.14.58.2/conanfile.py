#!/usr/bin/env python3
"""Conan recipe — libgsf 1.14.58.2 (autotools, GitLab archive bootstrap).

源码为 GitLab release 归档（不含 configure），build() 内 autoreconf 引导生成。
依赖 glib/libxml2/zlib 均经 conan 提供，PkgConfigDeps 使其 .pc 可供 autotools 使用。
"""
import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class LibgsfConan(ConanFile):
    name = "libgsf"
    version = "1.14.58.2"
    description = "libgsf: structured file library (OLE2 / ZIP / ...) used by AbiWord"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/libgsf"
    url = ""  # CI fills this
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # autoreconf 强制调用 aclocal/automake（AM_INIT_AUTOMAKE 宏），但 CI 沙箱
        # PATH 里没有它们（usr/local/bin 下 770 权限，CI 进程无执行权，报
        # "aclocal: inaccessible or not found"）。用 conan 的 automake/1.18 作为
        # build 工具依赖：其 recipe 的 buildenv_info 已内置 ACLOCAL/AUTOMAKE/
        # PERL5LIB/ACLOCAL_PATH 注入，AutotoolsToolchain 自动聚合进 conanbuild.sh，
        # CI 从 ohpcd 远端拉取（与 ohos-aarch64 profile 匹配的预编译二进制）。
        self.tool_requires("automake/1.18")
        # configure.ac 的 LT_INIT([win32-dll]) 需要 libtoolize + libtool.m4 宏：
        # CI 沙箱同样没有（usr/local/bin 下 770 权限不可执行，hnp 无 libtool）。
        # libtool/2.5.4 的 buildenv_info 已内置 LIBTOOLIZE/ACLOCAL_PATH/
        # _lt_pkgdatadir 注入，避免 autoreconf 报 "possibly undefined macro: LT_INIT"。
        self.tool_requires("libtool/2.5.4")
        self.requires("glib/2.84.0.1")
        self.requires("libxml2/2.15.3.1")
        self.requires("zlib/1.3.1.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()

        tc = AutotoolsToolchain(self)
        # gtk-doc / NLS 在 OHOS 环境不可用（GTK_DOC_CHECK 为 stub，见 patches）
        tc.configure_args.append("--disable-gtk-doc")
        tc.configure_args.append("--disable-nls")
        # CI 沙箱无法运行 clang 编译出的 OHOS 程序（configure 交叉编译探测
        # 报 "cannot run C compiled programs"，Error 77）。显式传 triplet
        # （config.sub 已 patch 支持 *-linux-ohos），configure 不再探测运行。
        # 注意 --build 必须与 --host 不同（或省略 --build）：autoconf 2.72
        # 只在 build_alias != host_alias（或 build 未给）时置 cross_compiling
        # 为 maybe/yes 并跳过 conftest 运行测试；两者相同则保持 no，仍会
        # 尝试运行 → CI 沙箱 EACCES 报 Error 77（abiword-sdw 同款 triplet
        # 之所以能过，是其 minimal configure.ac 无 AC_PROG_CC 运行探测）。
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        tc.generate()

        # OHOS 环境 automake/aclocal 脚本内 @am_AUTOM4TE@ 占位符未替换（E089）：
        # 用环境变量覆盖为真实路径；SED/AUTOCONF/AUTOHEADER 同理。
        env = Environment()
        env.define("AUTOM4TE", "/data/service/hnp/bin/autom4te")
        env.define("SED", "/usr/bin/sed")
        env.define("AUTOCONF", "/data/service/hnp/bin/autoconf")
        env.define("AUTOHEADER", "/data/service/hnp/bin/autoheader")
        # configure.ac 含 AM_GNU_GETTEXT 宏，autoreconf 强制调用 autopoint：
        # /data/service/hnp/bin 仅装了 gettext/msgfmt/xgettext（无 autopoint），
        # CI 沙箱 PATH 也搜不到 autopoint，需显式指向 gettext.org 的 autopoint，
        # 否则 autoreconf 报 "Can't exec autopoint"（FileUtils.pm line 318）而失败。
        env.define("AUTOPOINT", "/data/service/hnp/gettext.org/gettext_0.26/bin/autopoint")
        # gettext_0.26 的 autopoint 编译期硬编码了 Lycium 构建路径
        # （/home/lycium++/lycium/usr/gettext/arm64-v8a/share/gettext），本机无此目录；
        # gettext_datadir 支持环境变量覆盖（: ${gettext_datadir=...}），
        # 指向 gettext.org 实际安装的 archive.dir.tar.xz 所在目录。
        env.define("gettext_datadir", "/data/service/hnp/gettext.org/gettext_0.26/share/gettext")
        tmpdir = os.path.join(self.build_folder, ".tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env.define("TMPDIR", tmpdir)
        # PkgConfigDeps 生成的 .pc 在 generators 目录
        env.append_path("PKG_CONFIG_PATH", self.generators_folder)
        # E107/E142: 全局 LDFLAGS=-L/usr/local/lib 会使链接器优先选中旧静态 glib
        # （缺 g_libintl_*/ffi/pcre2 符号）。覆盖 LDFLAGS：conan 依赖 libdirs 在前。
        deps_ld = []
        for dep in self.dependencies.host.values():
            pkg_folder = dep.package_folder
            if not pkg_folder:
                continue  # 未安装/无包目录的依赖跳过（pkg-config 已提供路径）
            for libdir in dep.cpp_info.libdirs:
                ld = libdir if os.path.isabs(libdir) else os.path.join(pkg_folder, libdir)
                deps_ld.append("-L" + ld)
        env.define("LDFLAGS", " ".join(deps_ld) + " -lintl")
        # autoreconf 会调用 gtkdocize（configure.ac 含 GTK_DOC_CHECK），stub 在源码根
        env.append_path("PATH", self.source_folder)
        env.vars(self).save_script("gsf_build_env")

    def build(self):
        # patch_ng 不创建父目录：0005 补丁新增 m4/ohos-gtkdoc-stub.m4，
        # 必须先确保 m4/ 存在，否则 stub 宏被拍平导致 GTK_DOC_CHECK 未展开
        os.makedirs(os.path.join(self.source_folder, "m4"), exist_ok=True)
        apply_conandata_patches(self)
        # autoreconf --install 会用 tool_requires automake/1.18 自带的上游
        # config.guess/config.sub（无 OHOS 分支）覆盖 patch 0001/0002 的 OHOS
        # 适配版：configure 报 "unable to guess system type"（HarmonyOS 未识别），
        # 且上游版 set_cc_for_build 用 mktemp 建 700 临时目录，沙箱 uid 映射下
        # 写 dummy.c 报 Permission denied。autoreconf 前备份 OHOS 版。
        for _f in ("config.guess", "config.sub"):
            copy(self, pattern=_f, dst=self.build_folder,
                 src=self.source_folder, keep_path=False)
        # 补丁不打可执行位：gtkdocize stub 需 +x 才能被 autoreconf 从 PATH 找到
        self.run("chmod +x gtkdocize", cwd=self.source_folder)
        # GitLab 归档不含 configure：autoreconf 引导生成（需 gtkdocize stub 补丁）
        self.run(
            "autoreconf --force --install",
            cwd=self.source_folder,
            env=["conanbuild", "gsf_build_env"],
        )
        # autoreconf 用 automake/1.18 上游 config.guess/sub 覆盖了 OHOS 版，
        # 恢复备份（configure 从 source 复制 aux 文件到 build，恢复 source 即可）。
        for _f in ("config.guess", "config.sub"):
            copy(self, pattern=_f, dst=self.source_folder,
                 src=self.build_folder, keep_path=False)
        # E129/E167: HMDFS 上 mktemp 临时目录 setgid + 权限问题 →
        # config.status 无法写 confXXXXXX/subs1.awk。修复：把 ac_tmp 固定到
        # 预创建的可写目录，不再依赖 mktemp 动态目录。
        self.run(
            "sed -i 's|ac_tmp=\\$tmp|ac_tmp=./fixed_tmp|g' configure && "
            "mkdir -p fixed_tmp",
            cwd=self.source_folder,
        )
        # config.status 实际在 build folder 中运行（Autotools.configure 的 cwd），
        # 必须在 build folder 也预创建 fixed_tmp，否则 ./fixed_tmp/subs1.awk 报 No such file
        self.run("mkdir -p fixed_tmp", cwd=self.build_folder)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, pattern="COPYING*", dst="licenses", src=self.source_folder)

    def package_info(self):
        self.cpp_info.libs = ["gsf-1"]
        self.cpp_info.includedirs = ["include/libgsf-1"]
        self.cpp_info.set_property("cmake_file_name", "libgsf")
        self.cpp_info.set_property("cmake_target_name", "libgsf::gsf-1")
        self.cpp_info.set_property("pkg_config_name", "libgsf-1")
        # 传递依赖：test_package/下游通过 libgsf::gsf-1 获取 glib/libxml2/zlib 的
        # include 路径（gsf.h 包含 <glib.h>）
        self.cpp_info.requires = [
            "glib::glib-2.0",
            "glib::gobject-2.0",
            "glib::gio-2.0",
            "libxml2::libxml2",
            "zlib::zlib",
        ]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
