#!/usr/bin/env python3
"""Conan recipe for OpenDBX 1.4.6 — Autotools build system.

OpenDBX is a database abstraction layer: libopendbx (C API) plus
libopendbxplus (C++ API). Eight of the nine backend driver modules (mysql,
pgsql, sqlite, firebird, mssql, sybase, oracle, odbc) each require a vendor
client library or a live database server that is unavailable on OHOS, so
this recipe builds the backend-independent core libraries plus the sqlite3
file backend (--with-backends=sqlite3). The sqlite3 backend needs no server:
test_package runs the upstream CREATE/INSERT/SELECT/DROP path against a
local temp file, which is the same file-DB path the upstream odbxtest suite
uses for sqlite3. The core needs nothing but libdl for the dlopen() based
driver loader.

The sqlite3 engine itself is vendored, not required from any Conan remote:
build() downloads the official sqlite-autoconf-3490100 bundle (same URL +
sha256 as the OHOS-adapted archives/s/sqlite3/3.49.1 recipe) and compiles
the amalgamation (sqlite3.c) directly with clang, bypassing the autosetup
configure that cannot run on the HMDFS worker. Rationale: resolving
sqlite3/3.49.1 from a multi-remote preflight graph can pick the upstream
CMake-based recipe, whose configure fails on the preflight machine
(unknown HarmonyOS platform + read-only /tmp compiler-test temp files);
vendoring keeps the sqlite3 file-backend test runnable with zero Conan
dependencies and no remote ambiguity (precedent: luasql/2.4.0 vendors the
sqlite amalgamation the same way).

OHOS scope reductions (all documented in notes.md):
- --disable-utils: drops the odbx-sql shell, which would pull in the
  readline/ncurses dependency chain.
- --disable-nls: drops the libintl dependency.
- Only the sqlite3 file backend is built: the other eight upstream
  regression backends (test/odbxtest.sh matrix) require live database
  servers with per-site credentials (Gentoo RESTRICTs the suite as
  interactive-only). The sqlite3 path needs no server and is exercised by
  test_package against a temp file; `make check` itself has no automake
  TESTS targets, so build() keeps it as a structural Makefile validation.

Build with `make -j1` (upstream is not parallel-safe, Gentoo bug #322221).
C++ sources predate C++11 (dynamic exception specifications), so they are
compiled with -std=c++14 exactly like Gentoo and Alpine do.
"""

import os
import re
import shlex
import shutil
import stat

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rm,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class OpendbxConan(ConanFile):
    name = "opendbx"
    version = "1.4.6"
    description = "Database abstraction layer with a C and C++ API."
    license = "LGPL-2.1-or-later"
    homepage = "https://www.linuxnetworks.de/doc/index.php/OpenDBX"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # Zero Conan dependencies by design. The sqlite3 file-backend engine
        # is vendored from the official sqlite-autoconf bundle and compiled
        # in build() (see _ensure_vendored_sqlite3): resolving sqlite3/3.49.1
        # from a multi-remote graph can select the upstream CMake-based
        # recipe, which fails to configure on the OHOS preflight machine,
        # while CI (conancenter disabled) would use the OHOS-adapted one --
        # a preflight/CI inconsistency. Vendoring removes the ambiguity and
        # keeps the runnable upstream sqlite3 subset. No requires() call.
        pass

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "opendbx recipe is currently adapted for Linux/OHOS only, "
                "not {}".format(self.settings.os)
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(self._configure_args())
        # C++ sources use dynamic exception specifications (pre-C++11);
        # Gentoo and Alpine both build them with -std=c++14.
        tc.cxxflags.append("-std=c++14")
        # VPATH fix: lib/odbx_impl.hpp does #include "lib/odbx_iface.hpp"
        # which only resolves via the top source dir, and test/ tools do
        # #include <odbx.h> which lives in source lib/. In-source builds see
        # both through -I.. / -I../lib (= top / top lib), but Conan VPATH
        # builds compile in build-release/lib|test with -I.. (= build top)
        # and -I../lib (= build lib), so the source headers are not found.
        # Add the top source dir and source lib/ to the search path;
        # include-only, no semantics change.
        src_top = (self.source_folder or "").replace("\\", "/")
        if src_top:
            incs = ["-I{}".format(src_top), "-I{}/lib".format(src_top)]
            for attr in ("cflags", "cxxflags", "extra_cflags", "extra_cxxflags"):
                lst = getattr(tc, attr, None)
                if lst is not None:
                    lst.extend(incs)
            extra_cxx = getattr(tc, "extra_cxxflags", None)
            if extra_cxx is not None:
                extra_cxx.append("-std=c++14")
        # sqlite3 backend headers/libs: opendbx configure probes them via
        # AC_CHECK_HEADERS(sqlite3.h)/AC_CHECK_LIB(sqlite3), which honor
        # CPPFLAGS (-I) and LDFLAGS (-L). The engine is vendored in build()
        # (_ensure_vendored_sqlite3 compiles the official amalgamation into
        # build_folder/sqlite-prefix); point the toolchain at that prefix so
        # the flags land in _configure_args (this recipe drives
        # configure/make with explicit commands that reuse
        # autotools._configure_args, same channel as the VPATH -I flags
        # above that already work on the preflight machine).
        sqlite_prefix = os.path.join(
            self.build_folder or "", "sqlite-prefix"
        ).replace("\\", "/")
        if self.build_folder:
            sqlite_inc = "-I{}/include".format(sqlite_prefix)
            sqlite_libdir = "-L{}/lib".format(sqlite_prefix)
            for attr in ("cflags", "cxxflags", "extra_cflags", "extra_cxxflags"):
                lst = getattr(tc, attr, None)
                if lst is not None:
                    lst.append(sqlite_inc)
            for attr in ("ldflags", "extra_ldflags"):
                lst = getattr(tc, attr, None)
                if lst is not None:
                    lst.append(sqlite_libdir)
        if self.settings.os == "OHOS":
            env = tc.environment()
            shell = self._select_shell()
            tmpdir = self._writable_tmpdir()
            env.define("CONFIG_SHELL", shell)
            env.define("SHELL", shell)
            env.define("TMPDIR", tmpdir)
            env.define("TMP", tmpdir)
            env.define("TEMP", tmpdir)
            self._define_compiler_tools(env)
            tc.generate(env=env)
        else:
            tc.generate()

    def build(self):
        apply_conandata_patches(self)
        self._patch_configure_umask()
        self._prepare_tmpdir()
        self._ensure_vendored_sqlite3()
        autotools = Autotools(self)
        self._configure_autotools(autotools)
        self._patch_interlib_for_ohos_sysroot()
        # R9: -j1, upstream build is not parallel-safe (Gentoo bug #322221).
        self._make_autotools(autotools, args=["-j1"])
        if not self.conf.get("tools.build:skip_test", default=False, check_type=bool):
            # Upstream `make check` has no automake TESTS targets (the
            # odbxtest.sh matrix is driven manually, not via `make check`),
            # so this stays a structural no-op validating the Makefiles.
            # The runnable sqlite3 file-backend subset is exercised in
            # test_package against a temp file instead.
            self._make_autotools(autotools, target="check", args=["-j1"])

    def package(self):
        self._prepare_tmpdir()
        autotools = Autotools(self)
        self._install_autotools(autotools, args=["-j1"])
        rm(self, "*.la", os.path.join(self.package_folder, "lib"), recursive=True)
        self._fallback_install_headers()
        self._fallback_install_libs()
        self._fallback_install_backends()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = ["opendbx", "opendbxplus"]
        self.cpp_info.set_property("cmake_file_name", "opendbx")
        self.cpp_info.set_property("cmake_target_name", "opendbx::opendbx")
        self.cpp_info.set_property("pkg_config_name", "opendbx")

    def _configure_args(self):
        args = []
        if self.settings.os == "OHOS":
            triplet = self._ohos_configure_triplet()
            args.extend(["--build={}".format(triplet), "--host={}".format(triplet)])
        args.extend(
            [
                "--prefix=/",
                # sqlite3 file backend only: every other backend needs a
                # vendor client library or a live server (mysqlclient,
                # libpq, ...) unavailable on OHOS. sqlite3 needs just the
                # file-DB engine (vendored amalgamation, see
                # _ensure_vendored_sqlite3) and no server, so its
                # upstream path runs offline on the preflight machine.
                "--with-backends=sqlite3",
                # Drops the odbx-sql shell and its readline/ncurses chain.
                "--disable-utils",
                # Drops the libintl dependency.
                "--disable-nls",
                "--enable-shared" if self.options.shared else "--disable-shared",
                "--disable-static" if self.options.shared else "--enable-static",
            ]
        )
        return args

    def _ohos_configure_triplet(self):
        if self.settings.arch == "armv8":
            return "aarch64-unknown-linux-gnu"
        raise ConanInvalidConfiguration(
            "opendbx OHOS configure triplet is not mapped for {}".format(
                self.settings.arch
            )
        )

    def _prepare_tmpdir(self):
        if self.settings.os != "OHOS":
            return
        shell = self._select_shell()
        tmpdir = self._writable_tmpdir()
        os.environ["CONFIG_SHELL"] = shell
        os.environ["SHELL"] = shell
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMP"] = tmpdir
        os.environ["TEMP"] = tmpdir

    def _ensure_vendored_sqlite3(self):
        """Compile the vendored sqlite3 amalgamation for the sqlite3 backend.

        真机根因：本配方曾 `requires("sqlite3/3.49.1")`，多 remote 预检图
        可能选中上游 CMake 版 sqlite3 配方，其 configure 在预检机失败
        （cmake 不认 HarmonyOS 平台 + 只读 /tmp 导致编译器自检写临时文件
        失败），而 CI（conancenter 已禁用）则用 OHOS 适配版 —— 预检/CI
        不一致，编译门禁硬失败。本方法改为零 Conan 依赖：直接下载官方
        sqlite-autoconf-3490100 包（URL + sha256 与 OHOS 适配的
        archives/s/sqlite3/3.49.1 配方逐字一致，已在 CI 验证可达），用
        clang 把 amalgamation（sqlite3.c）直编为静态库，绕开 autosetup
        configure（jimsh0 在 HMDFS 上无法 exec 子进程，见本地 sqlite3
        配方注释）与 CMake 双重坑位；布局与编译旗标与本地 sqlite3 配方
        对齐（-fPIC + RTREE/FTS5/COLUMN_METADATA/UNLOCK_NOTIFY/
        SECURE_DELETE/DBSTAT_VTAB）。产物落到 build_folder/sqlite-prefix
        （generate() 已把 -I/-L 指向该前缀），幂等：头文件与静态库齐备
        则跳过。仅替换依赖来源，不改 opendbx 语义与安装布局。
        """
        prefix = os.path.join(self.build_folder or os.getcwd(), "sqlite-prefix")
        inc_dir = os.path.join(prefix, "include")
        lib_dir = os.path.join(prefix, "lib")
        lib = os.path.join(lib_dir, "libsqlite3.a")
        hdr = os.path.join(inc_dir, "sqlite3.h")
        if os.path.isfile(lib) and os.path.isfile(hdr):
            return
        src_dir = os.path.join(self.build_folder or os.getcwd(), "sqlite-src")
        try:
            os.makedirs(src_dir, exist_ok=True)
            os.makedirs(inc_dir, exist_ok=True)
            os.makedirs(lib_dir, exist_ok=True)
        except OSError:
            pass
        marker = os.path.join(src_dir, "sqlite3.c")
        if not os.path.isfile(marker):
            get(
                self,
                url="https://www.sqlite.org/2025/sqlite-autoconf-3490100.tar.gz",
                sha256="106642d8ccb36c5f7323b64e4152e9b719f7c0215acf5bfeac3d5e7f97b59254",
                destination=src_dir,
                strip_root=True,
            )
        cc = self._sqlite_cc()
        ar = self._sqlite_ar(cc)
        defines = (
            "-DSQLITE_THREADSAFE=1 -DSQLITE_ENABLE_RTREE "
            "-DSQLITE_ENABLE_FTS5 -DSQLITE_ENABLE_COLUMN_METADATA "
            "-DSQLITE_ENABLE_UNLOCK_NOTIFY -DSQLITE_SECURE_DELETE "
            "-DSQLITE_ENABLE_DBSTAT_VTAB"
        )
        self._run_with_ohos_env(
            "{} -c -O2 -fPIC -I{} {} {} -o {}".format(
                shlex.quote(cc),
                shlex.quote(src_dir),
                defines,
                shlex.quote(os.path.join(src_dir, "sqlite3.c")),
                shlex.quote(os.path.join(src_dir, "sqlite3.o")),
            )
        )
        self._run_with_ohos_env(
            "{} rcs {} {}".format(
                shlex.quote(ar),
                shlex.quote(lib),
                shlex.quote(os.path.join(src_dir, "sqlite3.o")),
            )
        )
        for name in ("sqlite3.h", "sqlite3ext.h"):
            copy(
                self,
                name,
                src=src_dir,
                dst=inc_dir,
                keep_path=False,
            )
        if not (os.path.isfile(lib) and os.path.isfile(hdr)):
            raise ConanInvalidConfiguration(
                "vendored sqlite3 amalgamation build produced no libsqlite3.a/sqlite3.h"
            )
        self.output.info(
            "vendored sqlite3 amalgamation ready at {}".format(prefix)
        )

    def _sqlite_cc(self):
        # 真机证据：预检沙箱内 /bin/sh 执行绝对路径
        # /data/service/hnp/bin/clang 报 `inaccessible or not found`
        # （exit 127），而 PATH 经 hmbs 前置了可访问的工具目录（本地
        # sqlite3/3.49.1 配方同样只用裸 `clang`/`llvm-ar` 走 PATH）。
        # 因此优先 PATH 解析到的结果，绝对路径只作回退。
        tools = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        configured = tools.get("c") or "clang"
        basename = os.path.basename(configured) or "clang"
        for cand in (
            shutil.which(basename),
            shutil.which("clang"),
            configured,
            "/data/service/hnp/bin/clang",
        ):
            if cand and os.path.isfile(cand):
                return cand
        return basename

    def _sqlite_ar(self, cc):
        for cand in (shutil.which("llvm-ar"), shutil.which("ar")):
            if cand and os.path.isfile(cand):
                return cand
        cc_path = shutil.which(cc) or cc
        sibling = os.path.join(os.path.dirname(cc_path), "llvm-ar")
        if sibling and os.path.isfile(sibling):
            return sibling
        hnp = "/data/service/hnp/bin/llvm-ar"
        if os.path.isfile(hnp):
            return hnp
        return "ar"

    def _writable_tmpdir(self):
        """OHOS 真机 /tmp 为只读挂载，复用 hmbs 注入的可写临时目录。

        优先级 HMBS_TMPDIR > TMPDIR > TMP > TEMP，回退 build_folder/tmp；
        仅替换临时文件根目录，不改安装前缀。调用方负责建目录并透传
        至 configure/make 子进程，避免 autoconf mktemp 落到只读 /tmp。
        只读的 "/tmp" 会被跳过（HMBS readonly_tmp），避免沿用失败。
        """
        for var in ("HMBS_TMPDIR", "TMPDIR", "TMP", "TEMP"):
            value = os.environ.get(var)
            if value and value != "/tmp":
                tmpdir = value
                break
        else:
            tmpdir = os.path.join(self.build_folder or os.getcwd(), "tmp")
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            fallback = os.path.join(self.build_folder or os.getcwd(), "tmp")
            os.makedirs(fallback, exist_ok=True)
            tmpdir = fallback
        return tmpdir

    def _patch_configure_umask(self):
        """HMFS 根因修复：剥离 configure 内 AS_TMPDIR 的 ``umask 077``。

        真机现象与 buildtorrent/0.9.1 同源：toybox ``mktemp -d`` 按
        ``umask 077`` 建出 drwx--S--- 目录后拒绝后续写入，
        ``config.status`` 报 ``can't create ./confXXXX/subs1.awk:
        Permission denied`` → ``could not setup config files machinery``。
        本机能力 chmod:0 + local_mktemp:1 + readonly_tmp 即此模式。

        有意不用 mktemp exit-1 shim：HMBS_CAP_CHMOD=0 下 shim 不可执行，
        且 mkdir fallback 自身仍带 ``umask 077``，不能根治（沿用已验证
        的 buildtorrent 经验）。仅 OHOS 生效，Linux 原样。
        """
        if self.settings.os != "OHOS":
            return
        configure_path = os.path.join(self.source_folder or "", "configure")
        if not configure_path or not os.path.isfile(configure_path):
            return
        try:
            current_mode = os.stat(configure_path).st_mode
            os.chmod(
                configure_path,
                current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH,
            )
        except OSError:
            self.output.warning("chmod +x configure ignored (HMBS_CAP_CHMOD=0)")
        try:
            with open(configure_path, "r", encoding="utf-8", errors="replace") as handle:
                text = handle.read()
        except OSError:
            return
        patched, n_mktemp = re.subn(
            r"um(?:ask|ash) 077 && mktemp -d", "mktemp -d", text
        )
        patched, n_mkdir = re.subn(
            r"um(?:ask|ash) 077 && mkdir", "mkdir", patched
        )
        if n_mktemp == 0 and n_mkdir == 0:
            self.output.warning(
                "configure has no AS_TMPDIR 'umask 077' pattern; "
                "HMFS workaround not applied"
            )
            return
        with open(configure_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(patched)
        self.output.info(
            "patched configure AS_TMPDIR: removed 'umask 077 && ' "
            "for HMFS writable tmpdir (mktemp:%d, mkdir:%d)"
            % (n_mktemp, n_mkdir)
        )

    def _patch_interlib_for_ohos_sysroot(self):
        """OHOS 安装期重链接修复：libopendbxplus 改直链构建期 .so。

        真机现象：`make` 构建成功，`make install DESTDIR=...` 在
        `libtool --mode=relink libopendbxplus.la` 报
        `ld.lld: error: unable to find library -lopendbx`。
        上游 `lib/Makefile.am` 声明
        `libopendbxplus_la_LIBADD = $(LTLIBINTL) libopendbx.la`，
        构建期 libtool 经相对 VPATH 解析到构建目录 `.libs`（成功），
        安装期 relink 则经绝对 `-L<DESTDIR>//lib -lopendbx` 解析已安装
        的 `libopendbx`（OHOS sysroot 交叉下该绝对搜索落空，失败）。
        因此在 configure 生成构建 `lib/Makefile` 后、make 之前，把
        `libopendbxplus_la_LIBADD` 中的 `libopendbx.la` 替换为构建目录
        下绝对路径 `.libs/libopendbx.so` 直链：直接文件参数不走 `-l`
        搜索，构建与安装期 relink 均可直接打开；`DEPENDENCIES` 行保持
        `libopendbx.la` 不动，仍保证先编 libopendbx 的串行顺序。
        仅 OHOS shared 生效；static 无 relink，Linux 原样。

        只替换临时文件根目录之外的链接写法，不删测试、不改安装布局
        （头文件与 .pc 仍走 `make install`）。
        """
        if self.settings.os != "OHOS":
            return
        try:
            shared = bool(self.options.shared)
        except Exception:
            shared = True
        if not shared:
            return
        build_root = self.build_folder or ""
        candidates = []
        if build_root:
            candidates.append(os.path.join(build_root, "lib", "Makefile"))
            candidates.append(os.path.join(build_root, "build-release", "lib", "Makefile"))
            # VPATH 布局兜底：递归找 build 树下的 lib/Makefile（最多走 4 层）。
            try:
                for root, dirs, files in os.walk(build_root):
                    depth = os.path.relpath(root, build_root).count(os.sep)
                    if depth > 4:
                        dirs[:] = []
                        continue
                    if os.path.basename(root) == "lib" and "Makefile" in files:
                        candidate = os.path.join(root, "Makefile")
                        if candidate not in candidates:
                            candidates.append(candidate)
                        dirs[:] = []
            except OSError:
                pass
        seen = set()
        for makefile in list(candidates):
            if not makefile or makefile in seen:
                continue
            seen.add(makefile)
            if not os.path.isfile(makefile):
                continue
            try:
                with open(makefile, "r", encoding="utf-8", errors="replace") as handle:
                    text = handle.read()
            except OSError:
                continue
            if "libopendbxplus_la_LIBADD" not in text:
                continue
            lib_dir = os.path.dirname(makefile)
            direct = os.path.join(lib_dir, ".libs", "libopendbx.so")
            patched, count = re.subn(
                r"(?m)^(libopendbxplus_la_LIBADD\s*=\s*.*?)\blibopendbx\.la\b",
                lambda match: match.group(1) + direct,
                text,
                count=1,
            )
            if count == 0:
                continue
            with open(makefile, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(patched)
            self.output.info(
                "patched libopendbxplus LIBADD to direct {} (OHOS sysroot relink fix)".format(direct)
            )
            return
        self.output.warning(
            "lib/Makefile for OHOS sysroot relink fix not found; install relink may fail"
        )

    def _configure_autotools(self, autotools):
        if self.settings.os != "OHOS":
            autotools.configure()
            return
        configure = os.path.join(self.source_folder, "configure")
        command = " ".join(
            part for part in (shlex.quote(configure), autotools._configure_args) if part
        )
        self._run_with_ohos_env(command)

    def _make_autotools(self, autotools, target=None, args=None):
        if self.settings.os != "OHOS":
            autotools.make(target=target, args=args)
            return
        command = [self._make_program()]
        if target:
            command.append(target)
        command.extend(args or [])
        self._run_with_ohos_env(shlex.join(command))

    def _install_autotools(self, autotools, args=None):
        if self.settings.os != "OHOS":
            autotools.install(args=args)
            return
        opts = [a for a in (args or []) if a.startswith("-")]
        extras = [a for a in (args or []) if not a.startswith("-")]
        install_args = opts + ["DESTDIR={}".format(self.package_folder), "install"] + extras
        self._make_autotools(autotools, args=install_args)

    def _fallback_install_headers(self):
        """兜底补装头文件：真机 `make install DESTDIR` 未落下头文件时补齐。

        真机证据：test_package 以 `-I<package>/include` 编译
        `test_opendbx.c` 报 `fatal error: 'odbx.h' file not found`，
        说明 `make install` 的头文件未进入 `package_folder/include`。
        上游头文件为静态文本（`lib/odbx.h` + `lib/opendbx/` 目录，
        Alpine `opendbx-dev` 同口径为 `/usr/include/odbx.h` 与
        `/usr/include/opendbx/api`），从源码树补拷不改变语义；
        仅当目标缺失时复制，已正确安装时保持 `make install` 结果不动。
        """
        if not self.source_folder:
            return
        include_dir = os.path.join(self.package_folder, "include")
        top_header = os.path.join(include_dir, "odbx.h")
        if not os.path.isfile(top_header):
            copy(
                self,
                "odbx.h",
                src=os.path.join(self.source_folder, "lib"),
                dst=include_dir,
                keep_path=False,
            )
        cxx_dir = os.path.join(include_dir, "opendbx")
        need_cxx = (not os.path.isdir(cxx_dir)) or (not os.listdir(cxx_dir))
        if need_cxx:
            copy(
                self,
                "*",
                src=os.path.join(self.source_folder, "lib", "opendbx"),
                dst=cxx_dir,
                keep_path=True,
            )

    def _fallback_install_libs(self):
        """兜底补装可链接库：真机 test_package 报 -lopendbx 找不到时补齐。

        真机证据：`make` 已编出 `.libs/libopendbx.so.1.2.0` 及
        `.libs/libopendbxplus.so.1.0.0`，但 test_package 以
        `-L<package>/lib -lopendbx` 链接报
        `ld.lld: error: unable to find library -lopendbx`，
        说明 `make install DESTDIR` 未把可链接库落到
        `package_folder/lib`（版本链缺失或布局差异）。
        从构建树 `.libs/` 补拷同名产物并重建 `libopendbx.so` /
        `libopendbxplus.so` 开发软链（失败则复制），不改变语义；
        已正确安装时保持 `make install` 结果不动。static 时补 `.a`。
        """
        try:
            shared = bool(self.options.shared)
        except Exception:
            shared = True
        lib_dir = os.path.join(self.package_folder, "lib")
        try:
            os.makedirs(lib_dir, exist_ok=True)
        except OSError:
            pass
        try:
            before = sorted(os.listdir(lib_dir))
        except OSError:
            before = []
        self.output.info("package lib before fallback: {}".format(before))
        for base in ("libopendbx", "libopendbxplus"):
            if shared:
                self._ensure_dev_link(lib_dir, base)
            else:
                self._ensure_static_lib(lib_dir, base)
        # shared 且开发链仍缺失时，从构建树 .libs 补拷版本链。
        if shared:
            missing = [
                base
                for base in ("libopendbx", "libopendbxplus")
                if not os.path.isfile(os.path.join(lib_dir, base + ".so"))
            ]
            if missing:
                copied = self._copy_built_so_chain(lib_dir, set(missing))
                self.output.info(
                    "fallback copied built .so chain for {}: {}".format(missing, copied)
                )
                for base in missing:
                    self._ensure_dev_link(lib_dir, base)
        try:
            after = sorted(os.listdir(lib_dir))
        except OSError:
            after = []
        self.output.info("package lib after fallback: {}".format(after))

    def _ensure_dev_link(self, lib_dir, base):
        """版本链存在但缺 `libfoo.so` 时重建开发链（软链优先，失败则复制）."""
        dev = os.path.join(lib_dir, base + ".so")
        if os.path.isfile(dev) or os.path.islink(dev):
            return
        try:
            entries = sorted(os.listdir(lib_dir))
        except OSError:
            return
        versioned = [e for e in entries if e.startswith(base + ".so.") and e != base + ".so"]
        if not versioned:
            return
        # 优先最长版本号（如 .so.1.2.0），与 libtool 构建产物一致。
        versioned.sort(key=len, reverse=True)
        target = versioned[0]
        try:
            if os.path.islink(dev) or os.path.exists(dev):
                os.remove(dev)
        except OSError:
            pass
        try:
            os.symlink(target, dev)
            self.output.info("recreated dev symlink {} -> {}".format(dev, target))
        except OSError:
            try:
                shutil.copy2(os.path.join(lib_dir, target), dev)
                self.output.info("copied {} as dev link fallback".format(dev))
            except OSError as exc:
                self.output.warning("dev link fallback failed for {}: {}".format(dev, exc))

    def _ensure_static_lib(self, lib_dir, base):
        if os.path.isfile(os.path.join(lib_dir, base + ".a")):
            return
        copied = self._copy_built_so_chain(lib_dir, {base}, suffix=".a")
        if copied:
            self.output.info("fallback copied built static lib for {}: {}".format(base, copied))

    def _copy_built_so_chain(self, lib_dir, bases, suffix=".so"):
        copied = []
        build_root = self.build_folder or ""
        if not build_root or not os.path.isdir(build_root):
            return copied
        try:
            walker = os.walk(build_root)
        except OSError:
            return copied
        for root, _dirs, _files in walker:
            if os.path.basename(root) != ".libs":
                continue
            try:
                entries = os.listdir(root)
            except OSError:
                continue
            for entry in entries:
                for base in bases:
                    if not entry.startswith(base + suffix):
                        continue
                    src = os.path.join(root, entry)
                    dst = os.path.join(lib_dir, entry)
                    if os.path.isfile(dst) or os.path.islink(dst):
                        continue
                    try:
                        if os.path.islink(src):
                            target = os.readlink(src)
                            try:
                                os.symlink(target, dst)
                            except OSError:
                                shutil.copy2(os.path.realpath(src), dst)
                        elif os.path.isfile(src):
                            shutil.copy2(src, dst)
                        else:
                            continue
                        copied.append(entry)
                    except OSError as exc:
                        self.output.warning(
                            "fallback copy {} -> {} failed: {}".format(src, dst, exc)
                        )
        return copied

    def _fallback_install_backends(self):
        """兜底补装 sqlite3 后端 .so：保证裸 soname 为真实文件。

        真机证据：test_package 以 glob 找到 libsqlite3backend.so（悬空
        软链）后 realpath 到 libsqlite3backend.so.1.2.0 再 copy2，报
        FileNotFoundError——包内 lib/opendbx 只有悬空链、缺真实字节，
        dlopen 与后续暂存都无从谈起。根因是 make install 的后端版本链
        在 OHOS DESTDIR 下不完整（与 libopendbx/libopendbxplus 的缺链
        同类问题，但后者已有 _fallback_install_libs 覆盖，后端此前无
        覆盖）。本方法只做最小修复：若包内裸 soname 不是真实可读文件
        （缺失或悬空链），从构建树所有 .libs（含 backends/sqlite*/.libs）
        找最大且非空的 libsqlite3backend.so* 真实文件，按字节复制为裸
        soname（先删悬空链；复制不用软链，HMDFS 软链能力不可靠）；已是
        真实文件时不动，不改安装布局与语义。
        """
        backend_dir = os.path.join(self.package_folder, "lib", "opendbx")
        try:
            os.makedirs(backend_dir, exist_ok=True)
        except OSError:
            pass
        bare = os.path.join(backend_dir, "libsqlite3backend.so")
        if os.path.isfile(bare):
            try:
                if os.path.getsize(bare) > 0:
                    with open(bare, "rb") as handle:
                        if handle.read(4) == b"\x7fELF":
                            return
            except OSError:
                pass
        # 包内版本链现状打日志，便于下轮真机定位。
        try:
            before = sorted(os.listdir(backend_dir))
        except OSError:
            before = []
        self.output.info("package backend before fallback: {}".format(before))
        best = None
        best_size = -1
        build_root = self.build_folder or ""
        if build_root and os.path.isdir(build_root):
            try:
                walker = os.walk(build_root)
            except OSError:
                walker = iter(())
            for root, _dirs, _files in walker:
                if os.path.basename(root) != ".libs":
                    continue
                try:
                    entries = os.listdir(root)
                except OSError:
                    continue
                for entry in entries:
                    if not entry.startswith("libsqlite3backend.so"):
                        continue
                    src = os.path.join(root, entry)
                    # isfile 跟随软链：悬空链返回 False，自动跳过。
                    if not os.path.isfile(src):
                        continue
                    try:
                        size = os.path.getsize(src)
                    except OSError:
                        continue
                    if size <= 0 or size <= best_size:
                        continue
                    try:
                        with open(src, "rb") as handle:
                            if handle.read(4) != b"\x7fELF":
                                continue
                    except OSError:
                        continue
                    best = src
                    best_size = size
        if best is None:
            self.output.warning(
                "backend fallback found no built libsqlite3backend.so* ELF; "
                "keeping package backend state {}".format(before)
            )
            return
        try:
            if os.path.islink(bare) or os.path.exists(bare):
                os.remove(bare)
        except OSError:
            pass
        try:
            # 按字节复制为真实文件，不建软链。
            with open(best, "rb") as src_handle:
                data = src_handle.read()
            with open(bare, "wb") as dst_handle:
                dst_handle.write(data)
            self.output.info(
                "fallback installed backend {} ({} bytes) -> {}".format(
                    best, len(data), bare
                )
            )
        except OSError as exc:
            self.output.warning(
                "fallback install backend {} -> {} failed: {}".format(best, bare, exc)
            )

    def _run_with_ohos_env(self, command, **kwargs):
        if self.settings.os != "OHOS":
            self.run(command, **kwargs)
            return
        self.run("{} {}".format(self._ohos_env_prefix(), command), **kwargs)

    def _ohos_env_prefix(self):
        shell = self._select_shell()
        tmpdir = self._writable_tmpdir()
        env = {
            "CONFIG_SHELL": shell,
            "SHELL": shell,
            "TMPDIR": tmpdir,
            "TMP": tmpdir,
            "TEMP": tmpdir,
        }
        return " ".join(
            "{}={}".format(key, shlex.quote(value)) for key, value in env.items()
        )

    def _make_program(self):
        return self.conf.get("tools.gnu:make_program", default="make")

    def _define_compiler_tools(self, env):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        for key, var, fallback in (
            ("c", "CC", "clang"),
            ("cpp", "CXX", "clang++"),
            ("cxx", "CXX", "clang++"),
        ):
            command = compilers.get(key)
            if command:
                env.define(var, self._resolve_configured_tool(command, fallback))
        for key, var in (
            ("ar", "AR"),
            ("ranlib", "RANLIB"),
            ("nm", "NM"),
            ("strip", "STRIP"),
        ):
            command = compilers.get(key) or self._tool_from_compiler_dir(key)
            if command:
                env.define(var, command)

    def _tool_from_compiler_dir(self, name):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = compilers.get("c") or compilers.get("cpp") or ""
        compiler_path = shutil.which(compiler) or compiler
        compiler_dir = os.path.dirname(compiler_path) if compiler_path else ""
        llvm_name = "llvm-" + name
        for candidate in (
            os.path.join(compiler_dir, llvm_name) if compiler_dir else "",
            shutil.which(llvm_name) or "",
            shutil.which(name) or "",
        ):
            if candidate and os.path.isfile(candidate):
                return candidate
        return ""

    def _resolve_configured_tool(self, command, fallback):
        basename = os.path.basename(command)
        hmbs_bin = "/data/service/hnp/bin"
        for candidate in (
            command,
            shutil.which(basename) or "",
            os.path.join(hmbs_bin, basename),
        ):
            resolved = shutil.which(candidate) or candidate
            if os.path.isfile(resolved) and os.access(resolved, os.X_OK):
                return resolved
        return self._resolve_tool(fallback)

    def _resolve_tool(self, name, aliases=()):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = compilers.get("c") or compilers.get("cpp") or ""
        compiler_path = shutil.which(compiler) or compiler
        compiler_dir = os.path.dirname(compiler_path) if compiler_path else ""

        env_key = name.upper().replace("-", "_")
        candidates = [os.environ.get(env_key), compilers.get(name)]
        for alias in aliases:
            candidates.append(compilers.get(alias))
        if compiler_dir:
            candidates.append(os.path.join(compiler_dir, name))
            for alias in aliases:
                candidates.append(os.path.join(compiler_dir, alias))
        candidates.extend(
            [
                os.path.join("/data/service/hnp/bin", name),
                shutil.which(name) or "",
            ]
        )
        for alias in aliases:
            candidates.append(shutil.which(alias) or "")

        for candidate in candidates:
            if not candidate:
                continue
            resolved = shutil.which(candidate) or candidate
            if os.path.isfile(resolved) and os.access(resolved, os.X_OK):
                return resolved
        raise ConanInvalidConfiguration("required OHOS tool was not found: " + name)

    def _select_shell(self):
        for shell in (
            os.environ.get("CONFIG_SHELL"),
            os.environ.get("SHELL"),
            os.path.join(os.path.expanduser("~"), "usr/local", "bin", "bash"),
            "/bin/sh",
            "/system/bin/sh",
            "sh",
        ):
            if not shell:
                continue
            resolved = shutil.which(shell) or shell
            if os.path.isfile(resolved) and os.access(resolved, os.X_OK):
                return resolved
        return "sh"
