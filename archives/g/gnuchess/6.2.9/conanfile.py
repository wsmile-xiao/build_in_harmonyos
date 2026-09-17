#!/usr/bin/env python3
"""Conan recipe for GNU Chess 6.2.9 — chess engine + UCI/XBoard wrappers.

Adaptation notes (HarmonyOS PC / OHOS aarch64):
  - E011/E114: HMDFS turns the `umask 077 && mktemp -d` temp dir created by
    the generated configure into an unwritable drwx--S--- dir; drop
    `umask 077` before configure runs (opendmarc 1.4.2 / ekg2 0.3.1
    precedent).
  - config.sub (autoconf 2.69, 2015) predates OHOS, so configure is invoked
    with --build only and never --host with an ohos triplet (GLM-19 pit #1);
    the OHOS clang reaches the build through the conanbuild environment.
  - The optional readline frontend probes `AC_CHECK_LIB(ncurses, tputs)`,
    but the conan ncurses package ships wide-char libraries only
    (libncursesw.a), so the hardcoded `-lncurses` probe can never pass;
    readline is disabled with --without-readline. Engine behaviour is
    unaffected — readline only provides interactive line editing.
  - Upstream has no automated test suite (no tests/ directory and no
    TESTS/check_PROGRAMS/dejagnu registration in any Makefile.am,
    N_static=0); the consumer test drives the real engine instead.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import AutotoolsToolchain

TOOLS = ["gnuchess", "gnuchessu", "gnuchessx"]


def _drop_umask_077(path):
    """E011/E114: HMDFS forces setgid on directories; `umask 077 && mktemp -d`
    creates a temp dir (drwx--S---) that the current process cannot write.
    Remove `umask 077` (and the now-orphaned parentheses) so config.status
    can create its ./confXXXXXX temp dir."""
    if not os.path.exists(path):
        return
    data = open(path, "r", encoding="utf-8", errors="replace").read()
    data = data.replace(
        'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&',
        'tmp=`mktemp -d "./confXXXXXX" 2>/dev/null` &&')
    data = data.replace(
        '(umask 077 && mkdir "$tmp")',
        'mkdir "$tmp"')
    open(path, "w", encoding="utf-8").write(data)


def _patch_ohos_gaps(src):
    """OHOS musl exposes no pthread_cancel(); components.cc:174-175 uses it
    to stop the stdin reader at quit. Replace cancel+join with a detach —
    the input thread exits on EOF/quit, and process exit reclaims the rest."""
    path = os.path.join(src, "src", "components.cc")
    if not os.path.exists(path):
        return
    data = open(path, "r", encoding="utf-8", errors="replace").read()
    data = data.replace(
        "  pthread_cancel( input_thread );\n"
        "  pthread_join( input_thread, NULL );",
        "  /* OHOS: musl-based libc exposes no pthread_cancel(); the stdin\n"
        "     reader thread exits on EOF/quit and is reclaimed at exit. */\n"
        "  pthread_detach( input_thread );")
    open(path, "w", encoding="utf-8").write(data)


class GnuchessConan(ConanFile):
    name = "gnuchess"
    version = "6.2.9"
    description = "GNU Chess: chess engine with UCI/XBoard wrapper scripts"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/chess/"
    url = "https://ftp.gnu.org/gnu/chess/gnuchess-6.2.9.tar.gz"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "gnuchess is supported only on Linux/OHOS")

    def configure(self):
        # 2015-era engine code uses the `register` keyword, which C++17
        # removed; drop the profile's cppstd=17 so clang 15 falls back to
        # its default (gnu++14, where register only warns).
        del self.settings.compiler.cppstd

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def generate(self):
        # Environment only: build() invokes configure manually with --build
        # pinned, so the toolchain's generated --host args never apply; what
        # matters is the conanbuild env it emits (CC/PATH to the OHOS clang).
        AutotoolsToolchain(self).generate()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # E011/E114: HMDFS temp-dir permission workaround
        _drop_umask_077(os.path.join(self.source_folder, "configure"))
        # OHOS musl has no pthread_cancel
        _patch_ohos_gaps(self.source_folder)
        # config.sub (2015) does not know OHOS: pin --build only, never pass
        # --host with an ohos triplet; CC/CXX come from the conanbuild env.
        self.run('sh ./configure --build=aarch64-unknown-linux-gnu '
                 f'--prefix="{self.package_folder}" && make -j1',
                 cwd=self.source_folder)

    def package(self):
        # bin_PROGRAMS/bin_SCRIPTS both live in src/ (src/Makefile.am);
        # ship the engine binary and the two wrapper scripts like dominion.
        for tool in TOOLS:
            copy(self, tool, src=os.path.join(self.source_folder, "src"),
                 dst=os.path.join(self.package_folder, "bin"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
