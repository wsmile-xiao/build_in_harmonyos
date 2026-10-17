#!/usr/bin/env python3
"""Conan recipe for tgl — the Telegram API / MTProto protocol library.

Upstream (https://github.com/vysheng/tgl at commit ffb04cac) is a 2016 C
library built with autotools.  The release tarball has no install target and
no test suite; the patches add the install rule, hand the TL schema compiler
over to the packaged tl-parser tool, and fix two problems that newer
toolchains expose (OpenSSL 1.1+ opaque RSA, an uninitialized tgl_peer_id_t).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class TglConan(ConanFile):
    name = "tgl"
    version = "2.0.1-git20160323.ffb04cac"
    description = "Telegram API and MTProto protocol library"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/vysheng/tgl"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    # Static only: the shared library upstream also builds cannot be linked
    # here, because the packaged zlib it pulls in is a non-PIC static archive.
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("tgl is supported only on Linux/OHOS")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def requirements(self):
        self.requires("openssl/3.5.6.1")
        self.requires("zlib/1.3.1")
        # tgl only ships its own net/timers when configure runs with
        # --enable-libevent; that is what makes the packaged library usable on
        # its own, and it is how Debian builds it as well.
        self.requires("libevent/2.1.13")

    def build_requirements(self):
        # Upstream compiles tl-parser from a git submodule that the release
        # tarball does not contain; the packaged tool takes its place.
        self.tool_requires("tl-parser/0.0.0-git20210107.1933e76f")

    def layout(self):
        basic_layout(self)
        # tgl builds in-source: configure() writes config.h next to the sources
        # and crypto/*.c include it as "../config.h".
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--enable-libevent")
        # AC_FUNC_MALLOC/AC_FUNC_REALLOC run a probe program to check the
        # malloc(0)/realloc(NULL) contracts.  That probe cannot run here (see
        # patch 0006), and autoconf's fallback would define malloc/realloc as
        # rpl_malloc/rpl_realloc, which the library does not implement.  These
        # are autoconf's own answers for "the libc implementation is fine".
        tc.configure_args.extend([
            "ac_cv_func_malloc_0_nonnull=yes",
            "ac_cv_func_realloc_0_nonnull=yes",
        ])
        tc.generate()
        # tgl locates its dependencies with plain Autoconf checks, so it needs
        # the include/library flags (AutotoolsDeps) and, for the AX_CHECK_OPENSSL
        # probe, an openssl pkg-config file (PkgConfigDeps).
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()
        # Puts the tl-parser tool_requires bin directory on PATH, so that the
        # patched Makefile.tl-parser resolves its default TL_PARSER.
        VirtualBuildEnv(self).generate()

    def _tl_parser(self):
        dep = self.dependencies.build["tl-parser"]
        return os.path.join(dep.package_folder, "bin", "tl-parser")

    def build(self):
        apply_conandata_patches(self)
        # HMDFS: the ephemeral Conan build directory cannot always be used as a
        # process working directory (getcwd() fails there), so pin the logical
        # path for the shell builtin.  Patch 0005 lets configure fall back to
        # it when `pwd` fails.
        os.environ["PWD"] = self.build_folder
        autotools = Autotools(self)
        autotools.configure()
        # make does not only compile: it runs the freshly linked bin/generate,
        # which is itself linked against the shared dependencies.  Layer the
        # Conan run environment (library search paths) over the build one.
        runenv = os.path.join(self.generators_folder, "conanrun.sh")
        self.run('if [ -f "%s" ]; then . "%s"; fi; make -j1 TL_PARSER="%s" LIB_LIST=%s'
                 % (runenv, runenv, self._tl_parser(), self._library()), env="conanbuild")
        self._audit_upstream_tests()

    @staticmethod
    def _library():
        # LIB_LIST is a makefile variable: passing it on the command line keeps
        # `all` (and therefore `install`) away from libs/libtgl.so.
        return "libs/libtgl.a"

    def _audit_upstream_tests(self):
        # Upstream ships no test suite: there is no tests/ directory, no
        # check_PROGRAMS/TESTS in the makefiles and no "check" target.  The
        # audit runs inside the build so the conan create log carries machine
        # evidence for the upstream_test_audit entry in test_package.
        self.run("grep -nE 'check_PROGRAMS|^TESTS|check-local|^check:' "
                 "Makefile.in Makefile.tl-parser || true")
        self.run("find . -maxdepth 2 -iname '*test*' -o -maxdepth 2 -iname '*check*' || true")

    def package(self):
        autotools = Autotools(self)
        # The patched install target ships the static library plus every public
        # header, which is the same file set the Debian package installs.
        autotools.install(args=["LIB_LIST=%s" % self._library()])

    def package_info(self):
        self.cpp_info.libs = ["tgl"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
