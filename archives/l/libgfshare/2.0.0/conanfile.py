#!/usr/bin/env python3
"""Conan recipe — libgfshare 2.0.0 (autotools).

libgfshare is an implementation of Shamir Secret Sharing over GF(2^8) by
Daniel Silverstone.  It builds a small C library (libgfshare) plus two CLI
tools (gfsplit / gfcombine) for splitting and recombining files.

Upstream: https://github.com/kinnison/libgfshare  (tag 2.0.0)

OHOS adaptations:
  - The 2.0.0 tag ships NO release dist tarball — the official source is the
    GitHub git-archive snapshot, which contains only configure.ac / Makefile.am
    (no `configure`, no `config.sub`, no `Makefile.in`, no
    `libgfshare_tables.h`).  build() therefore runs `autoreconf -fi` to
    bootstrap the autotools machinery from source.
  - Toolchain: autoreconf/autoconf are provided by the build environment;
    automake/aclocal are supplied explicitly by tool_requires automake/1.18,
    and GNU m4 is supplied by tool_requires m4/1.4.19.  The automake package
    propagates PATH, PERL5LIB and ACLOCAL_PATH for consistent local/CI use.
  - automake/1.18 and libtool/2.5.4.1 propagate their build environment
    through Conan; GNU M4 is pointed explicitly at the m4/1.4.19 package
    binary (autom4te honours the $M4 environment variable).
  - --build/--host are passed explicitly as aarch64-unknown-linux-ohos so
    configure never runs the config.guess probe (uname -s = "HarmonyOS" is
    unknown to older config.guess; automake 1.18 provides a config.sub that recognises
    *-linux-ohos after autoreconf copies it in).  Because build == host this is
    a *native* build, so gfshare_maketable (an `noinst_PROGRAMS` build helper
    that emits libgfshare_tables.h at make time) is compiled with the OHOS
    clang and run directly on the OHOS host — no build/host split is needed.
  - E114: the generated configure's config.status creates its temp dir with
    `umask 077`; on HMDFS the resulting setgid 0700 dir is unwritable, so the
    `umask 077` is stripped at build time.
  - E074: make runs with -j1 (HMDFS forbids the make jobserver fifo).
  - make check runs the upstream test suite (2 C tests + 1 shell integration
    test) — see test_package/MANIFEST.yml for the L1 declaration.
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


def _set_autotools_env(self):
    """Set GNU m4 for autoreconf.

    automake/1.18 and libtool/2.5.4.1 are Conan tool requirements and
    propagate their own PATH, PERL5LIB, ACLOCAL_PATH, AUTOMAKE, ACLOCAL,
    LIBTOOLIZE and libtool macro paths through the conan build environment.
    Do not derive PERL5LIB from system Automake, because mixing system Automake
    Perl modules with the Conan Automake executable causes version
mismatch.

    autom4te needs GNU m4, so M4 is pointed explicitly at m4/1.4.19.
    """
    m4_dep = self.dependencies.build.get("m4")
    if m4_dep and m4_dep.package_folder:
        m4bin = os.path.join(m4_dep.package_folder, "bin", "m4")
        if os.path.isfile(m4bin):
            os.environ["M4"] = m4bin
            self.output.info("M4 = %s" % m4bin)


def _drop_umask_077(conanfile, path):
    """E114: HMDFS forces setgid on directories; `umask 077 && mktemp -d`
    creates a drwx--S--- temp dir that is not writable even by its owner.
    Remove `umask 077` (and the now-orphaned parentheses) so config.status
    can create its temp dir.  No-op if the generated configure does not
    contain that pattern."""
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()
    data = data.replace(
        'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
        'tmp=`mktemp -d "./confXXXXXX" 2>/dev/null`')
    data = data.replace('(umask 077 && mkdir "$tmp")', 'mkdir "$tmp"')
    with open(path, "w", encoding="utf-8") as f:
        f.write(data)


class LibgfshareConan(ConanFile):
    name = "libgfshare"
    version = "2.0.0"
    description = "Implementation of Shamir Secret Sharing in GF(2^8)"
    license = "MIT"
    homepage = "https://github.com/kinnison/libgfshare"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libgfshare is pure C depending only on libc (random()/malloc).
        pass

    def build_requirements(self):
        # autoreconf is provided by the build environment, while aclocal /
        # automake must be available explicitly on CI.  Use the repository
        # automake package so PATH/PERL5LIB/ACLOCAL_PATH are propagated
        # consistently to the build environment.
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4.1")
        self.tool_requires("m4/1.4.19")

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libgfshare is only supported on Linux/OHOS, not "
                + str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        _set_autotools_env(self)
        tc = AutotoolsToolchain(self)
        # libgfshare is not a system-name library (no collision with a system
        # lib), so R26 does not force static; default_options keeps shared
        # False for simplicity.  Pass the triplet explicitly so configure
        # never runs the config.guess probe (uname -s = "HarmonyOS").
        # build == host → native build: gfshare_maketable runs on the host.
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        _set_autotools_env(self)
        # The git archive ships no `configure`: generate one from
        # configure.ac (run in the source folder).
        self.run("autoreconf -fi", cwd=self.source_folder, env="conanbuild")
        # E114: drop umask 077 from the generated configure (HMDFS).
        _drop_umask_077(self, os.path.join(self.source_folder, "configure"))
        autotools = Autotools(self)
        autotools.configure()
        # E074: parallel make hits HMDFS jobserver fifo EPERM.
        autotools.make(args=["-j1"])
        # L1: run the upstream test suite (2 C tests + 1 shell test).
        autotools.make(target="check", args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # Remove libtool *.la wrappers (kept out of the package per repo
        # convention).
        for _la in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(_la)

    def package_info(self):
        self.cpp_info.libs = ["gfshare"]
        self.cpp_info.includedirs = ["include"]
        # gfsplit / gfcombine CLI tools ship in bin/ (R38: commands.json
        # declared at the software level).
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "libgfshare")
        self.cpp_info.set_property("cmake_target_name", "libgfshare::libgfshare")
        self.cpp_info.set_property("pkg_config_name", "libgfshare")
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin"))
