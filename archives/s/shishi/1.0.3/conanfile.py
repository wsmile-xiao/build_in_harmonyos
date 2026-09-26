#!/usr/bin/env python3
"""Conan recipe for GNU Shishi 1.0.3 — Kerberos 5 implementation.

Builds libshishi (client/library side), libshisa (Shisa database layer) and
the command line tools (shishi, shisa, shishid, keytab2shishi,
ccache2shishi) from the official release tarball.  The release tarball is
mandatory: the command line parsers (src/*_cmd.c/_cmd.h) are gengetopt
output that only ships in the release tarball, and neither the device nor
the CI worker provides gengetopt (see notes.md).
"""

import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class ShishiConan(ConanFile):
    name = "shishi"
    version = "1.0.3"
    description = "GNU Shishi - Kerberos 5 implementation (KDC and client libraries)"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/shishi/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def validate(self):
        # R32: settings.os 判断必须 in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("shishi is supported only on Linux/OHOS")

    def requirements(self):
        # configure.ac 硬闸：libgcrypt（AC_MSG_ERROR）与 libtasn1（AC_MSG_ERROR）
        # libidn/gnutls/PAM 为可选依赖，OHOS 上以 configure 开关关闭（见 generate）
        self.requires("libgcrypt/1.12.2")
        self.requires("libtasn1/4.21.0")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            # 无 gtk-doc 工具；NLS 需要 msgfmt（设备仅 harmonybrew 有，CI worker 无——
            # 按设备事实 §一.4 禁止依赖 harmonybrew PATH）；libidn 未发布到 ohpcd，
            # gnutls STARTTLS 与 PAM 为可选能力，OHOS 上关闭并留痕 notes.md。
            "--disable-gtk-doc",
            "--disable-nls",
            "--without-stringprep",
            "--disable-starttls",
            "--disable-pam",
        ])
        # 上游 AM_PATH_LIBGCRYPT 变体只认 libgcrypt-config、没有 pkg-config 回退；
        # 指到 conan 包前缀即可命中其 bin/libgcrypt-config（版本探测 1.12.2 ≥ 1.4.4）。
        # 其输出的 -I//include、-L//lib 是构建期陈旧前缀，靠下方 extra_cflags/ldflags 兜底。
        tc.configure_args.append(
            "--with-libgcrypt-prefix={}".format(
                self.dependencies["libgcrypt"].package_folder
            )
        )
        if str(self.settings.os) == "OHOS":
            # uname -s = HarmonyOS，上游 2022-05-25 的 config.guess 不识别；
            # 显式等值 build/host 让 configure 跳过 config.guess 探测。设备实测
            # `checking whether we are cross compiling... no`，gnulib 运行期检查
            # （working mktime 等）照常执行，非交叉编译。
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-gnu",
            ])
        # conan 的 AutotoolsToolchain 不注入依赖 include/lib 路径，按 cpp_info 显式补
        for _, dep in self.dependencies.items():
            pf = dep.package_folder
            for inc in dep.cpp_info.includedirs:
                path = inc if os.path.isabs(inc) else os.path.join(pf, inc)
                flag = "-I{}".format(path)
                if flag not in tc.extra_cflags:
                    tc.extra_cflags.append(flag)
            for libdir in dep.cpp_info.libdirs:
                path = libdir if os.path.isabs(libdir) else os.path.join(pf, libdir)
                flag = "-L{}".format(path)
                if flag not in tc.extra_ldflags:
                    tc.extra_ldflags.append(flag)
        tc.generate()

    def _align_info_timestamps(self):
        """Keep the shipped info manual newer than the doc timestamp chain.

        doc/Makefile has `stamp-vti: shishi.texi $(top_srcdir)/configure` →
        `version.texi` → `shishi.info`.  Applying our configure patch makes
        configure newer than the shipped stamp-vti, so make regenerates
        version.texi and then wants to rebuild shishi.info with makeinfo —
        which exists neither on the device nor on the CI worker (texinfo is
        not published to ohpcd either), failing both `make check` and
        `make install`.  Only mtimes are touched here (file content is
        untouched, so patches/diffs are unaffected) to mark the shipped
        generated manual as up to date.
        """
        doc = os.path.join(self.source_folder, "doc")
        for name in ("stamp-vti", "version.texi", "shishi.info",
                     "shishi.info-1", "shishi.info-2", "shishi.info-3"):
            path = os.path.join(doc, name)
            if os.path.exists(path):
                os.utime(path, None)

    def _ensure_run_libs(self):
        """Make dependency shared libraries resolvable while building.

        The upstream test executables and the install-data-hook (it runs
        ``shisa -a``) execute shared binaries during build()/package(), but
        conan create's build process has no conanrun environment.  libtool
        only records an rpath for dependencies that ship a ``.la`` file, and
        the libgcrypt package ships only ``.so`` files, so the loader cannot
        find ``libgcrypt.so.20`` and every test fails with exit 127 (first
        G2 round: TOTAL 16 / PASS 0 / FAIL 16, every .log line
        "Error loading shared library libgcrypt.so.20").  Precedent:
        srecord/1.65.0 ``_ensure_run_libs`` (E019) — prepend the
        dependencies' libdirs to LD_LIBRARY_PATH for this process and its
        children instead of embedding machine-specific rpaths.
        """
        dirs = []
        for _, dep in self.dependencies.items():
            for libdir in dep.cpp_info.libdirs:
                path = libdir if os.path.isabs(libdir) else os.path.join(
                    dep.package_folder, libdir)
                if path not in dirs and os.path.isdir(path):
                    dirs.append(path)
        if not dirs:
            raise ConanInvalidConfiguration(
                "no dependency libdirs found for runtime library path")
        existing = os.environ.get("LD_LIBRARY_PATH", "")
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
            dirs + ([existing] if existing else []))
        self.output.info(
            "LD_LIBRARY_PATH={}".format(os.environ["LD_LIBRARY_PATH"]))

    def build(self):
        self._ensure_run_libs()
        apply_conandata_patches(self)
        self._align_info_timestamps()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j2"])
        # 上游回归套件（tests/ 的 16 个 automake TESTS 用例）纳入构建契约，
        # 使 conan create（G2/W3/CI）每次都真实运行上游测试。
        autotools.make(target="check", args=["-j2"])

    def package(self):
        self._ensure_run_libs()  # install-data-hook executes bin/shisa
        autotools = Autotools(self)
        autotools.install()
        # libtool *.la 包装器不进包（仓库惯例）
        for _la in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(_la)
        # 上游 install-data-hook 用 shisa -a 建库+host key，但 shisa 运行期读的
        # 是编译进去的宿主绝对路径（conan 以 prefix=/ + DESTDIR 布局安装，
        # DESTDIR 只搬文件不改编译期字符串），必然失败并留下 0 字节 shishi.keys
        # （见 notes.md 问题表第 8 行）。清掉该空壳，建库属部署动作。
        _keys = os.path.join(self.package_folder, "etc", "shishi", "shishi.keys")
        if os.path.exists(_keys) and os.path.getsize(_keys) == 0:
            os.remove(_keys)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "shishi")
        self.cpp_info.set_property("pkg_config_name", "shishi")
        # libshisa 依赖 libshishi，静态链接顺序在前
        self.cpp_info.libs = ["shisa", "shishi"]
        self.cpp_info.system_libs = ["m"]
        # conan 的 AutotoolsToolchain 把 --sbindir 也映射到 bindirs[0]，
        # 5 个工具（含 shishid/keytab2shishi）实测全部落在 bin/（包内实核）
        self.cpp_info.bindirs = ["bin"]
