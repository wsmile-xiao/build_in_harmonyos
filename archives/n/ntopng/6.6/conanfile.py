#!/usr/bin/env python3
"""Conan recipe for ntopng 6.6 — high-speed web-based network traffic analysis.

ntopng is a network traffic probe / web GUI (ntop.org).  Autotools C++ project
(configure.ac.in + Makefile.in, ~900 translation units) which also builds the
bundled third-party lua-5.4.6 and rrdtool-1.4.8 libraries.

OHOS(aarch64)/worker-filesystem notes validated during the manual buildwork chain
(see buildwork/ohc-logs + archives notes.md, 2026-09-05/06):
  * nDPI pairing is **5.0** (released 2025-11-17T08:11Z, same morning as ntopng
    tag 6.6).  ntopng 6.6 calls ndpi_init_detection_module(NULL) (1-arg) which is
    the nDPI 5.x API; nDPI 6.0 (2026-08-28) switched to a 2-arg call and does NOT
    compile against ntopng 6.6.  nDPI/libmaxminddb are NOT published on remote
    ohpcd, so they are built here from official sources into a private prefix
    (R49) and are NOT listed in requires (W3 L0i / R36 only checks requires).
  * clickhouse-cpp is a git submodule absent from release tarballs -> Makefile.in
    guard (patch 0001).  Community edition has no Pro/clickhouse need.
  * rrdtool's bundled configure cannot `config.guess` on HarmonyOS
    (uname -s=HarmonyOS, kernel "HongMeng Kernel") -> pass
    --build=aarch64-unknown-linux-gnu; also LIBRRDTOOL_LIB carries a bare
    "-lm" which GNU make turns into a second (race-prone) target -> dropped
    (patch 0002).  Build serially is not required anymore; -j8 was validated.
  * rrdtool 1.4.8 configure.ac hard-checks glib-2.0/libxml-2.0 (only needed by
    rrd_graph which ntopng disables) and *nroff/*troff (only for docs).  None
    exist on this machine.  The build image has NO autopoint, so rrdtool's own
    autogen.sh (autoreconf --install) cannot regenerate configure.  build()
    therefore patches the CHECKED-IN generated configure directly (the hard
    EX_CHECK_ALL gate and the two doc-tool aborts are downgraded), runs it once
    to emit rrd_config.h/Makefiles, then archives the core librrd subset
    (rrd_graph + rrd_restore excluded - they need glib/libxml) into
    src/.libs/librrd_th.a where the top-level Makefile expects it (same subset
    as the manual buildwork chain, ARCHIVE_OK 2026-09-05).  configure.ac /
    src/Makefile.am are edited too, for provenance/documentation only.
  * autoconf-generated `configure`/`config.status` create their private temp dir
    with `(umask 077 && mktemp -d ...)`.  On this worker FS a mode-0700 dir is
    NOT owner-writable and chmod is a no-op, so the run fails with
    "can't create ./confXXXX/subs1.awk: Permission denied".  -> sed
    `umask 077` to `umask 002` right after every autogen.sh (E011 pattern).
  * The Lua bundled Makefile hard-codes `CC= gcc -std=gnu99`; there is no gcc
    here.  -> always call make with `CC=<clang> CXX=<clang++>` on the command
    line so the value is propagated to sub-makes (command line overrides the
    Makefile assignment).
  * json-c installs its headers under include/json-c/ but ntopng does
    `#include "json.h"`; hiredis under include/hiredis/ with `#include <hiredis.h>`.
    The pkg-config wrapper files must expose both the include root and the
    sub-directory (json-c.pc / hiredis.pc Cflags are augmented in generate()).

Conan packaging layout:
  package_type = "application"; the built `ntopng` binary plus httpdocs/scripts
  (share/ntopng) are installed under self.package_folder (--prefix at configure
  time, then `make install`).
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, chdir, copy
from conan.tools.gnu import AutotoolsToolchain, AutotoolsDeps, PkgConfigDeps
import os
import shutil


def _prepare_autotools_env():
    """The installed automake/aclocal/libtoolize hardcode absolute paths for
    autoconf/autom4te/sed that do not exist in this environment.  Point the
    env vars at whatever is actually on PATH (same workaround as
    abiword-plugin-* recipes)."""
    for tool, var in (("autoconf", "AUTOCONF"),
                      ("autoheader", "AUTOHEADER"),
                      ("autom4te", "AUTOM4TE"),
                      ("sed", "SED")):
        if os.environ.get(var):
            continue
        path = shutil.which(tool)
        if path:
            os.environ[var] = path


class NtopngConan(ConanFile):
    name = "ntopng"
    version = "6.6"
    description = "High-speed web-based network traffic analysis (ntop.org)"
    license = "GPL-3.0"
    homepage = "https://github.com/ntop/ntopng"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "with_hiredis": [True, False]}
    default_options = {"shared": False, "with_hiredis": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Published on remote ohpcd (verified by W3 L0i via conan download
        # from the ohpcd registry).
        # nDPI and libmaxminddb are NOT on ohpcd and therefore are NOT listed here
        # (L0i would fail); they are built from official source inside build() (R49).
        self.requires("json-c/0.18")
        self.requires("openssl/3.5.6.1")
        self.requires("sqlite3/3.49.1")
        self.requires("libpcap/1.10.6")
        if self.options.with_hiredis:
            self.requires("hiredis/1.2.0")
        self.requires("curl/8.15.0")
        self.requires("zeromq/4.3.5")

    def build_requirements(self):
        # ntopng's own autogen.sh regenerates `configure` from configure.ac.in
        # and requires autoconf + automake + (libtool|libtoolize) + autoreconf
        # + pkg-config.  The CI sandbox (minimal OHOS image) only ships the
        # autoconf suite under /data/service/hnp/bin — automake / libtoolize
        # are missing, so `sh autogen.sh` aborts before configure is created.
        # Pull them in as tool_requires (same approach as abiword-plugin-* /
        # argp-standalone).  Resolved with the *build* profile.
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def generate(self):
        _prepare_autotools_env()
        deps = PkgConfigDeps(self)
        deps.generate()
        tc = AutotoolsToolchain(self)
        tc.generate()
        ad = AutotoolsDeps(self)
        ad.generate()
        # openssl/zeromq upstream .pc naming may not provide the exact names
        # ntopng's configure.ac requests (libssl, libzmq).  Create the two
        # aliases next to the generated .pc files when the real providers exist.
        self._ensure_pc_aliases()
        # json-c / hiredis headers live in <include>/<subdir> while ntopng does
        # `#include "json.h"` / `#include <hiredis.h>`.  Expose both roots via
        # the generated .pc files (same trick as the buildwork env.sh used).
        self._augment_pc_cflags("json-c.pc", "${includedir}/json-c")
        self._augment_pc_cflags("hiredis.pc", "${includedir}/hiredis")

    # ---------------------------------------------------------------- helpers
    def _ensure_pc_aliases(self):
        pc_dir = self.generators_folder
        if not os.path.isdir(pc_dir):
            return
        try:
            files = os.listdir(pc_dir)
        except OSError:
            return
        for alias, candidates in (("libssl.pc", ("openssl-ssl.pc", "ssl.pc", "openssl.pc")),
                                  ("libzmq.pc", ("zeromq.pc", "libzmq.pc"))):
            if alias in files:
                continue
            for cand in candidates:
                if cand in files:
                    link = os.path.join(pc_dir, alias)
                    if not os.path.lexists(link):
                        try:
                            os.symlink(os.path.join(pc_dir, cand), link)
                        except OSError:
                            copy(self, cand, pc_dir, os.path.join(pc_dir, alias))
                    break

    def _augment_pc_cflags(self, pc_name, extra_include):
        """Best-effort: append `-I<extra_include>` to a generated .pc Cflags."""
        pc_dir = self.generators_folder
        path = os.path.join(pc_dir, pc_name)
        if not os.path.isfile(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as fh:
                text = fh.read()
        except OSError:
            return
        if extra_include in text:
            return
        if "Cflags:" not in text:
            return
        updated = []
        for line in text.splitlines(keepends=True):
            if line.startswith("Cflags:"):
                line = line.rstrip("\n") + " -I\"" + extra_include + "\"\n"
            updated.append(line)
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("".join(updated))
        except OSError:
            pass

    @staticmethod
    def _sed_file(path, old, new):
        with open(path, "r", encoding="utf-8", errors="surrogateescape") as fh:
            data = fh.read()
        if old in data:
            with open(path, "w", encoding="utf-8", errors="surrogateescape") as fh:
                fh.write(data.replace(old, new))
            return True
        return False

    @staticmethod
    def _umask_fix(path):
        # E011: 0700 autoconf temp dirs are not owner-writable on this FS.
        return NtopngConan._sed_file(path, "umask 077", "umask 002")

    @staticmethod
    def _rewrite_lines(path, predicate, newline):
        """Rewrite whole lines matching predicate to a fixed replacement."""
        with open(path, "r", encoding="utf-8", errors="surrogateescape") as fh:
            lines = fh.readlines()
        out = []
        changed = False
        for ln in lines:
            if predicate(ln):
                out.append(newline)
                changed = True
            else:
                out.append(ln)
        if changed:
            with open(path, "w", encoding="utf-8", errors="surrogateescape") as fh:
                fh.writelines(out)
        return changed

    def _neutralize_rrdtool_sources(self):
        """Source-level rrdtool adaptation (replayable; configure regenerated by
        its own autogen.sh afterwards):
          * glib-2.0/libxml-2.0 EX_CHECK_ALL are only required by rrd_graph
            (disabled by the ntopng Makefile rule) -> scope them to that branch.
          * *nroff/*troff are only needed for docs -> AC_MSG_ERROR -> warning.
          * rrd_restore.c needs libxml/parser.h -> drop from src/Makefile.am.
        """
        rrd = os.path.join(self.source_folder, "third-party", "rrdtool-1.4.8")
        cfgac = os.path.join(rrd, "configure.ac")
        mkam = os.path.join(rrd, "src", "Makefile.am")
        # --- configure.ac: guard glib/xml checks with the rrd_graph branch ---
        with open(cfgac, "r", encoding="utf-8", errors="surrogateescape") as fh:
            lines = fh.readlines()
        out = []
        for i, ln in enumerate(lines):
            if ln.startswith("EX_CHECK_ALL(glib-2.0,"):
                out.append("if test $enable_rrd_graph != no; then\n")
                out.append(ln)
            elif ln.startswith("EX_CHECK_ALL(xml2,"):
                out.append(ln)
                out.append("fi\n")
            else:
                out.append(ln)
        with open(cfgac, "w", encoding="utf-8", errors="surrogateescape") as fh:
            fh.writelines(out)
        # --- configure.ac: nroff/troff are docs-only -> warn instead of abort ---
        self._rewrite_lines(
            cfgac,
            lambda l: "AC_MSG_ERROR([I need a copy of *nroff" in l,
            "  AC_MSG_WARN([I need a copy of *nroff to format the documentation])\n")
        self._rewrite_lines(
            cfgac,
            lambda l: "AC_MSG_ERROR([I need a copy of *troff" in l,
            "  AC_MSG_WARN([I need a copy of *troff to format the documentation])\n")
        # --- src/Makefile.am: drop rrd_restore.c (libxml dependency) ---
        with open(mkam, "r", encoding="utf-8", errors="surrogateescape") as fh:
            mk_lines = fh.readlines()
        mk_out = [ln for ln in mk_lines if not ln.strip().startswith("rrd_restore.c")]
        if len(mk_out) != len(mk_lines):
            with open(mkam, "w", encoding="utf-8", errors="surrogateescape") as fh:
                fh.writelines(mk_out)

    def _resolve_c_compiler(self):
        """Return the C compiler from the OHOS profile
        (tools.build:compiler_executables conf), 'clang' fallback.
        R33: never read a bare ${CC} from the shell environment."""
        cc = "clang"
        try:
            exe = self.conf.get("tools.build:compiler_executables", default={})
        except Exception:
            exe = {}
        if isinstance(exe, dict):
            cc = exe.get("c") or cc
        elif isinstance(exe, str):
            import json as _json
            try:
                d = _json.loads(exe)
                if isinstance(d, dict):
                    cc = d.get("c") or cc
            except Exception:
                pass
        return cc

    def _dep_lib_dirs(self):
        """Absolute lib dirs of every conan require.  Used to build an
        LD_LIBRARY_PATH so configure-time conftest executables (which inherit
        the aggregated LIBS and link the shared curl/zmq/json-c ...) can load
        them when configure runs them (same trick as the manual buildwork
        env.sh)."""
        dirs = []
        try:
            items = self.dependencies.items()
        except Exception:
            items = []
        for _name, dep in items:
            try:
                pf = dep.package_folder
                libdirs = dep.cpp_info.libdirs
            except Exception:
                continue
            if not pf:
                continue
            for libdir in (libdirs or ["lib"]):
                p = os.path.join(pf, libdir)
                if os.path.isdir(p) and p not in dirs:
                    dirs.append(p)
        return dirs

    def _neutralize_rrdtool_configure(self, rrd):
        """Patch the checked-in generated rrdtool `configure` so the hard
        glib-2.0/libxml-2.0 EX_CHECK_ALL gate and the docs-only *nroff/*troff
        checks become warnings (rrd_graph is disabled by the ntopng Makefile
        rule and no docs are formatted).  Also applies the E011 umask fix.

        This image has no autopoint, so `autoreconf --install` (rrdtool's own
        autogen.sh) cannot regenerate configure -> we operate directly on the
        generated configure instead (same approach as the 2026-09-05 manual
        buildwork chain)."""
        cfg = os.path.join(rrd, "configure")
        self._umask_fix(cfg)
        for pat in (
                'as_fn_error $? "Please fix the library issues listed above '
                'and try again." "$LINENO" 5',
                'as_fn_error $? "I need a copy of *nroff to format the '
                'documentation" "$LINENO" 5',
                'as_fn_error $? "I need a copy of *troff to format the '
                'documentation" "$LINENO" 5'):
            self._sed_file(cfg, pat, ":")

    def _archive_librrd_th(self, rrd):
        """Build the bundled rrdtool core-library subset ntopng links against
        (rrd_graph/rrd_restore excluded: they require glib/libxml which are not
        present on the image) and place it at src/.libs/librrd_th.a - exactly
        where the top-level Makefile rule expects it, so that rule is skipped
        during the main make.  Same 26-file subset as the manual buildwork
        chain (buildwork/ohc-logs/build-librrd.sh, 2026-09-05, ARCHIVE_OK)."""
        cc = self._resolve_c_compiler()
        obj = os.path.join(rrd, "src", ".libs")
        srcs = ("rrd_create hash_32 rrd_parsetime rrd_hw rrd_hw_math rrd_hw_update "
                "rrd_diff rrd_format rrd_info rrd_error rrd_open rrd_client "
                "rrd_nan_inf rrd_rpncalc rrd_utils rrd_update rrd_version rrd_last "
                "rrd_lastupdate rrd_first rrd_dump rrd_flushcached rrd_fetch "
                "rrd_resize rrd_tune rrd_thread_safe")
        flags = ("-O2 -fPIC -pthread -DHAVE_CONFIG_H -D_GNU_SOURCE "
                 "-DNUMVERS=1.4008 -I%s -I%s/src" % (rrd, rrd))
        cmd = ("mkdir -p %(obj)s && cd %(rrd)s/src && "
               "for s in %(srcs)s; do %(cc)s -c %(flags)s $s.c -o %(obj)s/$s.o || exit 1; done && "
               "ar rcs %(obj)s/librrd_th.a %(obj)s/*.o"
               % {"obj": obj, "rrd": rrd, "srcs": srcs, "cc": cc, "flags": flags})
        self.run(cmd, env="conanbuild")

    # ------------------------------------------------------------- conan steps
    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _build_private_ndpi(self, prefix, jobs):
        """Build nDPI 5.0 from official source into a private prefix (R49)."""
        src = os.path.join(self.build_folder, "_priv-src", "ndpi")
        get(self, **{"url": self.conan_data["ndpi"]["url"],
                     "sha256": self.conan_data["ndpi"]["sha256"]},
            destination=src, strip_root=True)
        with chdir(self, src):
            self.run("sh autogen.sh", env="conanbuild")
            # E011 on the freshly generated configure
            self._umask_fix(os.path.join(src, "configure"))
            # config.guess cannot identify HarmonyOS (uname -s=HarmonyOS /
            # HongMeng Kernel) and its tmp-dir probe fails on this FS, so pass
            # the triplet explicitly (same as the bundled rrdtool configure).
            conf = ("env -u LIBS CPPFLAGS= LDFLAGS= ./configure --prefix=%s "
                    "--build=aarch64-unknown-linux-gnu "
                    "--with-only-libndpi --disable-shared --enable-static --with-pic"
                    % prefix)
            self.run(conf, env="conanbuild")
            self.run("make -j%d" % jobs, env="conanbuild")
            self.run("make install", env="conanbuild")

    def _build_private_libmaxminddb(self, prefix, jobs):
        """Build libmaxminddb 1.11.0 (CMake) into a private prefix (R49)."""
        src = os.path.join(self.build_folder, "_priv-src", "libmaxminddb")
        get(self, **{"url": self.conan_data["libmaxminddb"]["url"],
                     "sha256": self.conan_data["libmaxminddb"]["sha256"]},
            destination=src, strip_root=True)
        with chdir(self, src):
            self.run("cmake -S . -B build -DCMAKE_SYSTEM_NAME=Linux "
                     "-DCMAKE_INSTALL_PREFIX=%s "
                     "-DCMAKE_BUILD_TYPE=%s -DBUILD_TESTING=OFF -DBUILD_SHARED_LIBS=OFF"
                     % (prefix, self.settings.build_type), env="conanbuild")
            self.run("cmake --build build -j%d" % jobs, env="conanbuild")
            self.run("cmake --install build", env="conanbuild")
        # The generated libmaxminddb.pc carries RELATIVE libdir/includedir
        # ("lib"/"include"), so pkg-config yields "-Llib -Iinclude" which are
        # meaningless relative to the ntopng build dir.  Normalize them to the
        # absolute private prefix so ntopng configure computes usable
        # MAXMINDDB_CFLAGS/MAXMINDDB_LIBS.
        pc = os.path.join(prefix, "lib", "pkgconfig", "libmaxminddb.pc")
        if os.path.isfile(pc):
            with open(pc, "r", encoding="utf-8") as fh:
                lines = fh.readlines()
            fixed = False
            for i, ln in enumerate(lines):
                if ln.startswith("libdir=") and not ln.strip().endswith("/lib"):
                    lines[i] = "libdir=%s/lib\n" % prefix
                    fixed = True
                elif ln.startswith("includedir=") and not ln.strip().endswith("/include"):
                    lines[i] = "includedir=%s/include\n" % prefix
                    fixed = True
            if fixed:
                with open(pc, "w", encoding="utf-8") as fh:
                    fh.writelines(lines)

    def build(self):
        jobs = 8  # -j8 validated on this FS for ntopng (notes 2026-09-06).
        apply_conandata_patches(self)

        # 0) bundled rrdtool.  The image has no autopoint, so rrdtool's own
        #    autogen.sh (autoreconf --install) cannot run; instead patch the
        #    checked-in generated configure (neutralize glib/xml/nroff/troff
        #    hard aborts + E011 umask), run configure once to emit rrd_config.h
        #    and the Makefiles, then archive the core librrd subset
        #    (rrd_graph/rrd_restore excluded) to src/.libs/librrd_th.a so the
        #    top-level ntopng make rule for the bundled rrdtool is skipped.
        rrd = os.path.join(self.source_folder, "third-party", "rrdtool-1.4.8")
        self._neutralize_rrdtool_sources()
        self._neutralize_rrdtool_configure(rrd)
        with chdir(self, rrd):
            # rrdtool is a self-contained bundled sub-build: run configure with
            # the aggregated conan LIBS/CPPFLAGS/LDFLAGS cleared so configure
            # conftest executables do not link/run the conan shared deps.
            self.run("env -u LIBS CPPFLAGS= LDFLAGS= ./configure "
                     "--build=aarch64-unknown-linux-gnu --disable-shared "
                     "--disable-libdbi --disable-libwrap --disable-rrdcgi "
                     "--disable-libtool-lock --disable-nls --disable-rpath "
                     "--disable-perl --disable-ruby --disable-lua --disable-tcl "
                     "--disable-python --disable-dependency-tracking --disable-rrd_graph",
                     env="conanbuild")
        self._archive_librrd_th(rrd)

        # 1) regenerate ntopng configure from configure.ac.in
        with chdir(self, self.source_folder):
            self.run("sh autogen.sh", env="conanbuild")
            # 2) E011: worker FS cannot write into mode-0700 autoconf temp dirs
            self._umask_fix(os.path.join(self.source_folder, "configure"))

        # 3) nDPI 5.0 + libmaxminddb into a private prefix (not on remote ohpcd)
        priv = os.path.join(self.build_folder, "priv")
        self._build_private_ndpi(priv, jobs)
        self._build_private_libmaxminddb(priv, jobs)

        # 4) configure ntopng against conan deps + private prefix.
        #    conanbuild env provides CC/CXX/CPPFLAGS/LDFLAGS/PKG_CONFIG_PATH for
        #    the conan requires; prepend the private pkgconfig dir on top.
        #    LD_LIBRARY_PATH is extended with the require lib dirs so configure
        #    conftest executables (which link the shared curl/zmq/json-c ...)
        #    can run (same as the manual buildwork env.sh).
        #    --prefix points at a build-local staging dir; make install fills it
        #    and package() copies it into the conan package_folder.
        priv_pc = os.path.join(priv, "lib", "pkgconfig")
        stage = os.path.join(self.build_folder, "stage")
        ld_dirs = ":".join(self._dep_lib_dirs())
        cfg = ("LD_LIBRARY_PATH=\"%s:$LD_LIBRARY_PATH\" "
               "PKG_CONFIG_PATH=\"%s:$PKG_CONFIG_PATH\" ./configure "
               "--build=aarch64-unknown-linux-gnu "
               "--prefix=%s "
               "--with-ndpi-static-lib=%s/lib "
               "--with-ndpi-includes=%s/include/ndpi" % (
                   ld_dirs, priv_pc, stage, priv, priv))
        if not self.options.with_hiredis:
            cfg += " --without-hiredis"
        with chdir(self, self.source_folder):
            self.run(cfg, env="conanbuild")
            self.run("make -j%d CC=clang CXX=clang++" % jobs, env="conanbuild")
            self.run("make install", env="conanbuild")

    def package(self):
        # Copy the staged make-install tree (bin/ntopng, share/ntopng,
        # man pages) into the conan package_folder.
        stage = os.path.join(self.build_folder, "stage")
        if os.path.isdir(stage):
            for root, _dirs, files in os.walk(stage):
                rel = os.path.relpath(root, stage)
                dst = os.path.join(self.package_folder, rel)
                for f in files:
                    copy(self, f, root, dst)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
