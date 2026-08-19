#!/usr/bin/env python3
"""Conan recipe — lttoolbox 3.7.6 (Apertium letter transducer toolbox).

lttoolbox is the core finite-state transducer library used by the Apertium
machine translation platform. It provides dictionary compilation (lt-comp),
lexical-string processing (lt-proc), and transducer inspection (lt-print)
tools built atop libxml2, ICU, and utfcpp.

Build system: autotools (configure.ac + Makefile.am + autogen.sh).
The release tarball ships NO pre-generated `configure` script — we must
run `autoreconf -fi` (via autogen.sh) to generate it before invoking
configure/make.

Dependencies (per configure.ac):
  - libxml-2.0 >= 2.6.17  (Conan: libxml2)
  - icu-i18n, icu-io, icu-uc  (Conan: icu4c)
  - utf8cpp/utf8.h  (Conan: utf8cpp)
  - pthread  (system)

R26: System-level library, build static only to avoid polluting /lib.
R32: Supports both Linux and OHOS platforms.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LttoolboxConan(ConanFile):
    name = "lttoolbox"
    version = "3.7.6"
    description = "Apertium letter transducer toolbox — finite-state transducer library"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/apertium/lttoolbox"
    url = ""  # CI fills this
    topics = ("apertium", "transducer", "finite-state", "nlp", "dictionary",
              "machine-translation")
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)
        # patches/autotools/ contains pre-generated autoreconf products
        # (configure, aclocal.m4, Makefile.in, m4/*.m4, ltmain.sh,
        # config.guess/sub, INSTALL, compile, depcomp, install-sh, missing).
        # The CI Worker has no aclocal (automake not installed), so build()
        # copies these into the source folder instead of invoking autoreconf.
        # export_conandata_patches only copies patches listed in conandata.yml
        # patches:; autotools/ is a vendored build input not a patch, so we
        # copy it ourselves here (same pattern address-standardizer uses for
        # pg_mem_stubs.c). At build time export_sources_folder becomes
        # self.source_folder, so build() resolves them via
        # self.source_folder/patches/autotools/.
        autotools_src = os.path.join(self.recipe_folder, "patches", "autotools")
        if os.path.isdir(autotools_src):
            autotools_dst = os.path.join(self.export_sources_folder,
                                         "patches", "autotools")
            for root, _, files in os.walk(autotools_src):
                rel = os.path.relpath(root, autotools_src)
                dst = os.path.join(autotools_dst, rel) if rel != "." else autotools_dst
                os.makedirs(dst, exist_ok=True)
                for f in files:
                    copy(self, f, root, dst)

    def requirements(self):
        self.requires("libxml2/2.15.3.1", transitive_headers=True)
        # lttoolbox's public headers (ustring.h) include ICU and utfcpp headers,
        # so these must be transitive for downstream consumers.
        self.requires("icu4c/77", transitive_headers=True)
        self.requires("boost/1.91.0")
        self.requires("utf8cpp/4.1.1", transitive_headers=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Copy pre-generated autotools files (configure, aclocal.m4,
        # Makefile.in, m4/*.m4, ltmain.sh, config.guess/sub, INSTALL,
        # compile, depcomp, install-sh, missing) into the freshly-extracted
        # source tree RIGHT HERE in source() — before Conan caches the source
        # folder. Doing this in build() failed because Conan's source folder
        # management overwrote the top-level configure back to a stale
        # 21936-line cache residue (with raw PKG_CHECK_MODULES macros not
        # expanded) between configure() and make(), causing syntax errors.
        # source() runs once right after get() extracts the tarball; copying
        # here bakes the correct 22272-line expanded configure into the
        # cached source so build() sees it without any Conan mechanism able
        # to overwrite it back.
        # export_sources() 已把 patches/autotools 复制到 export_sources_folder
        # （recipe_folder 在导出后不含该目录），故优先从 export_sources_folder
        # 读取，fallback 到 recipe_folder（本地源码目录场景）。
        autotools_src = os.path.join(self.export_sources_folder, "patches", "autotools")
        if not os.path.isdir(autotools_src):
            autotools_src = os.path.join(self.recipe_folder, "patches", "autotools")
        if os.path.isdir(autotools_src):
            import shutil
            for root, _, files in os.walk(autotools_src):
                rel = os.path.relpath(root, autotools_src)
                dest = os.path.join(self.source_folder, rel) if rel != "." else self.source_folder
                os.makedirs(dest, exist_ok=True)
                for f in files:
                    shutil.copy2(os.path.join(root, f), os.path.join(dest, f))
            self.output.info("Copied pre-generated autotools files from patches/autotools/ in source()")

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: System-level library — static only to avoid polluting /lib
        tc.configure_args.append("--enable-static")
        tc.configure_args.append("--disable-shared")

        # Propagate dependency include/lib paths to configure via env vars.
        # autotools PKG_CHECK_MODULES uses pkg-config; we inject the Conan
        # dependency paths directly into CPPFLAGS/LDFLAGS so configure can
        # find the headers and libraries without relying on system pkg-config.
        cppflags = []
        ldflags = []

        # Also set PKG_CONFIG_PATH so configure's PKG_CHECK_MODULES can find
        # the .pc files installed by Conan dependencies (libxml2, icu4c).
        pkgconfig_dirs = []

        for _ref, dep in self.dependencies.items():
            for inc in dep.cpp_info.includedirs:
                cppflags.append("-I{}".format(inc))
                # Also add subdirectories (e.g. utf8cpp/ for utf8.h includes).
                # CRITICAL: skip ICU's unicode/ subdir — its utf8.h conflicts
                # with utfcpp's utf8.h (ICU defines UTF8_* macros, not the
                # utf8 namespace that lttoolbox needs).
                if os.path.isdir(inc):
                    for sub in os.listdir(inc):
                        subdir = os.path.join(inc, sub)
                        if (sub != "unicode" and os.path.isdir(subdir)
                                and os.path.isfile(os.path.join(subdir, "utf8.h"))):
                            cppflags.append("-I{}".format(subdir))
            for lib in dep.cpp_info.libdirs:
                ldflags.append("-L{}".format(lib))
                # Check for pkgconfig subdirectory
                pc_dir = os.path.join(lib, "pkgconfig")
                if os.path.isdir(pc_dir):
                    pkgconfig_dirs.append(pc_dir)

        if cppflags:
            # Inject as env vars (not configure argv) so configure's AC_CHECK_HEADER
            # probes find utf8cpp/utf8.h via CPPFLAGS. Setting via tc.configure_args
            # passed CPPFLAGS=... as a configure argv which configure ignores.
            os.environ["CPPFLAGS"] = (
                " ".join(cppflags) + " " + os.environ.get("CPPFLAGS", "")
            )
        if ldflags:
            os.environ["LDFLAGS"] = (
                " ".join(ldflags) + " " + os.environ.get("LDFLAGS", "")
            )

        # Set PKG_CONFIG_PATH so configure's PKG_CHECK_MODULES finds .pc files
        if pkgconfig_dirs:
            os.environ["PKG_CONFIG_PATH"] = (
                ":".join(pkgconfig_dirs) + ":" + os.environ.get("PKG_CONFIG_PATH", "")
            )

        # Let configure find the icu/utfcpp headers
        tc.defines.append("HAVE_UTF8CPP")

        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # The upstream release tarball ships NO pre-generated configure script
        # (only configure.ac + Makefile.am). autoreconf -fi would generate it,
        # but the CI Worker has no aclocal (automake not installed, only
        # autoconf 2.72 at /data/service/hnp/autoconf.org/autoconf_2.72/).
        # Pre-generated autotools files (configure, aclocal.m4, Makefile.in,
        # m4/*.m4, ltmain.sh, config.guess/sub, INSTALL, compile, depcomp,
        # install-sh, missing) are copied in source() right after get()
        # extracts the tarball, baking the correct 22272-line expanded
        # configure (PKG_CHECK_MODULES macros expanded) into the cached source
        # so build() sees it without Conan mechanism able to overwrite it back.
        # Fallback for local builds with automake installed: run autoreconf.
        if not os.path.isfile(os.path.join(self.source_folder, "configure")):
            for candidate in [
                "/data/service/hnp/pkg-config.org/pkg-config_0.29.2/share/aclocal",
                "/usr/share/aclocal",
                "/usr/local/share/aclocal",
            ]:
                if os.path.isfile(os.path.join(candidate, "pkg.m4")):
                    existing = os.environ.get("ACLOCAL_PATH", "")
                    os.environ["ACLOCAL_PATH"] = (
                        candidate + (":" + existing if existing else "")
                    )
                    break
            self.run("autoreconf -fi", cwd=self.source_folder)

        # E011: autotools-generated configure/Makefile.in use umask 077 for
        # temporary directories, which causes Permission denied on HMDFS.
        # Patch umask 077 → umask 022 in the generated files (same fix as
        # libiconv E011). The pre-generated configure already uses umask 022.
        for fname in ["configure", "Makefile.in", "lttoolbox/Makefile.in"]:
            fpath = os.path.join(self.source_folder, fname)
            if os.path.isfile(fpath):
                with open(fpath, "r") as f:
                    content = f.read()
                    if "umask 077" in content:
                        replace_in_file(self, fpath, "umask 077", "umask 022")

        # CI #27655/#27669: make -j1 触发 Makefile:424 的 aclocal.m4 重建
        # 规则（m4/*.m4 或 configure.ac 时间戳比 aclocal.m4 新），调用
        # `missing aclocal-1.16` → "aclocal-1.16: command not found" → Error 127。
        # CI worker 没装 automake，预生成的 aclocal.m4 已含全部展开的宏。
        # touch 在 configure 之前无效（config.status 会重新 touch 部分文件）。
        # 根治：把 ACLOCAL 环境变量设为 `:`（no-op），即使 make 触发重建
        # 规则，$(ACLOCAL) 也是 `:`，不会调用 missing aclocal-1.16。
        os.environ["ACLOCAL"] = ":"
        os.environ["AUTOMAKE"] = ":"
        os.environ["AUTOCONF"] = ":"
        os.environ["AUTOHEADER"] = ":"
        os.environ["AUTOM4TE"] = ":"

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["lttoolbox"]
        self.cpp_info.bindirs = ["bin"]
        # The upstream installs liblttoolbox.la → lib/liblttoolbox.so/.a
        # On OHOS static build, the .a archive is the primary artifact.
        self.cpp_info.set_property("cmake_target_name", "lttoolbox::lttoolbox")
        self.cpp_info.set_property("pkg_config_name", "lttoolbox")
        # System libs linked by lttoolbox
        self.cpp_info.system_libs = ["pthread"]
