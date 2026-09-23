#!/usr/bin/env python3
"""Conan recipe for ncdc 1.25 (NCurses Direct Connect client) on HarmonyOS PC.

上游为 autotools 应用（发布 tarball 自带 configure/Makefile.in，无需自举）；
无测试套件（Makefile.am 无 TESTS/check 目标）。故层 1 以**真实二进制实跑
自证**：`ncdc --version` 会打印编译期与运行期的 glib / gnutls / sqlite3 版本，
一次性证明这些共享依赖在 OHOS 上可正常加载（含 glib 的 g_libintl_* 重定位）；
`ncdc --help` 证明 ncurses 初始化路径之外的 CLI 正常。test_package 侧另补
消费者断言。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, export_conandata_patches, get
from conan.tools.build import cross_building
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class NcdcConan(ConanFile):
    name = "ncdc"
    version = "1.25"
    description = "NCurses Direct Connect client — a text-mode client for the Direct Connect P2P network"
    license = "MIT"
    homepage = "https://dev.yorhel.nl/ncdc"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("direct-connect", "ncurses", "p2p", "cli")
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"ncdc supports Linux/OHOS only, got {self.settings.os}")
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("ncdc supports OHOS armv8 only")

    def requirements(self):
        self.requires("ncurses/6.6")
        self.requires("zlib/1.3.1.1")
        self.requires("bzip2/1.0.8")
        self.requires("sqlite3/3.49.1")
        # glib/2.84.0.2（R37）已把 proxy-libintl 静态链入 libglib：制品只含
        # libintl.a、无 libintl.so.8，避免 shared glib 图下 musl 解析 libglib
        # 自身 NEEDED 时的 g_libintl_* 重定位失败（旧版 2.84.0.1.x 会踩）。
        self.requires("glib/2.84.0.2")
        self.requires("gnutls/3.8.10")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # ncdc 的依赖发现分两路：
        #  - PKG_CHECK_MODULES：ncursesw / glib-2.0+gthread-2.0 / gnutls
        #  - AC_CHECK_LIB：-lz / -lbz2（+ sqlite3 的 pkg-config 失败后回退）
        # AutotoolsDeps 把全部依赖的 -I/-L/LIBS 注入 CPPFLAGS/LDFLAGS/LIBS，
        # 这正是 AC_CHECK_LIB 与静态 gnutls（gnutls.pc 只给 -lgnutls，静态链
        # 还需 nettle/gmp/libtasn1/libgcrypt/libunistring）能链上的关键。
        PkgConfigDeps(self).generate()
        AutotoolsDeps(self).generate()
        tc = AutotoolsToolchain(self)
        # geoip（libmaxminddb）/ libloc 均为可选且上游默认 no，显式关掉避免
        # 误探测到宿主库（configure.ac 只有 --with-geoip/--with-libloc）。
        tc.configure_args.append("--without-geoip")
        tc.configure_args.append("--without-libloc")
        # 固定使用 AC_INIT 的 1.25，不依赖 git describe。
        tc.configure_args.append("--disable-git-version")
        if str(self.settings.os) == "OHOS":
            # 沙箱内 config.guess 的写盘探针不可靠，显式指定三元组；
            # configure.ac 无 AC_RUN_IFELSE，host=build 不会尝试运行目标二进制。
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-gnu",
            ])
        self._write_glib_pcs()
        tc.generate()

    def _write_glib_pcs(self):
        """补写 glib-2.0.pc / gthread-2.0.pc。

        glib 配方把 pkg_config_name 设成 "glib-2.0-unofficial"（多模块 .pc 的
        产物名），故 PkgConfigDeps 只生成 glib-2.0-unofficial.pc；而 glib 包内
        自带的上游 .pc 的 prefix 是 "/"（meson 以 --prefix=/ 构建），不能直接用。
        ncdc 的 configure.ac 用 PKG_CHECK_MODULES([GLIB],[glib-2.0 gthread-2.0])，
        缺这两个名字会报 "No package 'glib-2.0' found"。
        AutotoolsToolchain 已把 generators 目录 prepend 进 PKG_CONFIG_PATH，
        在此目录写入即可被优先命中。
        """
        glib = self.dependencies.get("glib")
        if not glib or not getattr(glib, "package_folder", None):
            return
        root = glib.package_folder.replace("\\", "/")
        common = (
            "prefix={}\n"
            "libdir=${{prefix}}/lib\n"
            "includedir=${{prefix}}/include/glib-2.0\n"
            "includedir1=${{prefix}}/lib/glib-2.0/include\n"
            "\n"
        ).format(root)
        glib_pc = common + (
            "Name: glib-2.0\n"
            "Description: Conan package: glib-2.0\n"
            "Version: 2.84.0\n"
            "Libs: -L${libdir} -lglib-2.0\n"
            "Cflags: -I${includedir} -I${includedir1}\n"
        )
        gthread_pc = common + (
            "Name: gthread-2.0\n"
            "Description: Conan package: gthread-2.0\n"
            "Version: 2.84.0\n"
            "Requires: glib-2.0\n"
            "Libs: -L${libdir} -lgthread-2.0 -pthread\n"
            "Cflags: -I${includedir} -I${includedir1} -pthread\n"
        )
        for name, text in (("glib-2.0.pc", glib_pc), ("gthread-2.0.pc", gthread_pc)):
            with open(os.path.join(self.generators_folder, name), "w", encoding="utf-8") as f:
                f.write(text)

    def _relax_configure_umask(self):
        """知识库 E011（edit-umask-in-configure）：HMDFS 下 umask 077 建 700 临时目录不可写。

        configure 用 `(umask 077 && mktemp -d ./confXXXXXX)` 在 cwd 建临时目录，
        随后 config.status 往里写 subs*.awk 被拒（CI #44312 实测：
        `./config.status: line 608: ./confMFAcCk/subs1.awk: Permission denied`
        → `config.status: error: could not setup config files machinery`）。
        根因是 HMDFS 的 UID 映射（目录 owner UID 被映射为 20001006，进程实际
        UID 20020083），0700 目录对当前进程不可写；TMPDIR 改不掉它——该目录不
        走 TMPDIR。configure 与它生成的 config.status 共用同一段 here-doc，故把
        configure 里的 `umask 077` 全部放宽为 `umask 022`（E011 推荐方法 2）。
        """
        configure_path = os.path.join(self.source_folder, "configure")
        with open(configure_path, encoding="utf-8") as fh:
            text = fh.read()
        if "umask 077" in text:
            with open(configure_path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(text.replace("umask 077", "umask 022"))

    def _host_libdirs(self):
        """全部 host 依赖的 libdir（去重）。

        conanbuild（VirtualBuildEnv）只覆盖**构建**依赖，不含 host 依赖的
        libdir；musl 解析共享库自身 NEEDED 时也不继承 RUNPATH，故凡在
        build() 内执行会加载 host 依赖 .so 的程序（ncdc 自身、以及下面的
        makeheaders）都必须显式喂 LD_LIBRARY_PATH。
        """
        libdirs = []
        for dep in self.dependencies.host.values():
            pf = getattr(dep, "package_folder", None)
            if not pf:
                continue
            for libdir in dep.cpp_info.aggregated_components().libdirs:
                libdirs.append(libdir if os.path.isabs(libdir) else os.path.join(pf, libdir))
        return list(dict.fromkeys(libdirs))

    def build(self):
        self._relax_configure_umask()
        autotools = Autotools(self)
        autotools.configure()
        # ncdc 的 `make` 会先编译并**运行** deps/makeheaders（生成 mkhdr.done
        # 的 bootstrap 工具，链 gnutls/glib/libgcrypt…）。conanbuild 不含 host
        # 依赖 libdir → makeheaders 启动即 `Error loading shared library
        # libgnutls.so.30: (needed by ./makeheaders)` → `mkhdr.done Error 127`
        # （CI #44320）。故把 host 依赖 libdir 注入 make 进程的 LD_LIBRARY_PATH。
        prefix = 'LD_LIBRARY_PATH="{}:$LD_LIBRARY_PATH" '.format(
            ":".join(self._host_libdirs()))
        self.run(prefix + "make -j1", env="conanbuild")

        # 交叉编译时目标二进制无法在构建 host 上执行，跳过实跑自证。
        if cross_building(self):
            self.output.info("cross-building：跳过二进制实跑自证")
            return

        # 上游无测试套件 → 以真实二进制实跑自证（见模块 docstring）。
        # 顶层 Makefile.am 的 `bin_PROGRAMS=ncdc`（非递归构建）→ 可执行文件落在
        # 构建根目录 $(builddir)/ncdc，而非 src/ 子目录（doc/gendoc 同理由
        # 构建根 `./gendoc` 生成 doc/ncdc.pod）。
        ncdc = os.path.join(self.build_folder, "ncdc")
        self.run(prefix + '"{}" --version'.format(ncdc), env="conanbuild")
        self.run(prefix + '"{}" --help'.format(ncdc), env="conanbuild")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
