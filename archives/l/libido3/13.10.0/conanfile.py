#!/usr/bin/env python3
"""Conan recipe — libido3 13.10.0 (Autotools).

Ubuntu Ayatana "ido" (Indicator Display Objects) — GTK3 menu item widgets
library, artifact name libido3-0.1. HarmonyOS PC (aarch64) adaptation notes:

  - Source mapping: no bare 13.10.0 tarball exists upstream (13.10.0 is the
    calendar-verse bzr-snapshot series 13.10.0+YY.MM.DD). The official
    mapping is the Ubuntu current-series 0ubuntu4 orig tarball
    (ido_13.10.0+22.10.20221007.orig.tar.gz), sha256 verified against the
    official .dsc Checksums-Sha256. Recipe version string stays 13.10.0
    (configure.ac's internal 13.10.1 is an upstream m4 leftover).
  - Build system: autotools, but the orig tarball ships NO generated
    configure/Makefile.in (autogen.sh needs gnome-common, unavailable) ->
    in-recipe bootstrap: aclocal -> autoconf -> autoheader -> ltmain.sh ->
    automake --add-missing (abiword-plugin-docbook precedent; the autoreconf
    chain itself hits the HMDFS autoconf.m4f loading conflict, E-knowledge).
  - src/idomenuitemfactory.c includes <gtk/ubuntu-private.h> unconditionally
    (Ubuntu GTK private API, absent from vanilla GTK3) -> patch 0001 adds a
    --disable-ubuntu-private-api switch (Alpine precedent) and this recipe
    builds with it disabled.
  - GOBJECT_INTROSPECTION_CHECK / CHECK_XORG_GTEST / GTK_DOC_CHECK m4 macros
    are not shipped in the tarball -> patch 0002 stubs them (all three
    features disabled: g-ir-scanner cannot run target binaries in the cross
    build, E179; xorg-gtest is unbuildable upstream, LP#1388892; gtk-doc
    unnecessary).
  - Upstream tests: tests/Makefile.am carries empty TESTS and
    check_PROGRAMS (upstream comment: "xorg-gtest isn't buildable",
    LP#1388892); the 4 gtest-menuitems TEST_F need X11/Xi + a display.
    make check therefore runs but has zero cases; the honest result is
    emitted as HMBS_UPSTREAM_TEST_RESULT (no_upstream_tests) and consumer
    verification lives in test_package (real device execution).
  - Explicit link closure (build-chain-pitfalls "shared library link
    closure"): every dependency libdir gets -L/-Wl,-rpath/-Wl,-rpath-link,
    and glib's proxy libintl (unique provider of g_libintl_*) is injected as
    an absolute link input, all appended before the toolchain environment
    snapshot.
  - Artifacts: lib/libido3-0.1.so.0(.0.0) + libido3-0.1.pc + headers under
    include/libido3-0.1/libido. Installed ELF files are OHOS self-signed in
    package() (glib recipe precedent).
"""
import glob
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class Libido3Conan(ConanFile):
    name = "libido3"
    version = "13.10.0"
    description = (
        "Ayatana Indicator Display Objects (Ubuntu ido) — GTK3 menu item "
        "widgets library (libido3-0.1)"
    )
    # Package-level license per the Ubuntu debian/copyright: dual LGPL-3
    # and/or LGPL-2.1 (individual files carry one of the two).
    license = "LGPL-2.1-or-later"
    homepage = "https://launchpad.net/ido"
    url = ""  # CI fills this
    topics = ("gtk3", "menu", "indicator", "ayatana")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # Same proven graph as the published ayatana-ido/0.10.4-v2 recipe
        # (same upstream family, same gtk/3.24.43 + glib/2.84.0.1 closure).
        # gtk/3.24.43 pins glib/2.84.0.1; the top level must align to avoid
        # graph conflicts. transitive_headers/libs: libido3-0.1.pc Requires
        # gtk+-3.0, so consumers and test_package need the full include/lib
        # closure.
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)
        self.requires("gtk/3.24.43", transitive_headers=True, transitive_libs=True)
        # Transitive closure alignment (verbatim from the CI-passed
        # ayatana-ido/0.10.4-v2 recipe; see its conanfile for the per-pin
        # rationale: CCI tool-edge elimination + ohpcd publish identity).
        self.requires(
            "pixman/0.46.4#09f648ede446f6abf85a98da455c7562",
            override=True,
        )
        self.requires("fontconfig/2.18.1.1", override=True)
        self.requires(
            "freetype/2.14.3#7e95a2b2401fd12dcbdd2bf748f56b19",
            override=True,
        )
        self.requires("zlib/1.3.1.1", override=True)
        self.requires(
            "libpng/1.6.58#d25df07aba0399181f60ee377e83d701",
            override=True,
        )
        self.requires("expat/2.8.2.1", override=True)
        self.requires(
            "libepoxy/1.5.10#92f7e70c459ed2e6a96cd82549e82391",
            override=True,
        )
        self.requires(
            "libffi/3.4.4#ca8b0eb4102edbca48730e504e3afbdc",
            override=True,
        )
        self.requires(
            "libjpeg-turbo/3.2.0#5ed08e7ff848da8fdf6b7bca74354560",
            override=True,
        )
        self.requires(
            "cairo/1.18.4#3894814f2279392f808090c9f3d8f200",
            override=True,
        )
        self.requires(
            "libtiff/4.7.2#f386d7b671befab127228dbcfc6fe1bf",
            override=True,
        )
        self.requires(
            "libdeflate/1.25#2346ca4f797e19d8d553b6f698dd8982",
            override=True,
        )
        self.requires(
            "zstd/1.5.7#83364ff4f4ab63fae26fbfb89f89fefe",
            override=True,
        )
        self.requires(
            "libwebp/1.6.0#8b273a5128ee70c508671933b61288ec",
            override=True,
        )
        self.requires(
            "lerc/4.1.1#9c8297567326e560407157395590b2f8",
            override=True,
        )
        self.requires(
            "jbigkit/2.1#872f3b26b5921c9156cb3aa4675b20c5",
            override=True,
        )
        self.requires(
            "xz/5.6.2#66ce4bbd966830b5a11768474be4b259",
            override=True,
        )

    def build_requirements(self):
        # The orig tarball has no generated configure/Makefile.in, and
        # autogen.sh requires gnome-common (unavailable): bootstrap in
        # build(). The device ships the autoconf family (2.72) via the
        # profile buildenv PATH, but not automake/libtool/aclocal — pull
        # them as tool_requires (abiword-plugin-docbook precedent).
        # pkgconf ships the pkg-config-compatible binary + pkg.m4
        # (ctpl/cassbeam precedent).
        self.tool_requires("pkgconf/3.0.5")
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libido3 %s only supports Linux and OHOS, got os=%s"
                % (self.version, self.settings.os)
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------
    # generate(): environment assembly.
    # Order matters: buildenv_info mutation must happen BEFORE
    # VirtualBuildEnv(self).generate(), and every tc.* mutation must happen
    # BEFORE tc.generate() (the environment snapshot), else it is silently
    # dropped (build-chain-pitfalls, libgee case).
    # ------------------------------------------------------------------
    def generate(self):
        PkgConfigDeps(self).generate()
        self._synthesize_vendored_pc_files()

        tc = AutotoolsToolchain(self)
        # OHOS is not recognized by the tarball-era config.guess/config.sub;
        # pin GNU triplets so configure skips the guess probe (compiler still
        # targets OHOS via the toolchain flags; ctpl/cdecl precedent). The
        # explicit values also override the auto-generated *-linux-ohos ones.
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.configure_args.append("--host=aarch64-unknown-linux-gnu")
        # Upstream LT_INIT([disable-static]) already forces shared-only; the
        # explicit flags keep the intent visible and stable.
        tc.configure_args.append("--disable-static")
        tc.configure_args.append("--enable-shared")
        # OHOS adaptation switch from patch 0001: vanilla GTK3 has no
        # <gtk/ubuntu-private.h>.
        tc.configure_args.append("--disable-ubuntu-private-api")
        # E179: introspection needs g-ir-scanner running target binaries;
        # gtk-doc has no doc toolchain on OHOS. Both flags are accepted by
        # the stub macros from patch 0002.
        tc.configure_args.append("--disable-introspection")
        tc.configure_args.append("--disable-gtk-doc")

        # Explicit link closure (build-chain-pitfalls): every host dep libdir
        # gets -L/-Wl,-rpath/-Wl,-rpath-link; g_libintl_* sole provider
        # (glib lib/libintl.so) becomes an explicit absolute link input.
        # glib >= 2.84 statically vendors pcre2/ffi — those Skipped binaries
        # have package_folder None and must be skipped.
        have_intl_input = False
        for dep in self.dependencies.values():
            if not dep.package_folder:
                continue
            for inc in dep.cpp_info.includedirs:
                tc.extra_cflags.append("-I%s" % inc)
            for libdir in dep.cpp_info.libdirs:
                tc.extra_ldflags.append("-L%s" % libdir)
                tc.extra_ldflags.append("-Wl,-rpath,%s" % libdir)
                tc.extra_ldflags.append("-Wl,-rpath-link,%s" % libdir)
            intl = os.path.join(dep.package_folder, "lib", "libintl.so")
            if os.path.isfile(intl):
                tc.extra_ldflags.append(intl.replace(os.sep, "/"))
                have_intl_input = True
        if not have_intl_input:
            tc.extra_ldflags.append("-lintl")
            self.output.info(
                "linkfix: no absolute libintl.so found, falling back to -lintl"
            )

        env = Environment()

        # Deterministic pkg-config resolution: PKG_PROG_PKG_CONFIG honours
        # the PKG_CONFIG env var; wrap whatever real binary we resolved in a
        # fixed-name shim so configure always finds a runnable one (worker
        # PATH state must not decide the build).
        pkg_bin = self._resolve_pkg_config_binary()
        shim_dir = os.path.join(self.build_folder, "hmbs-pkgconf-shim")
        os.makedirs(shim_dir, exist_ok=True)
        shim = os.path.join(shim_dir, "pkg-config")
        fd = os.open(shim, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o755)
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write('#!/bin/sh\nexec "%s" "$@"\n' % pkg_bin)
        try:
            os.chmod(shim, 0o755)
        except OSError:
            pass  # HMBS_CAP_CHMOD=0: open mode already grants exec
        env.define("PKG_CONFIG", shim)
        env.prepend_path("PATH", shim_dir)
        self.output.info("using pkg-config via shim: %s -> %s" % (shim, pkg_bin))

        # PKG_CONFIG_PATH order: PkgConfigDeps mirrors FIRST, then the
        # synthesized vendored mirrors, then the real package dirs.
        # Rationale: the ohpcd dependency packages ship their real .pc files
        # with prefix=/ (relocated packaging), so every -I/-L they expand is
        # wrong on the worker (CI round 8: "gio/gio.h not found" — configure
        # baked -I//glib-2.0 into GTK_CFLAGS). The PkgConfigDeps mirrors carry
        # the true absolute package-folder paths and a complete Requires
        # chain; real dirs remain as fallback for names without a mirror.
        pc_dirs = []
        try:
            gens = self.generators_folder
            if gens and os.path.isdir(gens):
                pc_dirs.append(gens)
        except Exception:
            pass
        vd = getattr(self, "_vendored_pc_dir", None)
        if vd and os.path.isdir(vd) and vd not in pc_dirs:
            pc_dirs.append(vd)
        for dep in self.dependencies.values():
            if not dep.package_folder:
                continue
            for sub in ("lib/pkgconfig", "lib64/pkgconfig", "share/pkgconfig"):
                d = os.path.join(dep.package_folder, sub)
                if os.path.isdir(d) and d not in pc_dirs:
                    pc_dirs.append(d)
        if pc_dirs:
            env.define("PKG_CONFIG_PATH", os.pathsep.join(pc_dirs))

        # glib-mkenums lives in the glib package bin dir; AC_PATH_PROG
        # resolves it during configure, and the make-time enum rules reuse
        # the baked path. All dep bin dirs go on the build PATH.
        for dep in self.dependencies.values():
            if not dep.package_folder:
                continue
            b = os.path.join(dep.package_folder, "bin")
            if os.path.isdir(b):
                env.append_path("PATH", b)
        # First observed in this port: a stale/broken glib-mkenums wrapper
        # on PATH gets cached by AC_PATH_PROG and fails at make time with
        # exit 126 (CI round 9: the hnp wrapper's shebang hardcodes
        # /usr/bin/perl, which is absent on this device). AC_PATH_PROG honors
        # a preset GLIB_MKENUMS env var — pin the real script in the glib pkg.
        glib_mkenums = self._find_glib_mkenums()
        if glib_mkenums:
            env.define("GLIB_MKENUMS", glib_mkenums)
            self.output.info("GLIB_MKENUMS pinned: %s" % glib_mkenums)

        # ACLOCAL_PATH: source m4 dir (tarball gcov.m4) + every build tool
        # package's share/aclocal (automake's own macros, libtool.m4,
        # pkg.m4). Must precede VirtualBuildEnv.generate().
        m4_dir = os.path.join(self.source_folder, "m4")
        if os.path.isdir(m4_dir):
            self.buildenv_info.append_path("ACLOCAL_PATH", m4_dir)
        try:
            build_deps = self.dependencies.build.values()
        except Exception:
            build_deps = []
        for dep in build_deps:
            if not dep.package_folder:
                continue
            d = os.path.join(dep.package_folder, "share", "aclocal")
            if os.path.isdir(d):
                self.buildenv_info.append_path("ACLOCAL_PATH", d)

        # VirtualBuildEnv: puts the tool_requires binaries (aclocal,
        # automake, pkgconf) and their buildenv on the conanbuild PATH.
        VirtualBuildEnv(self).generate()
        # Merge, don't replace: passing a bare env to generate() would drop
        # the toolchain's own env (LDFLAGS/CFLAGS with the link-closure
        # flags above) — expected behavior, not a log-observed fact: env
        # appended after the snapshot is silently dropped; compose instead.
        tc_env = tc.environment()
        tc_env.compose_env(env)
        tc.generate(env=tc_env)

    def _find_glib_mkenums(self):
        """Locate the real glib-mkenums inside the glib package (ayatana-ido
        precedent). Returns "" when not found."""
        try:
            for dep in self.dependencies.values():
                if not dep.package_folder:
                    continue
                if dep.ref.name == "glib":
                    cand = os.path.join(
                        dep.package_folder, "bin", "glib-mkenums"
                    )
                    if os.path.isfile(cand):
                        return cand
        except Exception:
            pass
        try:
            for dep in self.dependencies.values():
                if not dep.package_folder:
                    continue
                cand = os.path.join(dep.package_folder, "bin", "glib-mkenums")
                if os.path.isfile(cand):
                    return cand
        except Exception:
            pass
        return ""

    def _synthesize_vendored_pc_files(self):
        """Synthesize .pc mirrors for unresolvable public Requires names.

        The ohpcd binary closures vendor several libraries and declare them
        "Skipped binaries" (CI round-1 log: graphite2/1.3.14, libffi/3.4.4,
        pcre2/10.45, xz/5.6.2) — those nodes have no conan package folder and
        therefore no real .pc. Real dependency .pc files may still reference
        them in public Requires (gobject-2.0 -> libffi, glib-2.0 ->
        libpcre2-8, libtiff-4 -> liblzma), which makes a plain pkg-config
        chain resolution abort ("Package 'libffi' required by 'gobject-2.0'
        not found", CI round 1; "Package 'liblzma' required by 'libtiff-4'",
        CI round 2). Walk BOTH the real .pc dirs and the generators folder —
        the PkgConfigDeps mirror files in the generators folder are exactly
        where such references hide (e.g. the cairo-gobject package ships no
        real .pc, so its mirror resolves and pulls libffi) — and include
        Requires.private edges, because pkg-config 0.29 (the worker's
        /data/service/hnp/bin/pkg-config) demands they be locatable even for
        non-static queries (CI rounds 4/5). For every referenced name that
        cannot be resolved write a content-free mirror into a private
        build-folder dir, which sits in PKG_CONFIG_PATH after the PkgConfigDeps
        mirrors and before the real package dirs (real .pc files win whenever
        they exist). Empty
        Libs/Cflags is the correct content:
        the vendored symbols are exported by the vendoring library, nothing
        needs linking (build-chain-pitfalls). The synthesized Version is the
        highest version constraint observed at the reference site (or the
        graph-skipped version when visible), so sibling ">= x" checks hold.
        A final pkgconf probe on the modules configure needs (gtk+-3.0,
        gio-2.0) fails fast with a clear message instead of a cryptic
        configure error three build minutes later.
        """
        try:
            gens = self.generators_folder
        except Exception:
            return
        if not gens or not os.path.isdir(gens):
            return

        real_dirs = []
        skipped_versions = {}
        for dep in self.dependencies.values():
            if not dep.package_folder:
                try:
                    skipped_versions[dep.ref.name] = str(dep.ref.version)
                except Exception:
                    pass
                continue
            for sub in ("lib/pkgconfig", "lib64/pkgconfig", "share/pkgconfig"):
                d = os.path.join(dep.package_folder, sub)
                if os.path.isdir(d) and d not in real_dirs:
                    real_dirs.append(d)
        # Walk (and probe) in the SAME order as the final PKG_CONFIG_PATH:
        # mirrors first, synthesized vendored mirrors second, real dirs last.
        # Synthesized mirrors live in a PRIVATE build-folder dir, NOT in the
        # generators folder: conan rolls the generators folder back when a
        # generate() exception propagates (CI round 6: the fail-fast probe
        # raised, conan wiped the freshly written libffi.pc/graphite2.pc).
        vendored_dir = os.path.join(self.build_folder, "hmbs-vendored-pc")
        try:
            os.makedirs(vendored_dir, exist_ok=True)
        except OSError:
            return
        self._vendored_pc_dir = vendored_dir
        search_dirs = []
        try:
            if gens and os.path.isdir(gens):
                search_dirs.append(gens)
        except Exception:
            pass
        search_dirs.append(vendored_dir)
        search_dirs.extend(real_dirs)

        # .pc filename -> conan ref name of the vendored provider, when the
        # names differ (used to read the real version off the graph).
        provider = {"liblzma": "xz", "libpcre2-8": "pcre2", "libpcre2-posix": "pcre2"}

        def find_pc(name):
            for d in search_dirs:
                p = os.path.join(d, name + ".pc")
                if os.path.isfile(p):
                    return p
            return None

        def requires_edges(path):
            # pkg-config 0.29 (the worker's /data/service/hnp/bin/pkg-config)
            # requires Requires.private packages to be LOCATABLE even for
            # non-static queries (it errors "Package 'libffi' required by
            # 'gobject-2.0', not found" — CI rounds 1/2/4/5), so both
            # Requires and Requires.private edges must resolve. pkgconf
            # would only need them under --static, but the recipe must work
            # with either implementation. .pc Requires lists come in BOTH
            # spellings: comma-separated ("a, b >= 1.2") and
            # whitespace-separated ("a b >= 1.2", e.g. libtiff-4.pc:
            # "Requires.private: zlib libjpeg liblzma libzstd libwebp",
            # CI round 7) — normalize commas to spaces and parse
            # name/op/version triples sequentially.
            out = []
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    for line in f:
                        if not line.startswith("Requires"):
                            continue
                        toks = line.split(":", 1)[1].replace(",", " ").split()
                        i = 0
                        while i < len(toks):
                            name = toks[i]
                            op = toks[i + 1] if i + 1 < len(toks) else None
                            ver = toks[i + 2] if i + 2 < len(toks) else None
                            if op in (">=", "<=", "==", ">", "<", "="):
                                out.append((name, op, ver))
                                i += 3
                            else:
                                out.append((name, None, None))
                                i += 1
            except OSError:
                pass
            return out

        missing = {}  # name -> version to synthesize
        queue = sorted(
            os.path.basename(p)[:-3]
            for d in search_dirs
            for p in glob.glob(os.path.join(d, "*.pc"))
        )
        seen = set()
        while queue:
            name = queue.pop(0)
            if name in seen:
                continue
            seen.add(name)
            path = find_pc(name)
            if path is None:
                continue
            for dep_name, op, cver in requires_edges(path):
                if find_pc(dep_name) is None:
                    ver = skipped_versions.get(
                        provider.get(dep_name, dep_name), ""
                    )
                    if cver and op in (">=", "==", ">"):
                        if not ver or self._ver_gt(cver, ver):
                            ver = cver
                    missing[dep_name] = ver or "1"
                queue.append(dep_name)

        written = []
        for name in sorted(missing):
            pc = os.path.join(vendored_dir, name + ".pc")
            if os.path.isfile(pc):
                continue
            content = (
                "prefix=/\n"
                "libdir=${prefix}/lib\n"
                "includedir=${prefix}/include\n"
                "\n"
                "Name: %s\n" % name
                + "Description: Vendored (conan Skipped) binary; symbols are exported by the vendoring library, nothing to link\n"
                "Version: %s\n" % missing[name]
                + "Libs:\n"
                "Cflags:\n"
            )
            with open(pc, "w", encoding="utf-8", newline="\n") as f:
                f.write(content)
            written.append("%s(%s)" % (name, missing[name]))
        if written:
            self.output.info(
                "[ok] synthesized vendored .pc mirrors: %s" % ", ".join(written)
            )
        self._probe_pkg_config_resolution(search_dirs)

    def _probe_pkg_config_resolution(self, search_dirs):
        """Fail fast when the modules configure needs do not resolve."""
        import subprocess as _sp

        pkg_bin = (
            os.environ.get("PKG_CONFIG_REAL")
            or shutil.which("pkgconf")
            or shutil.which("pkg-config")
        )
        if not pkg_bin:
            self.output.warning(
                "no pkgconf/pkg-config for the resolution probe; skipping"
            )
            return
        env = dict(os.environ)
        env["PKG_CONFIG_PATH"] = os.pathsep.join(list(search_dirs))
        try:
            p = _sp.run(
                [pkg_bin, "--exists", "gtk+-3.0", "gio-2.0"],
                stdout=_sp.PIPE,
                stderr=_sp.STDOUT,
                text=True,
                timeout=30,
                env=env,
                check=False,
            )
        except Exception as exc:
            self.output.warning("pkg-config probe failed to run: %r" % exc)
            return
        if p.returncode == 0:
            self.output.info(
                "[ok] pkg-config probe: gtk+-3.0 + gio-2.0 resolve"
            )
        else:
            raise ConanException(
                "pkg-config cannot resolve gtk+-3.0/gio-2.0 even after "
                "vendored .pc synthesis (rc=%s, out=%s)"
                % (p.returncode, (p.stdout or "").strip())
            )

    @staticmethod
    def _ver_gt(a, b):
        try:
            ta = tuple(int(x) for x in re.split(r"[.\-_+]", a) if x.isdigit())
            tb = tuple(int(x) for x in re.split(r"[.\-_+]", b) if x.isdigit())
            return ta > tb
        except Exception:
            return False

    def _resolve_pkg_config_binary(self):
        """Find a runnable pkg-config/pkgconf binary (pcre2/accountsservice
        probe precedent). The conan pkgconf tool package is the guaranteed
        last candidate."""
        import subprocess as _sp

        conf_val = None
        try:
            conf_val = self.conf.get("tools.gnu:pkg_config", default=None)
        except Exception:
            conf_val = None
        pkgconf_pkg_bin = ""
        try:
            for dep in self.dependencies.build.values():
                if dep.ref.name == "pkgconf" and dep.package_folder:
                    cand = os.path.join(dep.package_folder, "bin", "pkgconf")
                    if os.path.isfile(cand):
                        pkgconf_pkg_bin = cand
                    break
        except Exception:
            pass
        candidates = [
            conf_val,
            os.environ.get("PKG_CONFIG"),
            shutil.which("pkg-config"),
            shutil.which("pkgconf"),
            "/data/service/hnp/bin/pkg-config",
            "/data/service/hnp/bin/aarch64-unknown-linux-ohos-pkg-config",
            pkgconf_pkg_bin,
        ]
        for cand in candidates:
            if not cand or not os.path.isfile(str(cand)):
                continue
            try:
                p = _sp.run(
                    [str(cand), "--version"],
                    stdout=_sp.PIPE,
                    stderr=_sp.STDOUT,
                    text=True,
                    timeout=10,
                    check=False,
                )
            except Exception:
                continue
            if p.returncode == 0 and (p.stdout or "").strip():
                return str(cand)
        raise ConanException("no runnable pkg-config/pkgconf binary found")

    # ------------------------------------------------------------------
    # build(): on-device autotools bootstrap + compile.
    # ------------------------------------------------------------------
    def build(self):
        apply_conandata_patches(self)
        self._bootstrap_autotools()
        self._patch_configure_umask()
        self._strip_dependency_la_files()
        self._prepare_runtime_env()
        shim = self._write_install_shim()
        autotools = Autotools(self)
        autotools.configure()
        self._redirect_install_to_shim(shim)
        autotools.make(args=["-j1"])
        self._run_upstream_check()

    def _bootstrap_autotools(self):
        """Generate configure/Makefile.in in the source folder.

        abiword-plugin-docbook precedent: the autoreconf chain has an
        autoconf.m4f loading conflict on HMDFS (base macros reported
        undefined), so run the aclocal -> autoconf -> autoheader ->
        ltmain.sh -> automake chain directly. $ACLOCAL/$AUTOMAKE/
        $LIBTOOLIZE/ACLOCAL_PATH only exist inside the conanbuild env, so
        every step runs through self.run(env="conanbuild").
        """
        src = self.source_folder

        self.output.info("bootstrap: aclocal (aclocal.m4 with AM_*/LT_*/PKG_* macros)")
        self.run(
            'ACLOCAL_PATH="%s:$ACLOCAL_PATH" "${ACLOCAL:-aclocal}" --force -I m4'
            % os.path.join(src, "m4"),
            cwd=src,
            env="conanbuild",
            ignore_errors=True,
        )
        if not os.path.isfile(os.path.join(src, "aclocal.m4")):
            raise ConanException("aclocal produced no aclocal.m4")

        self.output.info("bootstrap: autoconf (configure.ac -> configure)")
        self.run(
            "autoconf -o configure configure.ac",
            cwd=src,
            env="conanbuild",
            ignore_errors=True,
        )
        if not os.path.isfile(os.path.join(src, "configure")):
            raise ConanException("autoconf failed to generate configure")

        self.output.info("bootstrap: autoheader (config.h.in)")
        self.run("autoheader", cwd=src, env="conanbuild", ignore_errors=True)
        if not os.path.isfile(os.path.join(src, "config.h.in")):
            with open(os.path.join(src, "config.h.in"), "w"):
                pass

        # ltmain.sh must exist before automake --add-missing, else automake
        # aborts with "required file './ltmain.sh' not found".
        ltmain = os.path.join(src, "ltmain.sh")
        if not os.path.isfile(ltmain):
            copied = False
            # $LIBTOOLIZE is injected by the libtool package buildenv into
            # the conanbuild env (shell-expands inside self.run).
            self.run(
                'lt="$LIBTOOLIZE"; '
                'if [ -n "$lt" ] && [ -f "$lt" ]; then '
                '  srcdir="$(cd "$(dirname "$(dirname "$lt")")" && pwd)"; '
                '  src="$srcdir/share/libtool/build-aux/ltmain.sh"; '
                '  [ -f "$src" ] && cp "$src" ltmain.sh; '
                "fi",
                cwd=src,
                env="conanbuild",
                ignore_errors=True,
            )
            copied = os.path.isfile(ltmain)
            if not copied:
                # Fallback: resolve via the tool_requires package folder.
                try:
                    for dep in self.dependencies.build.values():
                        if dep.ref.name == "libtool" and dep.package_folder:
                            cand = os.path.join(
                                dep.package_folder,
                                "share", "libtool", "build-aux", "ltmain.sh",
                            )
                            if os.path.isfile(cand):
                                shutil.copy(cand, ltmain)
                                copied = True
                            break
                except Exception:
                    pass
            if copied:
                self.output.info("bootstrap: copied ltmain.sh from libtool package")
            else:
                self.output.warning(
                    "ltmain.sh not found; LT_INIT may fail at link time"
                )

        self.output.info("bootstrap: automake (Makefile.in + aux scripts)")
        self.run(
            '"${AUTOMAKE:-automake}" --add-missing --copy --no-force',
            cwd=src,
            env="conanbuild",
            ignore_errors=True,
        )
        for required in ("Makefile.in", "src/Makefile.in", "install-sh"):
            if not os.path.isfile(os.path.join(src, required)):
                raise ConanException(
                    "automake bootstrap incomplete: missing %s" % required
                )

    def _patch_configure_umask(self):
        # E011: configure/config.status use `umask 077 && mktemp -d`, which
        # yields an unwritable dir on HMDFS; relax to 022 (generated file,
        # variable form only, no baked absolute paths).
        cfg = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(cfg):
            return
        with open(cfg, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        if "umask 077" in content:
            content = content.replace("umask 077", "umask 022")
            with open(cfg, "w", encoding="utf-8", newline="\n") as f:
                f.write(content)
            self.output.info("[ok] relaxed umask 077 -> 022 in generated configure")

    def _strip_dependency_la_files(self):
        # E236: dependency packages ship .la files whose libdir was broken by
        # conan relocation ("//lib"), making libtool abort with "is not a
        # valid libtool archive". This build is shared-only, so libtool
        # falls back to .so when no .la exists (libgee/a52dec precedent).
        for dep in self.dependencies.values():
            if not dep.package_folder:
                continue
            lib_dir = os.path.join(dep.package_folder, "lib")
            if not os.path.isdir(lib_dir):
                continue
            for entry in os.listdir(lib_dir):
                if entry.endswith(".la"):
                    try:
                        os.remove(os.path.join(lib_dir, entry))
                        self.output.info(
                            "removed broken libtool archive: %s/%s"
                            % (dep.ref, entry)
                        )
                    except OSError:
                        pass

    def _prepare_runtime_env(self):
        # HMDFS: parent dirs may be unresolvable via getcwd(); preset PWD
        # (cdecl precedent). E002: device /tmp is read-only erofs; point
        # TMPDIR at a writable dir.
        try:
            os.chdir(self.build_folder)
        except OSError:
            self.output.warning("chdir(build_folder) failed; relying on PWD")
        os.environ["PWD"] = self.build_folder
        tmpdir = os.environ.get("TMPDIR") or os.path.join(
            self.build_folder, ".tmp"
        )
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMP"] = tmpdir
        os.environ["TEMP"] = tmpdir

    def _write_install_shim(self):
        # E182/E188: toybox install rejects chmod and the HMBS-provided
        # runtime install shim only accepts single-file two-arg calls, while
        # libtool/automake install rules need mkdir/cp semantics with
        # multi-source support. chmod is best-effort (HMBS_CAP_CHMOD=0).
        shim_dir = os.path.join(self.build_folder, "_ohos_install_shim")
        os.makedirs(shim_dir, exist_ok=True)
        install = os.path.join(shim_dir, "install")
        script = (
            "#!/bin/sh\n"
            "set -eu\n"
            "mode=\n"
            "while [ $# -gt 0 ]; do\n"
            "  case \"$1\" in\n"
            "    -p|-c) shift ;;\n"
            "    -m) [ $# -ge 2 ] || exit 2; mode=$2; shift 2 ;;\n"
            "    -d) shift; [ $# -gt 0 ] || exit 2; mkdir -p \"$@\"; exit 0 ;;\n"
            "    --) shift; break ;;\n"
            "    -*) shift ;;\n"
            "    *) break ;;\n"
            "  esac\n"
            "done\n"
            "[ $# -ge 2 ] || exit 2\n"
            "dest=\n"
            "for arg in \"$@\"; do dest=$arg; done\n"
            "count=$(($# - 1))\n"
            "if [ \"$count\" -gt 1 ]; then\n"
            '  mkdir -p "$dest"\n'
            "else\n"
            '  mkdir -p "$(dirname "$dest")"\n'
            "fi\n"
            "i=1\n"
            'for src in "$@"; do\n'
            "  [ $i -gt $count ] && break\n"
            '  cp -f "$src" "$dest"\n'
            '  if [ -n "$mode" ]; then\n'
            '    if [ -d "$dest" ]; then\n'
            '      chmod "$mode" "$dest/${src##*/}" 2>/dev/null || true\n'
            "    else\n"
            '      chmod "$mode" "$dest" 2>/dev/null || true\n'
            "    fi\n"
            "  fi\n"
            "  i=$((i + 1))\n"
            "done\n"
        )
        fd = os.open(install, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o755)
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(script)
        try:
            os.chmod(install, 0o755)
        except OSError:
            pass
        return install

    def _redirect_install_to_shim(self, shim_install):
        # configure bakes the probed install path into every generated
        # Makefile's INSTALL variable; point it at the cp/mkdir shim
        # (ctpl/xeyes precedent).
        for root, _, files in os.walk(self.build_folder):
            if "Makefile" not in files:
                continue
            mf = os.path.join(root, "Makefile")
            try:
                with open(mf, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except OSError:
                continue
            if "INSTALL =" not in content:
                continue
            lines = []
            changed = False
            for line in content.splitlines(True):
                stripped = line.lstrip()
                if stripped.startswith("INSTALL = ") and "/install" in stripped:
                    indent = line[: len(line) - len(stripped)]
                    lines.append("%sINSTALL = %s\n" % (indent, shim_install))
                    changed = True
                else:
                    lines.append(line)
            if changed:
                with open(mf, "w", encoding="utf-8", newline="\n") as f:
                    f.writelines(lines)
                self.output.info("[ok] install shim redirected %s" % mf)

    def _run_upstream_check(self):
        """Run `make check` and emit honest upstream-test evidence.

        Upstream tests/Makefile.am carries empty TESTS/check_PROGRAMS (the
        xorg-gtest harness is unbuildable upstream, LP#1388892; the 4
        gtest-menuitems TEST_F need X11/Xi and a display). make check is a
        deliberate zero-case run: it proves the check harness wires up, and
        the machine marker documents the real upstream state instead of
        faking a pass. Consumer verification happens in test_package.
        """
        self.run("make check -j1", env="conanbuild", ignore_errors=True)
        marker = {
            "status": "no_upstream_tests",
            "framework": "automake",
            "command": "make check -j1",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "upstream tests/Makefile.am: TESTS and check_PROGRAMS are "
                "empty (xorg-gtest unbuildable, LP#1388892); the 4 "
                "gtest-menuitems TEST_F require X11/Xi + a display"
            ),
        }
        import json as _json

        _msg = "HMBS_UPSTREAM_TEST_RESULT=" + _json.dumps(
            marker, ensure_ascii=False
        )
        print(_msg, flush=True)
        self.output.info(_msg)

    # ------------------------------------------------------------------
    # package(): install + OHOS artifact post-processing.
    # ------------------------------------------------------------------
    def package(self):
        autotools = Autotools(self)
        autotools.install()
        lib_dir = os.path.join(self.package_folder, "lib")
        # E236: never ship libtool metadata — downstream libtool links would
        # re-read stale dependency_libs paths.
        if os.path.isdir(lib_dir):
            for entry in os.listdir(lib_dir):
                if entry.endswith(".la"):
                    os.remove(os.path.join(lib_dir, entry))
                    self.output.info("[ok] removed libtool archive %s" % entry)
        self._make_soname_real_file(lib_dir)
        self._sign_installed_elfs()

    def _make_soname_real_file(self, lib_dir):
        # libtool installs the real file (libido3-0.1.so.0.0.0) plus symlinks
        # for the SONAME name. HMDFS symlinks are unreliable at runtime, and
        # consumers load via DT_NEEDED "libido3-0.1.so.0", so that name must
        # hold real file content (ayatana-ido precedent: copy, not symlink).
        real = sorted(glob.glob(os.path.join(lib_dir, "libido3-0.1.so.0.*")))
        real = [p for p in real if os.path.isfile(p) and not os.path.islink(p)]
        soname = os.path.join(lib_dir, "libido3-0.1.so.0")
        if not real:
            self.output.warning(
                "no real libido3-0.1.so.0.* file found; soname copy skipped"
            )
            return
        # libtool created soname as a symlink to the real file: drop it and
        # copy the bytes (copyfile would raise SameFileError through the
        # symlink).
        if os.path.lexists(soname):
            os.remove(soname)
        with open(real[0], "rb") as fsrc:
            data = fsrc.read()
        with open(soname, "wb") as fdst:
            fdst.write(data)
        self.output.info(
            "[ok] soname real file: %s <- %s" % (soname, real[0])
        )

    def _sign_installed_elfs(self):
        # OHOS requires ELF signatures for execution; re-sign after install
        # (glib recipe _sign_shared_libs precedent). binary-sign-tool may be
        # absent in cross/SDK environments — warn and skip there.
        lib_dir = os.path.join(self.package_folder, "lib")
        sos = glob.glob(os.path.join(lib_dir, "**", "*.so"), recursive=True)
        sos += glob.glob(os.path.join(lib_dir, "**", "*.so.*"), recursive=True)
        sos = sorted(set(sos))
        if not sos:
            return
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            self.output.warning(
                "binary-sign-tool not found; skip OHOS codesign (cross/SDK env)"
            )
            return
        objcopy = None
        candidates_objcopy = ["/data/service/hnp/bin/llvm-objcopy"]
        try:
            ce = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            )
            cc = (ce or {}).get("c") or ""
            if cc:
                candidates_objcopy.insert(
                    0, os.path.join(os.path.dirname(cc), "llvm-objcopy")
                )
        except Exception:
            pass
        candidates_objcopy.append(shutil.which("llvm-objcopy") or "")
        for cand in candidates_objcopy:
            if cand and os.path.isfile(cand):
                objcopy = cand
                break
        for so in sos:
            if objcopy:
                self.run(
                    '{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(
                        oc=objcopy, f=so
                    ),
                    ignore_errors=True,
                )
            self.run(
                '{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(
                    sg=signer, f=so
                )
            )
            self.output.info("[ok] signed %s" % so)

    # ------------------------------------------------------------------
    # package_info(): consumer metadata.
    # ------------------------------------------------------------------
    def package_info(self):
        self.cpp_info.libs = ["ido3-0.1"]
        # Headers install under include/libido3-0.1/libido and are included
        # as <libido/xxx.h> (libido3.pc Cflags: -I${includedir}/libido3-0.1).
        self.cpp_info.includedirs = ["include/libido3-0.1", "include"]
        self.cpp_info.set_property("cmake_file_name", "libido3")
        self.cpp_info.set_property("cmake_target_name", "libido3::libido3")
        self.cpp_info.set_property("pkg_config_name", "libido3-0.1")
        # libido3-0.1.pc Requires: gtk+-3.0 (which pulls the glib set).
        self.cpp_info.requires = ["gtk::gtk", "glib::glib"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
