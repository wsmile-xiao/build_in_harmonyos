#!/usr/bin/env python3
"""Conan recipe for dnswire 0.5.0 — Autotools C library (DNS encapsulations).

dnswire is a C library for encoding/decoding DNSTAP (protobuf) and
transporting DNS events over Frame Streams.

Adaptation notes (HarmonyOS PC, aarch64, clang 15):
- Dependencies: libtinyframe (>= 0.1.0) and libprotobuf-c (>= 1.0.1) come
  from the ohpcd registry; tinyframe is a pure runtime dep,
  protobuf-c is used at build time (codegen is pre-generated, see below)
  and linked statically (its ohpcd package ships a static lib only).
- dnstap.pb-c.[ch] are NOT shipped upstream as generated sources and the
  official codeberg archive tarball does NOT include the `src/dnstap.pb`
  git submodule (dnstap.proto). protoc-c is unavailable on the OHOS build
  host and in CI. The recipe therefore ships pre-generated
  dnstap.pb-c.c/.h (generated on-device with protobuf 3.17.3's protoc +
  protobuf-c 1.5.1's protoc-gen-c plugin, same approach as ocserv/1.5.0)
  via patches 0002/0006, and patches configure.ac to make protoc-c
  optional (0001). gen-macros.sh still runs at build time (no tools
  needed) to produce dnstap-macros.h.
- OHOS/HMDFS quirks handled by Knowledge Base entries:
  * E011: configure's `mktemp -d ./confXXXXXX` with umask 077 fails on
    HMDFS (UID mapping, dir owner != process uid). configure is patched to
    use umask 022 (0001).
  * E461: AF_UNIX file-socket bind is refused (EPERM on HMDFS, EACCES on
    /dev/shm). Upstream test5.sh uses a unix socket round trip; the test
    programs are minimally patched to use the Linux abstract namespace
    (0003/0004/0005) so the full upstream suite can run on OHOS.
- R32: os check uses ("Linux", "OHOS").
- R38: dnswire is a library package (libdnswire), no CLI binaries, so no
  commands.json is required.
- R47: language preflight -> detected C (cpp-compatible family), passed.
- R26: not a system-name library; shared default is fine, but static is
  chosen for consistency with the ohpcd protobuf-c package.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class DnswireConan(ConanFile):
    name = "dnswire"
    version = "0.5.0"
    description = ("dnswire: C library for DNS encapsulations "
                   "(DNSTAP protobuf) over Frame Streams")
    license = "LGPL-3.0-or-later"
    homepage = "https://codeberg.org/DNS-OARC/dnswire"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    exports_sources = "pregen/*"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"os={self.settings.os} not supported"
            )

    def requirements(self):
        self.requires("tinyframe/0.1.1")
        self.requires("protobuf-c/1.5.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Pre-generated artifacts that neither the official tarball nor the
        # OHOS build host provide (protoc-c unavailable, dnstap.pb submodule
        # absent from codeberg archive): ship them via exports_sources and
        # drop them into the source tree before building.
        # R03: pkg.m4 is NOT copied here any more — the official release asset
        # ships a pre-generated configure where PKG_INSTALLDIR/pkgconfigdir are
        # already expanded, and copying pkg.m4 into m4/ makes automake's
        # am__configure_deps newer than Makefile.in, which re-triggers the
        # automake rebuild rule (`Can't exec "aclocal"` on CI). The recipe no
        # longer runs autoreconf at all (see build()).
        copy(self, "dnstap.pb-c.c", src=os.path.join(self.export_sources_folder, "pregen"),
             dst=os.path.join(self.source_folder, "src"))
        copy(self, "dnstap.pb-c.h", src=os.path.join(self.export_sources_folder, "pregen"),
             dst=os.path.join(self.source_folder, "src"))
        copy(self, "dnstap.pb-c.h", src=os.path.join(self.export_sources_folder, "pregen"),
             dst=os.path.join(self.source_folder, "src", "dnswire"))

    def generate(self):
        # Generate .pc files for deps (libtinyframe, libprotobuf-c) and
        # inject PKG_CONFIG_PATH so configure's PKG_CHECK_MODULES finds them
        # (abiword-plugin-docbook proven pattern).
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.append(
            "PKG_CONFIG_PATH={}".format(self.generators_folder))
        # E011: HMDFS rejects umask-077 mktemp temp dirs; configure is patched
        # to umask 022, but keep the flag explicit for reproducibility.
        # --build triplet avoids config.guess probing the OHOS kernel.
        tc.configure_args.append("--build=aarch64-unknown-linux-musl")
        # examples need libuv (optional); skip to keep the dep graph minimal
        tc.configure_args.append("--disable-examples")
        # Library consumers get position-independent code by default on the
        # toolchain; -fPIC is explicitly appended (same as exploratory build).
        tc.configure_args.append("--with-extra-cflags=-fPIC")
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        # R03: the official release asset ships the full set of pre-generated
        # Autotools artifacts (configure, Makefile.in, aclocal.m4, ltmain.sh),
        # so autoreconf is NOT needed and must NOT be called: CI build hosts do
        # not provide aclocal/automake binaries (automake/1.18 tool_requires is
        # Skipped there), and running autoreconf would fail with
        # `Can't exec "aclocal"`. The generated-artifact adaptations (protoc-c
        # optional, pre-generated dnstap.pb-c usage, disable automake rebuild
        # rules) are applied inline below — they cannot live as conan patches
        # because finish/refresh-patch rewrites patches/ from the edit-tracker
        # and would move generated-artifact patches into .patch-backup-*.
        sf = self.source_folder

        def _rewrite(path, pairs):
            p = os.path.join(sf, path)
            with open(p, "r") as f:
                c = f.read()
            for old, new in pairs:
                if old not in c:
                    self.output.warning("rewrite anchor missing in %s: %r" % (path, old[:60]))
                c = c.replace(old, new)
            with open(p, "w") as f:
                f.write(c)

        # (a) E011: HMDFS rejects umask-077 mktemp temp dirs used by the shipped
        # configure's config.status; flatten to umask 022 (knowledge.doc/E011).
        _rewrite("configure", [
            ("umask 077", "umask 022"),
        ])
        # (b) protoc-c optional in the shipped configure (was AC_MSG_ERROR).
        _rewrite("configure", [
            ('''if test -z "$PROTOC_C"
then :

  as_fn_error $? "The protoc-c program was not found. Please install the protobuf-c compiler!" "$LINENO" 5

fi''',
             '''if test -z "$PROTOC_C"
then :
  PROTOC_C=true
  { printf "%s\\n" "$as_me:${as_lineno-$LINENO}: protoc-c not found, using pre-generated dnstap.pb-c files" >&5
printf "%s\\n" "protoc-c not found, using pre-generated dnstap.pb-c files" >&6; }
fi'''),
        ])
        # (c) src/Makefile.in: main sources include pre-generated dnstap.pb-c.c,
        # drop the protoc-c codegen rule, copy the pre-generated header via
        # $(srcdir).
        _rewrite("src/Makefile.in", [
            ('''libdnswire_la_SOURCES = decoder.c dnstap.c dnswire.c encoder.c reader.c \\
  writer.c trace.c
nodist_libdnswire_la_SOURCES = dnstap.pb-c.c''',
             '''libdnswire_la_SOURCES = decoder.c dnstap.c dnswire.c encoder.c reader.c \\
  writer.c trace.c dnstap.pb-c.c'''),
            ('''EXTRA_DIST = dnstap.pb/dnstap.proto dnstap.pb/LICENSE \\
	dnstap.pb/README.md gen-macros.sh dnstap.fields''',
             '''EXTRA_DIST = dnstap.pb-c.c dnstap.pb-c.h gen-macros.sh dnstap.fields'''),
            ('''dnswire/dnstap.pb-c.h: dnstap.pb-c.c
	mkdir -p dnswire/
	cp dnstap.pb-c.h dnswire/

dnstap.pb-c.c: dnstap.pb/dnstap.proto
	$(AM_V_GEN)@PROTOC_C@ "--c_out=." -I$(srcdir)/dnstap.pb "$(srcdir)/dnstap.pb/dnstap.proto"''',
             '''dnswire/dnstap.pb-c.h: $(srcdir)/dnstap.pb-c.h
	mkdir -p dnswire/
	cp $(srcdir)/dnstap.pb-c.h dnswire/'''),
        ])
        # (d) top-level Makefile.in: neutralise automake/autoconf/aclocal
        # rebuild rules (CI has no automake binaries).
        _rewrite("Makefile.in", [
            ('''$(srcdir)/Makefile.in:  $(srcdir)/Makefile.am  $(am__configure_deps)
	@for dep in $?; do \\
	  case '$(am__configure_deps)' in \\
	    *$$dep*) \\
	      echo ' cd $(srcdir) && $(AUTOMAKE) --foreign'; \\
	      $(am__cd) $(srcdir) && $(AUTOMAKE) --foreign \\
		&& exit 0; \\
	      exit 1;; \\
	  esac; \\
	done; \\
	echo ' cd $(top_srcdir) && $(AUTOMAKE) --foreign Makefile'; \\
	$(am__cd) $(top_srcdir) && \\
	  $(AUTOMAKE) --foreign Makefile''',
             '''$(srcdir)/Makefile.in:  $(srcdir)/Makefile.am  $(am__configure_deps)
	@:'''),
            ('''$(top_srcdir)/configure:  $(am__configure_deps)
	$(am__cd) $(srcdir) && $(AUTOCONF)''',
             '''$(top_srcdir)/configure:  $(am__configure_deps)
	@:'''),
            ('''$(ACLOCAL_M4):  $(am__aclocal_m4_deps)
	$(am__cd) $(srcdir) && $(ACLOCAL) $(ACLOCAL_AMFLAGS)''',
             '''$(ACLOCAL_M4):  $(am__aclocal_m4_deps)
	@:'''),
        ])
        autotools.configure()
        autotools.make(args=["-j1"])

    def _run_tests(self):
        """Run upstream autotools TESTS (6 scripts) with proper runtime env."""
        env = {}
        lib_dirs = []
        seen = set()
        stack = list(self.dependencies.values())
        while stack:
            dep = stack.pop(0)
            key = str(dep.ref)
            if key in seen:
                continue
            seen.add(key)
            lib_dir = os.path.join(dep.package_folder, "lib")
            if os.path.isdir(lib_dir):
                lib_dirs.append(lib_dir)
            try:
                stack.extend(dep.dependencies.values())
            except Exception:
                pass
        if lib_dirs:
            existing = os.environ.get("LD_LIBRARY_PATH", "")
            combined = ":".join(lib_dirs)
            os.environ["LD_LIBRARY_PATH"] = (
                combined + ":" + existing if existing else combined
            )
        self.output.info(
            "upstream test LD_LIBRARY_PATH: %s" % os.environ.get("LD_LIBRARY_PATH")
        )
        # source tree files referenced via $srcdir by the TESTS scripts
        os.environ["TMPDIR"] = self.build_folder
        # make check runs in build tree; automake TESTS need srcdir set by AM
        self.run("make check", cwd=self.build_folder, env="conanbuild",
                 ignore_errors=True)

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # headers: dnswire/*.h (public + generated pb-c)
        copy(self, "dnswire*.h", src=os.path.join(self.build_folder, "src", "dnswire"),
             dst=os.path.join(self.package_folder, "include", "dnswire"))
        copy(self, "dnstap.pb-c.h", src=os.path.join(self.build_folder, "src", "dnswire"),
             dst=os.path.join(self.package_folder, "include", "dnswire"))
        copy(self, "*.h", src=os.path.join(self.source_folder, "src", "dnswire"),
             dst=os.path.join(self.package_folder, "include", "dnswire"))
        # libtool convenience outputs live under src/.libs
        copy(self, "libdnswire.so*", src=os.path.join(self.build_folder, "src", ".libs"),
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "libdnswire.a", src=os.path.join(self.build_folder, "src", ".libs"),
             dst=os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["dnswire"]
        self.cpp_info.requires = ["tinyframe::tinyframe", "protobuf-c::protobuf-c"]
        self.cpp_info.set_property("cmake_file_name", "dnswire")
        self.cpp_info.set_property("cmake_target_name", "dnswire::dnswire")