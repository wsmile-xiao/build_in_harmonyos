#!/usr/bin/env python3
"""Conan recipe — QSopt_ex 2.5.10.3 (Autotools, exact rational LP solver library).

Upstream: https://github.com/jonls/qsopt-ex (tag v2.5.10.3)
QSopt_ex is a fork of the QSopt_ex exact rational linear-programming solver
(David Applegate / William Cook / Sanjeeb Dash / Daniel Espinoza), updated by
Jon Lund Steffensen with a friendlier autotools build system. The C library
libqsopt_ex delivers exact rational solutions to LP instances using GNU MP.
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class QsoptConan(ConanFile):
    name = "qsopt"
    version = "2.5.10.3"
    description = "QSopt_ex: exact rational linear programming (LP) solver library"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/jonls/qsopt-ex"
    url = "https://github.com/jonls/qsopt-ex"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}
    # Deterministic autotools outputs (configure/Makefile.in/aux files)
    # generated once with autoconf 2.73 + automake 1.18.1 + libtool 2.4.7:
    # the CI OHOS worker ships autoconf but NOT automake (no aclocal in
    # PATH), so build-time autoreconf fails there ("Can't exec aclocal").
    # Shipping the generated files mirrors upstream release tarball practice
    # (their tag tarball omits them) and keeps the build independent of
    # worker autotools versions. Applied in build() when configure is absent.
    exports_sources = "autotools/*"

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # GMP is a hard dependency of the exact solver (configure errors out
        # without it); zlib/bzip2 enable gz/bz2-compressed LP/MPS I/O and are
        # enabled by the upstream Debian/Fedora packaging as well.
        self.requires("gmp/6.3.0")
        self.requires("zlib/1.3.1")
        self.requires("bzip2/1.0.8")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        else:
            tc.configure_args.append("--disable-static")
            tc.configure_args.append("--enable-shared")
        # PIC objects let downstream link the static archive into shared libs.
        tc.configure_args.append("--with-pic")
        # OHOS: configure looks like a cross build (build=linux-gnu,
        # host=linux-ohos) exactly like the reviewed libopendbx recipe:
        # the vendor slot must be non-empty or libtool's `case $host_os in
        # linux*)` misses `ohos` and falls back to static-only (no .so).
        if str(self.settings.os) == "OHOS":
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-ohos",
                # AC_FUNC_MALLOC/REALLOC/MEMCMP/STRTOD probes run the test
                # binary; they cannot run under a cross-looking configure, and
                # their conservative cross defaults #define rpl_* that the
                # upstream code does not implement. bionic/musl have the
                # standard semantics, so pin the cache results (same pins as
                # libopendbx; strtod/memcmp added for this configure.ac).
                "ac_cv_func_malloc_0_nonnull=yes",
                "ac_cv_func_realloc_0_nonnull=yes",
                "ac_cv_func_memcmp_working=yes",
                "ac_cv_func_strtod=yes",
            ])
        # AutotoolsToolchain does not aggregate dependency cpp_info into
        # CPPFLAGS/LDFLAGS: inject gmp/zlib/bzip2 include+lib paths so the
        # AC_CHECK_LIB probes (gmp hard, z/bz2 optional) all succeed.
        for dep_name in ("gmp", "zlib", "bzip2"):
            dep = self.dependencies[dep_name]
            inc = os.path.join(dep.package_folder, dep.cpp_info.includedirs[0])
            lib = os.path.join(dep.package_folder, dep.cpp_info.libdirs[0])
            tc.extra_cflags.append(f"-I{inc}")
            tc.extra_ldflags.append(f"-L{lib}")
        # OHOS: libtool's shared-lib probe needs libc++ from the SDK llvm/lib
        # (runtime LD_LIBRARY_PATH only), otherwise it decides static-only.
        # Only relevant when shared=True; harmless otherwise.
        if str(self.settings.os) == "OHOS":
            sdk_llvm_libs = sorted(
                glob.glob("/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib")
            )
            if sdk_llvm_libs:
                tc.extra_ldflags.append(f"-L{sdk_llvm_libs[-1]}")
            else:
                self.output.warning("OHOS SDK llvm/lib not found; shared libs may not build")
        tc.generate()

    def build(self):
        autotools = Autotools(self)
        # The upstream tag tarball ships no generated configure script
        # (autoreconf source only). CI OHOS workers have autoconf but not
        # automake (aclocal missing from PATH), so regenerate from scratch
        # would fail there; the recipe therefore ships the generated outputs
        # (autotools/, produced once with autoconf 2.73/automake 1.18.1/
        # libtool 2.4.7) and restores them if configure is absent. autoreconf
        # remains only as a dev fallback when even the shipped set is gone.
        if not os.path.exists(os.path.join(self.source_folder, "configure")):
            shipped = os.path.join(self.source_folder, "autotools")
            if os.path.isdir(shipped):
                self.output.info("restoring shipped autotools generated files")
                for root, _dirs, files in os.walk(shipped):
                    rel = os.path.relpath(root, shipped)
                    dst_dir = self.source_folder if rel == "." else os.path.join(self.source_folder, rel)
                    os.makedirs(dst_dir, exist_ok=True)
                    for name in files:
                        shutil.copy2(os.path.join(root, name), os.path.join(dst_dir, name))
                # Past-stamp the autotools INPUTS (tarball's configure.ac,
                # tarball m4/*.m4, shipped m4 macros) — content untouched,
                # mtimes only. CI workers lack automake (no aclocal), so
                # automake's maintainer rules must never decide
                # aclocal.m4/configure/Makefile.in are stale and try to
                # regenerate them (missing m4/libtool.m4* prerequisites
                # would make make rebuild aclocal.m4 unconditionally).
                # Shipped aclocal.m4/configure/Makefile.in keep their normal
                # mtime (newer than all inputs); configure's own build-env
                # sanity check still passes (files it creates are newer).
                for dep in ["configure.ac"] + glob.glob(
                    os.path.join(self.source_folder, "m4", "*.m4")
                ) + glob.glob(os.path.join(self.source_folder, "autotools", "m4", "*.m4")):
                    if os.path.exists(dep):
                        os.utime(dep, (946684800, 946684800))  # 2000-01-01
                for basename in ("aclocal.m4", "configure", "Makefile.in", "config.h.in"):
                    path = os.path.join(self.source_folder, basename)
                    if os.path.exists(path):
                        self.output.info(
                            "shipped %s mtime=%s" % (basename, int(os.stat(path).st_mtime))
                        )
            else:
                self.output.warning("neither configure nor shipped autotools/ found; running autoreconf")
                autotools.autoreconf()
        # config.sub is generated with a recent automake that already knows
        # the linux-ohos kernel-OS pair; on older machines the shipped probe
        # applies the same 3 edits as scripts/patch-autotools-ohos.pl and
        # knowledge E072/E122 (idempotent, no-op when already accepted).
        self._patch_config_sub_if_needed()
        autotools.configure()
        autotools.make(args=["-j1"])
        # Upstream TAP suite (tests/test_qs): runs when the test binary can
        # execute natively (CI builds natively on OHOS; local cross-builds
        # cannot run the armv8 binary, so make check is skipped there).
        if can_run(self):
            autotools.make(target="check", args=["-j1"])

    def _patch_config_sub_if_needed(self):
        config_sub = os.path.join(self.source_folder, "config.sub")
        if not os.path.isfile(config_sub):
            return
        # Text-based probe (no shell needed — CI workers may lack `sh`/`curl`
        # in PATH): accept the OHOS triplet directly if config.sub already
        # knows linux-ohos (shipped automake 1.18.1 config.sub does).
        with open(config_sub, errors="replace") as f:
            content = f.read()
        if "linux-ohos" in content:
            self.output.info("config.sub already accepts aarch64-unknown-linux-ohos")
            return
        self.output.info("patching generated config.sub for linux-ohos triplet")
        from conan.tools.files import replace_in_file

        # 1) basic_os mapping: ohos-linux -> linux-ohos (after android-linux)
        replace_in_file(
            self,
            config_sub,
            "android-linux)",
            "android-linux)\n    ohos-linux)\n        basic_machine=$field1-unknown\n        basic_os=linux-ohos",
        )
        # 2) OS whitelist: add ohos* (guard: same block as android*|gnu*)
        replace_in_file(
            self,
            config_sub,
            "| android* | gnu* |",
            "| android* | ohos* | gnu* |",
        )
        # 3) kernel-OS pair: linux-ohos* accepted (after linux-android*-)
        replace_in_file(
            self,
            config_sub,
            "linux-android*- )",
            "linux-android*- | linux-ohos*- )",
        )

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # Library package: drop the interactive esolver demo binary (a plain
        # library per ARCHIVE-SPEC R38 — no commands.json needed) and the
        # libtool .la wrappers (not needed at runtime).
        bin_dir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bin_dir):
            shutil.rmtree(bin_dir)
        for _la in glob.glob(os.path.join(self.package_folder, "lib", "**", "*.la"), recursive=True):
            os.remove(_la)

    def package_info(self):
        self.cpp_info.libs = ["qsopt_ex"]
        # configure AC_SEARCH_LIBS(pow, m) and pthread probe add -lm/-lpthread
        self.cpp_info.system_libs = ["m", "pthread"]
