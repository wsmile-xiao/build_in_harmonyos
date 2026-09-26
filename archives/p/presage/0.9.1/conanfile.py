#!/usr/bin/env python3
"""Conan recipe for presage 0.9.1 — intelligent predictive text entry platform.

Upstream:  https://presage.sourceforge.net/
Git:       https://git.code.sf.net/p/presage/presage (tag 0.9.1)
License:   GPL-2.0-or-later (COPYING = GPL v2 or later)
Build:     Autotools (tarball ships pre-generated configure/Makefile.in, no autoreconf)

Adaptation notes (details in notes.md):
- patches/0001 config.guess (2012) does not recognize `uname -s` = HarmonyOS
  -> merge aarch64:HarmonyOS into the aarch64:Linux branch.
- patches/0002 config.status creates its temp dir via
  `(umask 077 && mktemp -d ./confXXXXXX)`; on HMDFS the resulting 0700 dir is
  uid-mapped and unwritable for the current process (knowledge E011 family).
  Disable the mktemp branch (mkdir fallback, group-writable) + relax umask to
  002.
- patches/0003 ProfileManager::get_user_home_dir() has an inverted
  `if (!my_passwd)` guard: getpwuid() returns NULL on OHOS (no passwd db) and
  the branch dereferences my_passwd->pw_dir -> SIGSEGV in every
  ProfileManager construction (upstream logic bug, hidden on hosts where
  getpwuid() succeeds).
- generate() builds two shims:
  * cppunit-config: AM_PATH_CPPUNIT (m4/cppunit.m4) only understands a
    `cppunit-config` executable; the Conan cppunit package ships none, so
    without the shim HAVE_CPPUNIT is empty, the testRunner binaries are not
    built and all 94 upstream CPPUNIT_TEST registrations are silently
    skipped while `make check` still reports success (false green).
  * libcurses.a -> libncursesw.a: upstream AC_CHECK_LIB([curses]) links
    -lcurses; Conan ncurses only ships *w library names, without the shim
    presage_demo (ncurses demo tool) is silently dropped by upstream's
    optional branch.
"""
import os

from conan import ConanFile
from conan.tools.files import (
    get,
    apply_conandata_patches,
    export_conandata_patches,
    save,
    copy,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class PresageConan(ConanFile):
    name = "presage"
    version = "0.9.1"
    description = "Presage, an extensible predictive text entry system"
    license = "GPL-2.0-or-later"
    homepage = "https://presage.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    # shared 面 = 原生对齐（编排方定案）：上游 libtool 默认同时产出
    # libpresage.so.1.1.1 + libpresage.a（原生构建/安装树实证两者俱在，演示程序
    # 链 .so 走 NEEDED 运行期解 C++ 符号）。此前沿用模板默认 shared=False 触发
    # --disable-shared/--enable-static → 纯 .a（libtool .la dlname='' 实证）→
    # bindings/c 的 presage_c_demo 由 CC 驱动静态链 .a，libc++ 符号全部顶到
    # 链接期（__cxa_rethrow/std::terminate undefined）。翻转为 True 后 configure
    # 不再注入任何 shared 开关 = 与原生 configure 完全同形（双产物）。
    # 注：显式 -o shared=False 的非默认变体仍会走到静态-only，需要时按 notes #10
    # 的探针补 -lc++（实测 rc=0），默认面不采用「加 -lc++ 掩盖静态化」。
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("sqlite3/3.53.4")
        self.requires("tinyxml/2.6.2")
        self.requires("ncurses/6.6")
        # cppunit is consumed only by make check (testRunner binaries);
        # visible=False keeps it out of downstream consumers' graphs.
        self.requires("cppunit/1.15.1", visible=False)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # 共享面策略=原生同形（编排方定案）：conan `pkg_type.py` 对
        # package_type=library（抽象型）+ shared 选项走 deduce_from_options()
        # —— shared=True 推断为有效 SHARED → AutotoolsToolchain 默认注入
        # `--enable-shared --disable-static`（R4 实测：configure 收到该对旗、
        # `ar cru .libs/libpresage.a` 计数=0 即静态未产）。而原生 configure 零
        # shared 开关 → libtool 默认**同时**产出 libpresage.so.1.1.1 + .a（TP
        # 安装树实证、demo 经 .so 链接）。此处把 conan 注入的四类 shared 旗一律
        # 滤除，使 configure 命令行回到零开关 = 原生完全同形；shared 选项保留，
        # 仅作用于有效 package_type（消费侧链接偏好）与 package_id。
        for _flag in ("--enable-shared", "--disable-shared",
                      "--enable-static", "--disable-static"):
            while _flag in tc.configure_args:
                tc.configure_args.remove(_flag)
        # C++ 代差·诊断豁免（A 案，xplc -Wno-* 同手法）：profile compiler.cppstd=17
        # 下 clang15 把上游动态异常规范 `throw (PresageException)` 判为 error
        # （"ISO C++17 does not allow dynamic exception specifications"）。差分读数：
        # 原生构建全量日志 `-std=` 零命中（clang15 默认 gnu++14，__cplusplus=201402L）
        # vs conan 注入 -std=c++17。探针：裸17 rc=1/376B、+本开关 rc=0/0B；真实 5 个
        # 核心 TU（presage.cpp/profileManager/selector/smoothedNgram/contextTracker）
        # 带本开关 -std=c++17 全 rc=0 无其它 C++17 移除特性残留。保留 cppstd=17
        # settings/package_id 语义不动。注意：必须走 extra_cxxflags（实例列表），
        # 不是 property cxxflags（xplc 实测 append 无效坑）。
        tc.extra_cxxflags.append("-Wno-dynamic-exception-spec")
        # （原模板 R26 块 `if not shared: --enable-static/--disable-shared` 已移除：
        # 共享面由上方「滤旗=原生同形零开关双产物」统一权威接管——保留该块会在
        # shared=False 变体把静态旗加回来、与定案冲突；R26 本义针对系统同名库，
        # 本包非系统同名库，deps 静态由各自包 option 决定不受影响。）
        # Optional face: python binding needs swig + python-dev (absent on
        # device and CI worker) -> disable explicitly (W0-④ 可选面禁用).
        tc.configure_args.append("--disable-python-binding")
        # R33: pin -O3 -pipe -DNDEBUG (Release already yields -O3 and -DNDEBUG
        # through conan; -pipe added here).
        tc.extra_cflags.append("-pipe")
        tc.extra_cxxflags.append("-pipe")
        tc.generate()

        deps = AutotoolsDeps(self)
        deps.generate()

        # ── shim 1: cppunit-config ────────────────────────────────────────
        # AM_PATH_CPPUNIT only looks for a `cppunit-config` program; the
        # Conan cppunit package has none. Without it HAVE_CPPUNIT is empty
        # and the upstream unit tests silently do not build (false green).
        cu = self.dependencies["cppunit"]
        shim_dir = os.path.join(self.build_folder or os.getcwd(), "conan-shims")
        cppunit_config = (
            "#!/bin/sh\n"
            'case "$1" in\n'
            '  --cflags)  echo "-I{inc}" ;;\n'
            '  --libs)    echo "-L{lib} -lcppunit" ;;\n'
            '  *)         echo "{ver}" ;;\n'
            'esac\n'
        ).format(
            inc=os.path.join(cu.package_folder, "include"),
            lib=os.path.join(cu.package_folder, "lib"),
            ver=str(cu.ref.version),
        )
        cfg_path = os.path.join(shim_dir, "cppunit-config")
        save(self, cfg_path, cppunit_config)
        # 必须用 os.chmod 落 POSIX mode：conan 的 tools.files chmod 第三参是
        # read/write/execute 布尔（签名 chmod(conanfile, path, read, write, execute)）
        # 不是 mode！传 0o755 会被当 read=True → 文件落 660 无执行位 →
        # AC_PATH_PROG 判 no → HAVE_CPPUNIT 空 → 93 单测静默不构建
        # （R4 实测 checking for cppunit-config... no + All 0 tests passed ×7
        #   = conan 面假绿实锤；E694 草稿预言的形态）
        os.chmod(cfg_path, 0o755)

        # ── shim 2: libcurses.a -> libncursesw.a ─────────────────────────
        # Upstream AC_CHECK_LIB([curses]) links -lcurses; Conan ncurses 6.6
        # only ships wide (*w) library names, so without this symlink
        # presage_demo (the ncurses demo tool) is silently skipped.
        nc = self.dependencies["ncurses"]
        nc_libdir = os.path.join(nc.package_folder, "lib")
        link_path = os.path.join(shim_dir, "libcurses.a")
        for libname in ("libncursesw.a", "libncurses.a"):
            target = os.path.join(nc_libdir, libname)
            if os.path.exists(target):
                if os.path.lexists(link_path):
                    os.remove(link_path)
                os.symlink(target, link_path)
                break

        # Make both shims reachable: PATH for cppunit-config, LIBRARY_PATH
        # for -lcurses (probe-verified: clang honours LIBRARY_PATH), plus an
        # explicit -L so consumers that only read LDFLAGS see it as well.
        env = Environment()
        env.prepend_path("PATH", shim_dir)
        env.prepend_path("LIBRARY_PATH", shim_dir)

        # ── sqlite3 CLI on PATH (CI worker ships none) ─────────────────────
        # SqliteDatabaseConnectorTest::assertDatabaseDumpEqualsBenchmark runs
        # system("sqlite3 <db> \".dump\" > dump") and asserts exit status 0
        # (test/lib/predictors/dbconnector/sqliteDatabaseConnectorTest.cpp
        # :437-438), so `make check` needs the sqlite3 *shell program*, not
        # just libsqlite3. The device PATH carries ~/.harmonybrew/bin/sqlite3
        # (3.53.0) which masks this locally, while the CI worker PATH has no
        # sqlite3 at all -> `sh: sqlite3: inaccessible or not found` and
        # SqliteDatabaseConnectorTest fails 3/14 (testInsertNgram /
        # testUpdateNgram / testIncrementNgramCount), aborting make check
        # (CI build #57994 / buildbot build 66615, conan-build-test
        # results=2; reproduced locally under a harmonybrew-stripped PATH).
        # The sqlite3/3.53.4 dependency already ships bin/sqlite3: expose it
        # through this buildenv script so device and worker resolve the same
        # binary (device masking family, device-facts §一.4).
        sq = self.dependencies["sqlite3"]
        env.prepend_path("PATH", os.path.join(sq.package_folder, "bin"))
        env.vars(self).save_script("conanbuildenv_presage_shims")
        tc.extra_ldflags.append("-L" + shim_dir)

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # L1: upstream test surface runs inside build() — 93 registered
        # CPPUNIT tests (94 CPPUNIT_TEST macros, 1 commented out upstream)
        # across 7 runner programs + test/integration/integration.sh (its
        # training corpus is the shipped COPYING file, not a fabricated
        # fixture).
        autotools.make(target="check")

    def package(self):
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["presage"]
        # bin/ ships presage_demo, presage_demo_text, presage_simulator,
        # text2ngram (+ dbus demo helpers) -> software-level commands.json
        # is required (R38/PF8).
