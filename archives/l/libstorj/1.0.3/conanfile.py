#!/usr/bin/env python3
"""Conan recipe for libstorj 1.0.3 — Autotools (configure + make).

libstorj is Storj Labs' V3 client library (C89/C99): encrypted file
transfer against the Storj bridge/farmer network, plus the `storj` CLI.
Upstream repo is archived (Storj/libstorj -> storj-archived/libstorj);
tag v1.0.3 has no release asset, the canonical source is the tag archive.

Upstream layout: top Makefile.am with SUBDIRS = src . test; the tag
archive ships NO pre-generated configure (autoreconf bootstrap needed).

Direct deps (configure.ac PKG_CHECK_MODULES, all verified published on
the ohpcd remote):
    libcurl >= 7.35.0, nettle >= 3.1, json-c >= 0.11, libuv >= 1.8.0
    libmicrohttpd >= 0.9 (test only: mock bridge :8091 / farmer :8092)

OHOS adaptation notes:
  - Tag archive bootstrap: `autoreconf -fi` in build(), with
    tool_requires("automake/1.18") + ("libtool/2.5.4") because the CI
    worker lacks automake/aclocal/libtoolize (E178; the autoconf suite
    itself is present under /data/service/hnp/bin). Same approach as
    afuse 0.5.0 / abiword-plugin-clarisworks 3.0.8.
  - HMDFS (E114): the generated configure creates its config.status temp
    dir with `umask 077`, yielding drwx--S--- which then dies with
    "can't create ./confXXXX/subs1.awk: Permission denied" (reproduced
    on device 2026-09-21). sed the generated configure to umask 000
    after autoreconf (same fix as aj/abook/mxml/afuse).
  - Upstream links the `storj` CLI and both test programs with
    `-static`. The OHOS SDK ships static musl + libclang_rt, so static
    executables link AND run (probe 2026-09-21: `clang -static` hello →
    ELF EXEC, runs rc=0). Kept as-is — no patch needed for linking.
  - R26: the library itself defaults to static
    (--enable-static --disable-shared); the -static CLI/tests then link
    libstorj.a plus the static archives of the five deps (all dep
    packages default to static in this repo).
  - Upstream tests need $TMPDIR (tests.c main() exits 1 without it);
    make check is driven with TMPDIR pointed at a writable
    build-local directory.
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, get, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class LibstorjConan(ConanFile):
    name = "libstorj"
    version = "1.0.3"
    description = (
        "libstorj - asynchronous multi-platform C library and CLI for "
        "encrypted file transfer on the Storj network (V3 bridge protocol)"
    )
    license = "LGPL-2.1-or-later"  # LICENSE: GNU LGPL v2.1+ (rs.c parts LGPL)
    homepage = "https://github.com/storj-archived/libstorj"
    url = "https://github.com/storj-archived/libstorj"
    topics = ("storj", "libstorj", "encrypted-file-transfer")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # All deps verified published on the ohpcd remote (2026-09-21) and
        # satisfying the configure.ac minimums:
        #   libcurl 8.5.0 (>=7.35.0), nettle 3.10.2.1 (>=3.1),
        #   json-c 0.18 (>=0.11), libuv 1.52.1.1 (>=1.8.0),
        #   libmicrohttpd 1.0.1 (>=0.9, tests/mock servers)
        # NOTE: once requires() is non-empty, AutotoolsDeps in generate()
        # is mandatory — without it configure's AC_CHECK_HEADERS gets no -I
        # and PKG_CHECK_MODULES has no CPPFLAGS/LDFLAGS (debfoster false-green).
        self.requires("libcurl/8.5.0")
        self.requires("nettle/3.10.2.1")
        self.requires("json-c/0.18")
        self.requires("libuv/1.52.1.1")
        self.requires("libmicrohttpd/1.0.1")

    def build_requirements(self):
        # Tag archive ships no configure: build() must run autoreconf -fi.
        # CI worker lacks automake/aclocal/libtoolize (E178) — resolve via
        # tool_requires with the build profile (both -pr:h and -pr:b are
        # passed to conan create). autoconf itself comes from the HNP
        # toolchain (/data/service/hnp/bin), deliberately NOT the conan
        # autoconf/2.72 package (PERL5LIB poison — device-facts §一.23).
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def validate(self):
        # R32
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libstorj supports only Linux/OHOS, got %s" % str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # .pc files for configure's PKG_CHECK_MODULES([LIBCURL]/[NETTLE]/
        # [JSON]/[UV]/[MICROHTTPD]); PKG_CONFIG_PATH points at the generators
        # folder (AutotoolsToolchain sets it in conanautotoolstoolchain.sh).
        PkgConfigDeps(self).generate()
        # The remote libuv package's cpp_info carries pkg_config_name
        # "libuv-static", so PkgConfigDeps emits libuv-static.pc only —
        # configure.ac asks pkg-config for the module "libuv" and dies with
        # "libuv1 1.8.0 or greater was not found" (2026-09-21 现场). Alias it
        # under the upstream module name.
        _uv_static = os.path.join(self.generators_folder, "libuv-static.pc")
        _uv_alias = os.path.join(self.generators_folder, "libuv.pc")
        if os.path.isfile(_uv_static) and not os.path.isfile(_uv_alias):
            with open(_uv_static, "r", encoding="utf-8") as _f:
                _data = _f.read()
            with open(_uv_alias, "w", encoding="utf-8") as _f:
                _f.write(_data.replace("Name: libuv-static", "Name: libuv"))
        # -I/-L/-l injection for AC_CHECK_HEADERS and the lib link (must be
        # generated in addition to PkgConfigDeps — see requirements()).
        AutotoolsDeps(self).generate()

        tc = AutotoolsToolchain(self)
        # R26 default: static library. (conan's default shared flags already
        # emit --enable-static/--disable-shared for shared=False; kept off here
        # to avoid duplicated args in the configure invocation.)
        # LT_INIT pulls AC_CANONICAL_HOST into configure (libtoolize installs
        # build-aux/config.guess+config.sub), while conan emits no triplets for
        # os=OHOS — configure then runs config.guess to determine the BUILD
        # type: the 2024-07 vintage does not recognize uname -s "HarmonyOS"
        # ("cannot guess build type; you must specify one", 2026-09-21 现场),
        # and its TMPDIR compile probe additionally dies on HMDFS. Specify the
        # triplets explicitly so configure never guesses (clarisworks/afuse
        # same approach; config.sub accepts *-linux-ohos).
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        # pkg.m4 (PKG_CHECK_MODULES) lives in the HNP pkg-config install;
        # aclocal must find it while regenerating configure.ac macros.
        env = tc.environment()
        for _d in sorted(glob.glob("/data/service/hnp/*/*/share/aclocal")):
            env.append_path("ACLOCAL_PATH", _d)
        # AutotoolsDeps puts the deps' -I/-L/-l into CPPFLAGS/LDFLAGS/LIBS,
        # but NOT their lib dirs into LD_LIBRARY_PATH — so configure's
        # AC_RUN_IFELSE conftests (and the AC_PROG_CC "whether we are cross
        # compiling" run) link against the remote prebuilt shared libs
        # (libcurl.so/libuv.so.1/libjson-c.so.5 ...) and then die with
        # "Error loading shared library" (rc=127) ⇒ "cannot run C compiled
        # programs" (2026-09-21 现场). Inject the dep lib dirs into the
        # build env so every conftest run — and the upstream `make check`
        # binaries — can load them.
        for _dep in self.dependencies.values():
            for _d in _dep.cpp_info.libdirs:
                env.append_path("LD_LIBRARY_PATH", _d)
        tc.generate(env=env)

    def build(self):
        apply_conandata_patches(self)

        # Tag archive: no pre-generated configure — bootstrap it. Run in the
        # source folder so src/Makefile + test/Makefile land together.
        self.run("autoreconf --install --verbose", cwd=self.source_folder,
                 env="conanbuild")

        # E114 (HMDFS): generated configure uses `umask 077` for its
        # config.status temp dir -> "can't create ./confXXXX/subs1.awk:
        # Permission denied". Relax to 000 (aj/abook/mxml/afuse same fix).
        self.run("sed -i 's/umask 077/umask 000/g' configure",
                 cwd=self.source_folder, env="conanbuild")

        autotools = Autotools(self)
        autotools.configure()
        # E074: parallel make hits HMDFS jobserver fifo EPERM — keep -j1.
        autotools.make(args=["-j1"])

        # Upstream tests need $TMPDIR (tests.c main() exits 1 when unset),
        # and the LIBRARY's internal temp files (.crypt/.parity) come from
        # env->tmp_path — whose TMPDIR branch in storj_init_env() is dead
        # code (`env->tmp_path = NULL;` then `if (env->tmp_path && ...)`) —
        # so without STORJ_TEMP the library falls back to the literal
        # "/tmp", which exists but is READ-ONLY on this device: every
        # fopen(".crypt","w+") fails and storj_bridge_store_file ends with
        # STORJ_FILE_ENCRYPTION_ERROR after 6 retries (diagnosed 2026-09-21
        # with a level-4 log rebuild; STORJ_TEMP is upstream's own escape
        # hatch). Drive make check with both pointing at the same writable
        # build-local directory. Serial: the mock servers bind fixed ports
        # :8091/:8092 (device-facts §一.20).
        check_tmp = os.path.join(self.build_folder, "test-tmp")
        os.makedirs(check_tmp, exist_ok=True)
        self.run(
            'export TMPDIR="%s" STORJ_TEMP="%s" && make check -j1'
            % (check_tmp, check_tmp),
            cwd=self.build_folder, env="conanbuild")

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["storj"]
