#!/usr/bin/env python3
"""Conan recipe for Litecoin Core 0.21.4 — OHOS PC (aarch64) adaptation.

Litecoin Core is a Bitcoin-family fork; 0.21.x keeps the classic autotools
build (autogen.sh + configure + make), with two Litecoin-specific extras
on top of Bitcoin 0.21: the MWEB (MimbleWimble Extension Blocks) module
(src/libmw, static libmw.a) and the scrypt PoW (src/crypto/scrypt*.cpp).
Both are plain C++ (no asm on aarch64 — ARM CRC32 intrinsics are gated
behind configure probes and fall back to plain C on OHOS).

Build system on OHOS:
  * autogen.sh needs automake/aclocal (from ~/usr-local-bin-backup-0911
    with AUTOCONF env override) + libtoolize (conan libtool/2.5.4.1
    tool_requires) + pkg.m4 (system pkg-config share dir). All wired up
    in build() below.
  * configure runs through the upstream build-aux/config.guess which
    already knows `aarch64-unknown-linux-ohos` (E007 knowledge).

Dependencies (all published on the ohpcd registry):
  * boost/1.84.0            — headers + filesystem/regex/program_options/iostreams
  * boost1.84-thread/1.84.0 — libboost_thread.a (Debian-style split package)
  * boost1.84-system/1.84.0 — libboost_system.a
  * openssl/3.5.6           — libssl/libcrypto
  * libevent/2.1.12         — via pkg-config (libevent + libevent_pthreads)
  * db/6.2.32               — Berkeley DB C++ API (wallet), --with-incompatible-bdb
  * fmt/8.1.1               — required by libmw (MWEB), shared .so

Boost layout merge: the three conan packages are merged into a single
prefix (include symlink from boost/1.84.0 + lib symlinks from all three)
because AX_BOOST_BASE expects one boost root.

OHOS specifics:
  * BOOST_SP_NO_PTHREAD_SETCANCELSTATE — OHOS musl lacks
    pthread_setcancelstate (same define the boost packages export).
  * make -j1 — HMDFS has no mkfifo jobserver support.
  * package() copies artifacts byte-identically (shutil.copy2) instead of
    `make install` to preserve OHOS fs-verity code signatures.
  * BDB_CFLAGS/BDB_LIBS bypass BITCOIN_FIND_BDB48 autodetection
    (--with-incompatible-bdb because 6.2 != 4.8).
  * Upstream Makefile.am gaps (not patched, worked around via global
    CPPFLAGS): (a) libbitcoin_util_a_CPPFLAGS lacks $(EVENT_CFLAGS) but
    compiles util/url.cpp (event2/http.h); (b) libbitcoinconsensus_la_
    CPPFLAGS lacks $(BOOST_CPPFLAGS) but compiles libmw sources that
    include boost/optional.hpp transitively.
"""
import os
import shutil
import glob as globmod

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
# db_cxx_stub.h（0004 配套）：拷到源码根，bdb.h include 可解析




class LitecoinConan(ConanFile):
    name = "litecoin"
    version = "0.21.4"
    description = "Litecoin Core node (litecoind/litecoin-cli/litecoin-tx + libbitcoinconsensus, wallet disabled)"
    license = "MIT"
    homepage = "https://litecoin.org/"
    url = "https://github.com/litecoin-project/litecoin"

    package_type = "library"  # ships libbitcoinconsensus.so + node binaries

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    exports_sources = "patches/db_cxx_stub.h"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("boost/1.84.0")
        self.requires("boost1.84-thread/1.84.0")
        self.requires("boost1.84-system/1.84.0")
        self.requires("openssl/3.5.6")
        self.requires("libevent/2.1.12")
        # db/6.2.32 移除：在途 PR #9252 未合入发布（CI #44803 registry
        # unreachable），--disable-wallet 去 BDB 依赖（保留节点+RPC 核心）；
        # #9252 合入后可另轮恢复 wallet
        self.requires("fmt/8.1.1")

    def build_requirements(self):
        self.tool_requires("libtool/2.5.4.1")
        # CI Worker 无 aclocal（autoconf 2.72 装了 automake 没装——
        # "Can't exec aclocal" #45059）：automake 包带 aclocal/automake
        # （codecrypt 先例同款）
        self.tool_requires("automake/1.18")

    def layout(self):
        # in-tree autotools: configure/build inside the source folder
        self.folders.source = "src"
        self.folders.build = "src"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # tarball ships autogen.sh without the group-exec bit (-rwxrwx---)
        os.chmod(os.path.join(self.source_folder, "autogen.sh"), 0o755)

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _merge_boost_prefix(self):
        """Merge the three boost conan packages into one prefix layout
        (include/ + lib/) that AX_BOOST_BASE can digest with
        --with-boost=<prefix>. Includes come from boost/1.84.0 (full
        header set); static libs are symlinked from every package."""
        merge = os.path.join(self.build_folder, "boost-merged")
        libdir = os.path.join(merge, "lib")
        os.makedirs(libdir, exist_ok=True)
        inc = os.path.join(merge, "include")
        if not os.path.exists(inc):
            main = self.dependencies["boost"].package_folder
            os.symlink(os.path.join(main, "include"), inc)
        for dep in ("boost", "boost1.84-thread", "boost1.84-system"):
            pkg_lib = os.path.join(self.dependencies[dep].package_folder, "lib")
            if not os.path.isdir(pkg_lib):
                continue
            for lib in os.listdir(pkg_lib):
                if lib.endswith(".a"):
                    dst = os.path.join(libdir, lib)
                    if not os.path.exists(dst):
                        os.symlink(os.path.join(pkg_lib, lib), dst)
        return merge

    # boost unit-test-framework compilation units (boost/1.84.0 ships the
    # full header set including boost/test/impl/*.ipp but the ohpcd split
    # packages carry no libboost_unit_test_framework.a — the only boost
    # library litecoin's --enable-tests path additionally needs, and none
    # of boost1.84-thread/system/…-prg_exec_monitor provides it). We build
    # it from the shipped .ipp implementation files (exactly what the
    # upstream b2 build does for this lib). cpp_main.ipp belongs to
    # libboost_prg_exec_monitor, NOT the unit-test-framework (its main()
    # clashes with unit_test_main's) — excluded.
    _BOOST_TEST_IPPS = (
        "compiler_log_formatter", "debug", "decorator", "execution_monitor",
        "framework", "junit_log_formatter", "plain_report_formatter",
        "progress_monitor", "results_collector", "results_reporter",
        "test_framework_init_observer", "test_main", "test_tools",
        "test_tree", "unit_test_log", "unit_test_main", "unit_test_monitor",
        "unit_test_parameters", "xml_log_formatter", "xml_report_formatter",
    )

    def _build_boost_unit_test_framework(self, boost_prefix):
        """Compile libboost_unit_test_framework.a from the boost/1.84.0
        header package's boost/test/impl/*.ipp files and drop it into the
        merged boost prefix (the ohpcd registry has no boost1.84-test
        split package — conan list -r=ohpcd verified). Returns the lib
        path. Idempotent: skips when the archive already exists."""
        libdir = os.path.join(boost_prefix, "lib")
        archive = os.path.join(libdir, "libboost_unit_test_framework.a")
        if os.path.isfile(archive):
            return archive
        boost_inc = os.path.join(boost_prefix, "include")
        objdir = os.path.join(boost_prefix, "boost-test-objs")
        os.makedirs(objdir, exist_ok=True)
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cxx = compilers.get("cpp", "clang++")
        objects = []
        for ipp in self._BOOST_TEST_IPPS:
            src = os.path.join(boost_inc, "boost", "test", "impl", f"{ipp}.ipp")
            if not os.path.isfile(src):
                raise ConanException(f"boost test impl missing: {src}")
            obj = os.path.join(objdir, f"{ipp}.o")
            self.run(
                f'"{cxx}" -std=c++17 -fPIC -DBOOST_SP_NO_PTHREAD_SETCANCELSTATE'
                f' -I"{boost_inc}" -x c++ -c "{src}" -o "{obj}"',
                env="conanbuild")
            objects.append(obj)
            self.output.info(f"boost-test ipp compiled: {ipp}")
        ar = shutil.which("llvm-ar") or shutil.which("ar") or "ar"
        # fresh archive (never append to an existing one)
        if os.path.exists(archive):
            os.remove(archive)
        self.run(f'"{ar}" rcs "{archive}" ' + " ".join(f'"{o}"' for o in objects),
                 env="conanbuild")
        self.output.info(f"libboost_unit_test_framework.a built ({len(objects)} objs)")
        return archive

    def _make_pkgconfig_dir(self):
        """Write absolute-path .pc files for libevent (configure resolves
        libevent via PKG_CHECK_MODULES) into a scratch dir."""
        pcdir = os.path.join(self.build_folder, "pkgconfig")
        os.makedirs(pcdir, exist_ok=True)
        event = self.dependencies["libevent"].package_folder
        for name in ("libevent", "libevent_pthreads", "libevent_core", "libevent_extra"):
            src_pc = os.path.join(event, "lib", "pkgconfig", f"{name}.pc")
            if not os.path.isfile(src_pc):
                continue
            with open(src_pc) as f:
                pc = f.read()
            pc = pc.replace("${prefix}", event)
            pc = pc.replace("${libdir}", os.path.join(event, "lib"))
            pc = pc.replace("${includedir}", os.path.join(event, "include"))
            with open(os.path.join(pcdir, f"{name}.pc"), "w") as f:
                f.write(pc)
        return pcdir

    def _autogen_env(self):
        """Return (env_vars_dict) for autogen.sh.

        OHOS developer machines have automake-1.17 in
        ~/usr-local-bin-backup-0911 (moved off PATH because its hardwired
        AUTOCONF default points at a removed prefix) and libtoolize coming
        from the conan libtool tool_requires package. pkg.m4 comes from
        the system pkg-config install. ACLOCAL_PATH must carry libtool +
        pkg-config m4 files, and AUTOCONF must be redirected to the
        working system autoconf.
        """
        from conan.tools.env import Environment as _Env
        env = _Env()
        backup = os.path.expanduser("~/usr-local-bin-backup-0911")
        # tool_requires land in the build context — resolve via .build
        libtool_pkg = self.dependencies.build["libtool"]
        libtool_bin = os.path.join(libtool_pkg.package_folder, "bin")
        libtool_aclocal = os.path.join(libtool_pkg.package_folder, "share", "aclocal")
        # NOTE: do NOT overwrite PATH wholesale — conanbuild env carries its
        # own PATH (compilers, tools); the autogen paths are *prepended* via
        # prepend_path so conan's entries survive.
        if os.path.isdir(backup):
            env.prepend_path("PATH", backup)
        env.prepend_path("PATH", libtool_bin)
        env.define("AUTOCONF", "/data/service/hnp/bin/autoconf")
        aclocal_paths = [libtool_aclocal]
        pkg_m4 = "/data/service/hnp/pkg-config.org/pkg-config_0.29.2/share/aclocal"
        if os.path.isdir(pkg_m4):
            aclocal_paths.append(pkg_m4)
        env.define("ACLOCAL_PATH", ":".join(aclocal_paths))
        env.define("LIBTOOLIZE", os.path.join(libtool_bin, "libtoolize"))
        return env

    # (Environment is imported at build() top; keep a lazy import here too
    #  so the helper stays self-contained.)

    def _patch_configure_scripts(self, src, _re):
        """Pre-patch the embedded config.status template inside every
        configure script (top-level + univalue + secp256k1-zkp).

        HMDFS root cause (verified empirically): dirs created by
        `mktemp -d` under umask 077 are un-writable on HMDFS (ACL quirk
        — even chmod 777 does not unlock them), while plain mkdir dirs
        in the same location are writable. The config.status template
        embedded in each configure contains:

            tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&
            ...
            tmp=./conf$$-$RANDOM
            (umask 077 && mkdir "$tmp")

        We blank the mktemp assignment (forcing the builtin fallback)
        and drop the fallback's umask. configure scripts are *generated*
        by autogen.sh in build() (R6: generated files are runtime-edited,
        never shipped as patches).
        """
        targets = [
            os.path.join(src, "configure"),
            os.path.join(src, "src", "univalue", "configure"),
            os.path.join(src, "src", "secp256k1-zkp", "configure"),
        ]
        for cfg_path in targets:
            if not os.path.isfile(cfg_path):
                continue
            with open(cfg_path) as f:
                cfg = f.read()
            orig = cfg
            # blank the mktemp primary branch (forces mkdir fallback)
            cfg = _re.sub(
                r'tmp=`\(umask 077 && mktemp -d "\.\/confXXXXXX"\) 2>/dev/null`',
                'tmp=',
                cfg)
            # drop the umask on the fallback mkdir
            cfg = _re.sub(r'umask 077 && mkdir "\$tmp"',
                          'umask 022 && mkdir -p "$tmp"', cfg)
            if cfg != orig:
                with open(cfg_path, "w") as f:
                    f.write(cfg)
                self.output.info(f"HMDFS config.status patch applied: {cfg_path}")

    # ------------------------------------------------------------------
    def build(self):
        apply_conandata_patches(self)
        # db_cxx_stub.h（0004 配套）：随配方导出，拷到源码根供 bdb.h include
        # exports_sources 的文件落在 build 树 patches/ 下（conan 缓存布局），
        # 按多候选路径探测拷入 source 根
        import shutil
        _cands = [
            os.path.join(self.build_folder, "patches", "db_cxx_stub.h"),
            os.path.join(self.recipe_folder, "patches", "db_cxx_stub.h"),
        ]
        _cands += [p for p in __import__("glob").glob(
            os.path.join(self.build_folder, "..", "patches", "db_cxx_stub.h"))]
        for _stub_src in _cands:
            if os.path.isfile(_stub_src):
                # autotools DEFAULT_INCLUDES = -I.（编译 cwd=src/src）+
                # -I$(top_builddir)/src/config——stub 拷到这两个可达点
                import shutil as _sh
                _sh.copy(_stub_src, os.path.join(self.source_folder, "src", "db_cxx_stub.h"))
                _sh.copy(_stub_src, os.path.join(self.source_folder, "src", "config", "db_cxx_stub.h"))
                _sh.copy(_stub_src, os.path.join(self.source_folder, "db_cxx_stub.h"))
                break

        from conan.tools.env import Environment

        src = self.source_folder

        # 1) autogen.sh — regenerate configure with local automake/libtool
        autogen_env = self._autogen_env()
        with autogen_env.vars(self).apply():
            self.run(f'cd "{src}" && sh autogen.sh', env="conanbuild")

        # 2) merged boost prefix + self-built libboost_unit_test_framework
        #    (ohpcd has no boost1.84-test package — conan list verified) +
        #    pkg-config dir for libevent
        boost_prefix = self._merge_boost_prefix()
        self._build_boost_unit_test_framework(boost_prefix)
        pcdir = self._make_pkgconfig_dir()

        openssl = self.dependencies["openssl"].package_folder
        libevent = self.dependencies["libevent"].package_folder

        fmt = self.dependencies["fmt"].package_folder

        # 3) configure — with all configure scripts pre-patched for HMDFS.
        # Each configure embeds a config.status template whose mktemp
        # branch breaks on HMDFS (see _patch_configure_scripts below).
        import re as _re
        self._patch_configure_scripts(src, _re)

        conf_env = Environment()
        conf_env.append_path("PKG_CONFIG_PATH", pcdir)
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")
        cxx = compilers.get("cpp", "clang++")
        conf_env.define("CC", cc)
        conf_env.define("CXX", cxx)
        with conf_env.vars(self).apply():
            self.run(
                f'cd "{src}" && ./configure'
                f" --build=aarch64-unknown-linux-ohos"
                f" --host=aarch64-unknown-linux-ohos"
                f" --prefix=/"
                f" --with-boost={boost_prefix}"
                f" --without-gui"
                f" --enable-tests"
                f" --disable-bench"
                f" --disable-zmq"
                f" --disable-man"
                f" --disable-wallet"
                f" --with-miniupnpc=no"
                f" --without-sqlite"
                f' CPPFLAGS="-I{os.path.join(openssl, "include")} -I{os.path.join(fmt, "include")} -I{os.path.join(libevent, "include")} -I{os.path.join(boost_prefix, "include")} -DBOOST_SP_NO_PTHREAD_SETCANCELSTATE -DSTRERROR_R_INT"'
                f' LDFLAGS="-L{os.path.join(openssl, "lib")} -L{os.path.join(fmt, "lib")}"'
,
                env="conanbuild",
            )


        # 4) make -j1 (HMDFS: no jobserver fifo support)
        build_env = Environment()
        build_env.append_path("PKG_CONFIG_PATH", pcdir)
        build_env.define("BOOST_SP_NO_PTHREAD_SETCANCELSTATE", "1")
        with build_env.vars(self).apply():
            self.run(f'cd "{src}" && make -j1', env="conanbuild")

        # 4.5) verify all four node binaries; relink any missing one.
        # litecoind's link (120 MB, ~4 min with lld) has been observed to
        # silently produce no output inside the conan run wrapper (make
        # reports CXXLD then continues; .DELETE_ON_ERROR removes the
        # partial file). A targeted `make -C src <binary>` in a fresh
        # run() invocation links it reliably — verify each artifact and
        # retry the missing ones individually.
        # litecoin-wallet 移除：--disable-wallet 下该工具不构建（其链接
        # 依赖 libbitcoin_wallet 的 WalletTool 符号，已随 wallet 禁用）
        # test_litecoin（--enable-tests）：上游单元测试二进制（462 用例 =
        # 404 src/test + 58 MWEB libmw/test，逐用例实跑记录见
        # notes.md §9.2），全静态链接
        # （test_test_litecoin_LDFLAGS 硬编码 -static；musl libc.a +
        # libc++.a/libunwind.a 均在 OHOS SDK sysroot/llvm 下）
        for bin_name in ("litecoind", "litecoin-cli", "litecoin-tx"):
            out = os.path.join(src, "src", bin_name)
            if not os.path.isfile(out):
                self.output.warning(f"{bin_name} missing after make — relinking")
                with build_env.vars(self).apply():
                    self.run(f'cd "{src}" && make -C src -j1 {bin_name}', env="conanbuild")
                if not os.path.isfile(out):
                    raise ConanException(f"binary {bin_name} failed to link")
            self.output.info(f"binary ready: {bin_name}")

        # 4.6) upstream unit-test binary: bin_PROGRAMS += test/test_litecoin
        # is built by the default `make` target set, but the same silent
        # link-failure mode applies (200+ MB static link, minutes) — verify
        # and relink explicitly if missing.
        test_bin = os.path.join(src, "src", "test", "test_litecoin")
        if not os.path.isfile(test_bin):
            self.output.warning("test_litecoin missing after make — relinking")
            with build_env.vars(self).apply():
                self.run(f'cd "{src}" && make -C src -j1 test_litecoin', env="conanbuild")
            if not os.path.isfile(test_bin):
                raise ConanException("test_litecoin failed to link")
        self.output.info("binary ready: test_litecoin (upstream unit tests)")

    # ------------------------------------------------------------------
    def package(self):
        # OHOS fs-verity: `make install` rewrites RPATH and invalidates
        # code signatures → byte-identical copy instead.
        pkg = self.package_folder
        src = self.source_folder
        for d in ("lib", "bin", "include"):
            os.makedirs(os.path.join(pkg, d), exist_ok=True)

        # 1) node binaries from src/ (autotools keeps them in-place)
        # litecoin-wallet 移除：--disable-wallet 下该工具不构建（其链接
        # 依赖 libbitcoin_wallet 的 WalletTool 符号，已随 wallet 禁用）
        # test_litecoin：上游单元测试二进制（--enable-tests 产出），
        # 供 test_package 全量实跑 462 用例（404 src/test + 58 MWEB；
        # 打包不做 fs-verity 签名的生产件，仅供测试验证；同目录
        # bin/ 一起字节级复制）
        for bin_name in ("litecoind", "litecoin-cli", "litecoin-tx", "test_litecoin"):
            cand = os.path.join(src, "src", bin_name)
            if not os.path.isfile(cand):
                cand = os.path.join(src, "src", "test", bin_name)
            if os.path.isfile(cand):
                shutil.copy2(cand, os.path.join(pkg, "bin", bin_name))
                self.output.info(f"copied {bin_name} -> bin/")

        # 2) libbitcoinconsensus (shared + libtool archive)
        for pat in (".libs/libbitcoinconsensus.so*", "libbitcoinconsensus.so*"):
            for f in globmod.glob(os.path.join(src, "src", pat)):
                base = os.path.basename(f)
                if base.endswith(".a") or base.endswith(".la"):
                    continue
                dst = os.path.join(pkg, "lib", base)
                if not os.path.exists(dst):
                    shutil.copy2(f, dst)
                    self.output.info(f"copied {base} -> lib/")

        # 3) headers for the consensus library API
        inc_src = os.path.join(src, "src")
        # generated config header
        for gen_hdr in ("config/bitcoin-config.h",):
            g = os.path.join(inc_src, gen_hdr)
            if os.path.isfile(g):
                dst_dir = os.path.join(pkg, "include", "config")
                os.makedirs(dst_dir, exist_ok=True)
                shutil.copy2(g, os.path.join(dst_dir, os.path.basename(gen_hdr)))
        # the public consensus header set (script/script.h chain)
        for hdr in ("script/bitcoinconsensus.h",):
            h = os.path.join(inc_src, hdr)
            if os.path.isfile(h):
                dst_dir = os.path.join(pkg, "include", "script")
                os.makedirs(dst_dir, exist_ok=True)
                shutil.copy2(h, os.path.join(dst_dir, os.path.basename(hdr)))

    def package_info(self):
        # components（而非包级 libs）：CMakeDeps 会为 litecoin::bitcoinconsensus
        # 生成按组件 requires 展开的接口——boost 侧解析到 boost 包的组件 target
        # （Boost::headers 等），不会生成包级默认名 boost::boost（后者与
        # boost1.84-thread 抢注的 cmake_file_name=Boost 冲突后不存在）。
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("cmake_file_name", "litecoin")
        comp = self.cpp_info.components["bitcoinconsensus"]
        comp.libs = ["bitcoinconsensus"]
        comp.includedirs = ["include"]
        comp.libdirs = ["lib"]
        comp.system_libs = ["pthread"]
        # Component-level requires: only what libbitcoinconsensus.so
        # actually NEEDs (verified via readelf: libfmt.so.8 + libc++).
        # The boost packages are compile-time only for the consensus lib;
        # referencing their components here would make CMakeDeps emit
        # targets (Boost::headers) that collide with boost1.84-thread's
        # cmake_file_name=Boost registration and don't exist in the
        # generated Boost-Target file — omit them and keep the CMake
        # interface minimal.
        # All direct requires must appear in some component's requires
        # (conan package_info completeness check). The boost family is
        # compile-time only for the consensus library, but is still
        # declared: boost (headers) via its boost_headers component, the
        # split packages via their components, openssl/libevent via
        # package-level, db via the db_cxx component, fmt via package
        # level (the only one libbitcoinconsensus NEEDs at link time).
        comp.requires = [
            "boost::boost_headers",
            "boost1.84-thread::boost_thread",
            "boost1.84-system::boost_system",
            "openssl::openssl",
            "libevent::libevent",
            "fmt::fmt",
        ]
        comp.set_property("cmake_target_name", "litecoin::litecoin")
