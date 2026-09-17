#!/usr/bin/env python3
"""Conan recipe — libuninameslist 0.3.20130501 (Autotools).

libuninameslist is a C library providing direct access to the Unicode
NamesList.txt annotation data: uniNamesList_name() returns the official
character name (e.g. "GREEK SMALL LETTER LAMBDA") and uniNamesList_annot()
returns the annotations block (aliases, cross references, ...).  It is part
of the fontforge ecosystem (fontforge links it for glyph-name lookups) and
is usable by any font/text tool that needs Unicode character metadata.

Upstream facts (audited 2026-09-15, tag 0.3.20130501):
  - tag archive libuninameslist-0.3.20130501.tar.gz (SHA256 bd16f553…)
    ships configure.ac + Makefile.am + m4/ but NO generated `configure`;
    the recipe bootstraps with `autoreconf -fi` in the source root.
  - pure C, zero third-party dependencies (libc only: the generated
    nameslist.c is a static const data table + binary-search lookup).
  - default build produces the main libuninameslist.{a,so}; the optional
    libuninameslist-fr (old French annotations, --enable-oldfrenchlib)
    is NOT enabled — DISTCHECK itself keeps it off by default and the
    main library is what fontforge consumes.
  - Makefile.am registers no TESTS / check_PROGRAMS / check-local:
    upstream `make check` is a zero-test audit target (recorded in
    test_package/MANIFEST.yml); consumer validation lives in
    test_package/.
  - license: the library data is Unicode Terms of Use (nameslist.c
    header) — recorded as "Unicode-TOU" with the upstream COPYING
    (GPL-2.0-or-later for the build tooling) noted in notes.md.

OHOS adaptations (0 source patches — all runtime, same strategy as
libantlr3c/3.5.3):
  - E007/E514: pass --build/--host=aarch64-unknown-linux-ohos so
    configure never runs the config.guess probe; the conan automake
    tool_require's config.sub accepts *-linux-ohos, and the explicit
    triplets make the 2013-vintage shipped scripts irrelevant.
  - E114: drop `umask 077` from the generated configure (HMDFS setgid
    turns the 0700 temp dir into an unwritable dir).
  - E074: `make -j1` (HMDFS jobserver fifo EPERM).
  - E443: autoreconf execs aclocal/automake/autoconf/... by bare name;
    automake/libtool come in as tool_requires so the closure is complete
    (autoconf itself is on the CI worker PATH via the SDK).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


def _drop_umask_077(path):
    """E114: HMDFS forces setgid on directories; `umask 077 && mktemp -d`
    creates a drwx--S--- temp dir that is not writable even by its owner.
    Remove `umask 077` (and the now-orphaned parentheses) so config.status
    can create its temp dir."""
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()
    data = data.replace(
        'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
        'tmp=`mktemp -d "./confXXXXXX" 2>/dev/null`')
    data = data.replace('(umask 077 && mkdir "$tmp")', 'mkdir "$tmp"')
    with open(path, "w", encoding="utf-8") as f:
        f.write(data)


class LibuninameslistConan(ConanFile):
    name = "libuninameslist"
    version = "0.3.20130501"
    description = (
        "Unicode character names and annotations library "
        "(NamesList.txt data with uniNamesList_name/annot lookup)"
    )
    license = "Unicode-TOU"
    homepage = "https://github.com/fontforge/libuninameslist"
    url = ""  # CI fills this

    package_type = "library"
    languages = "C"
    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
    }

    implements = ["auto_shared_fpic"]

    def configure(self):
        # pure C library: drop the C++ settings so they don't force a
        # libc++ ABI split this library never uses.
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libuninameslist is only supported on Linux/OHOS, not "
                + str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        # R3: patches (if any) are declared in conandata.yml — this
        # release ships 0 patches; the call stays so the pipeline holds.
        export_conandata_patches(self)

    def build_requirements(self):
        # The tag archive ships configure.ac/Makefile.am but no generated
        # `configure`: the recipe bootstraps with `autoreconf -fi`, which
        # execs the whole autotools closure (aclocal/automake/autoconf/
        # autoheader/autom4te/libtoolize) by bare name.  automake and
        # libtool are provided as tool_requires so the closure is complete
        # regardless of what the build host has on its base PATH (same
        # split as libantlr3c/libdap: autoconf itself comes from the SDK).
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # VirtualBuildEnv: inject profile [buildenv] PATH + tool_requires
        # (automake/libtool) bindirs into conanbuild so the autotools
        # closure is resolvable from the effective build environment.
        build_env = VirtualBuildEnv(self)
        build_env.generate()
        tc = AutotoolsToolchain(self)
        # E007/E514: the 2013-vintage config.guess cannot identify
        # HarmonyOS and its config.sub rejects *-linux-ohos.  Pin both
        # triplets explicitly so the probe never runs; the automake
        # tool_require's modern config.sub accepts *-linux-ohos.
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        # static/shared is driven by libtool via --enable-shared/
        # --disable-shared, which AutotoolsToolchain derives from
        # options.shared automatically.
        tc.generate()

    def build(self):
        # Apply patches declared in conandata.yml (R3; 0 for this release).
        apply_conandata_patches(self)
        # E443: apply the Conan build environment first — VirtualBuildEnv
        # merges profile [buildenv] PATH + tool_requires bindirs + base
        # PATH, so autoreconf can exec aclocal/automake/libtoolize.
        build_env = VirtualBuildEnv(self).vars()
        with build_env.apply():
            # The tag archive ships no `configure`: generate it from
            # configure.ac (run in source folder, in-source bootstrap).
            self.run("autoreconf -f -i", cwd=self.source_folder)
        # E114: drop umask 077 from the generated configure (HMDFS)
        _drop_umask_077(os.path.join(self.source_folder, "configure"))
        autotools = Autotools(self)
        autotools.configure()
        # E074: HMDFS jobserver fifo EPERM
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # libtool installs .la/.a even for shared builds; keep the tree
        # tidy by leaving them (conan convention keeps .a alongside).

    def package_info(self):
        self.cpp_info.libs = ["uninameslist"]
        self.cpp_info.set_property("pkg_config_name", "libuninameslist")
