#!/usr/bin/env python3
"""Conan recipe for trousers 0.3.15 — the TCG Software Stack (TSS) 1.2.

Upstream ships an autotools project without a generated ``configure`` (the
release tarball only carries ``configure.ac``/``Makefile.am``), no test suite,
and a hard OpenSSL dependency: ``src/trspi/crypto/openssl`` implements the
hash/RSA/symmetric primitives and configure requires libcrypto's
``EVP_DigestUpdate``.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class TrousersConan(ConanFile):
    name = "trousers"
    version = "0.3.15"
    description = "TCG Software Stack (TSS) 1.2: libtspi, the tcsd daemon and the TSS tools"
    license = "BSD-3-Clause"
    homepage = "https://trousers.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("trousers is supported only on Linux/OHOS")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def requirements(self):
        self.requires("openssl/3.5.6.1")

    def build_requirements(self):
        # The release tarball has no generated configure; the worker ships a
        # working autoconf 2.72 but neither automake/libtoolize nor aclocal.
        # autoconf is deliberately *not* taken from the registry: its shipped
        # scripts hard-code the registry perl's absolute shebang, whose XS
        # modules do not load on this platform (Perl_my_cxt_init), while the
        # worker's own autoconf runs fine under the system perl.
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")
        # configure.ac calls PKG_CHECK_MODULES (pkg.m4 must be on aclocal's path)
        self.tool_requires("pkg-config/0.29.2")

    def layout(self):
        basic_layout(self)
        # trousers builds in-source: config.h and the generated Makefiles live
        # next to the sources and src/*/Makefile.am extend CFLAGS in place.
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--with-gui=none")   # no GTK2 password popup
        if self.settings.os == "OHOS":
            # AC_CANONICAL_TARGET based project: declare the triple explicitly so
            # configure does not try to run freshly linked conftest binaries
            # (HarmonyOS only executes signed binaries).
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-gnu",
            ])
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--disable-shared", "--enable-static"])
        tc.generate()
        AutotoolsDeps(self).generate()
        # aclocal has to find pkg.m4 (pkg-config) and libtool.m4
        for dep in self.dependencies.build.values():
            for sub in ("share/aclocal", "share/aclocal-1.18"):
                path = os.path.join(dep.package_folder, sub)
                if os.path.isdir(path):
                    self.buildenv_info.append_path("ACLOCAL_PATH", path)
        VirtualBuildEnv(self).generate()

    def build(self):
        apply_conandata_patches(self)
        # HMDFS: the ephemeral Conan build directory cannot always be used as a
        # process working directory (getcwd() fails there), so pin the logical
        # path for the shell builtin.
        os.environ["PWD"] = self.build_folder
        # No configure in the release tarball; autoreconf also orders
        # aclocal/libtoolize correctly (bootstrap.sh runs them in the wrong
        # order for a clean tree).
        #
        # Everything runs under the worker's system perl (5.42.0): PERL5LIB is
        # narrowed to automake's own module directory so the system perl cannot
        # pick up the registry perl package's 5.42.2 XS modules, which fail to
        # relocate there ("Cwd.so: Perl_my_cxt_init: symbol not found").
        self.run('PERL5LIB="%s" autoreconf -fi' % self._automake_share(),
                 env="conanbuild")
        self._patch_generated_configure()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()
        self._audit_upstream_tests()

    def _patch_generated_configure(self):
        """HMDFS fixes for the freshly generated configure script.

        The script is produced by autoreconf inside build(), so these two
        edits cannot live in conandata patches:
          * autoconf's strict ``pwd`` check aborts when getcwd() fails even
            though the shell has a working directory -> fall back to $PWD;
          * the config.status scratch directory is created with umask 077,
            which HMDFS cannot write (new directories get the setgid bit).
        """
        path = os.path.join(self.build_folder, "configure")
        with open(path, encoding="utf-8", errors="replace") as handle:
            text = handle.read()
        original = text
        text = text.replace(
            'ac_pwd=`pwd` && test -n "$ac_pwd" &&',
            'ac_pwd=`pwd` 2>/dev/null || ac_pwd=$PWD\ntest -n "$ac_pwd" &&')
        text = text.replace(
            'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
            'tmp=`(umask 022 && mktemp -d "./confXXXXXX") 2>/dev/null`')
        text = text.replace(
            'tmp=./conf$$-$RANDOM\n  (umask 077 && mkdir "$tmp")',
            'tmp=./conf$$-$RANDOM\n  (umask 022 && mkdir "$tmp")')
        if text != original:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(text)
    def _automake_share(self):
        """Directory holding automake's pure-perl modules."""
        for dep in self.dependencies.build.values():
            share = os.path.join(dep.package_folder, "share")
            if not os.path.isdir(share):
                continue
            for name in sorted(os.listdir(share)):
                if name.startswith("automake-"):
                    return os.path.join(share, name)
        return ""

    def _audit_upstream_tests(self):
        # No Makefile.am registers check_PROGRAMS/TESTS: the *_selftest.c files
        # are compiled into the libraries and only run against a live TPM.
        # Record the audit in the build log (R51 declares N=0).
        self.run("grep -nE 'check_PROGRAMS|^TESTS|check-local|^check:' Makefile.am "
                 "src/Makefile.am src/*/Makefile.am src/*/*/Makefile.am || true")
        self.run("find . -maxdepth 3 -iname '*test*' | head || true")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # Drop the libtool wrappers: they contain build-machine paths.
        for name in os.listdir(os.path.join(self.package_folder, "lib")):
            if name.endswith(".la"):
                os.remove(os.path.join(self.package_folder, "lib", name))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["tspi"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin", "sbin"]
