#!/usr/bin/env python3
"""Conan recipe — rblcheck 20231210 (upstream release, GPL-2.0-or-later).

rblcheck is a command-line interface to RBL-style (DNSBL) filters: it builds a
reversed-IP (or hashed) query name such as `2.0.0.127.zen.spamhaus.org` and
resolves it through the system resolver to decide whether an address is listed.

It exercises a real networking/A resolver surface on the target platform:
`res_query` (from the resolver), `getaddrinfo`, `getopt_long`, and — when built
with a crypto backend (the upstream default) — OpenSSL/libcrypto for the hashed
DNSBL variants (SHA-1 / base32).

OHOS FINDINGS (both verified on the target)
-------------------------------------------
1. `res_query` **is** available in the OHOS libc — the configure probes
   `checking for res_query... yes` and `checking for getaddrinfo... yes` both
   succeed, and `<resolv.h>` / `<arpa/nameser.h>` are present.  No resolver
   shim is needed.

2. `config.status` **cannot create its temporary directory** on OHOS/HMDFS:

       ./config.status[756]: can't create ./conffA5XBi/subs1.awk: Permission denied
       config.status: error: could not setup config files machinery

   Autoconf's `config.status` creates its scratch directory as
   `(umask 077 && mktemp -d "./confXXXXXX")`, i.e. mode 700.  On the HMDFS mount
   that backs `/storage/Users/currentUser` a 700 directory is **not writable by
   its own owner** — reproduced minimally on the target:

       (umask 077 && mkdir t700)  -> drwx--S---   write into it: Permission denied
       (umask 022 && mkdir t755)  -> drwxr-s--x   write into it: OK

   The generated `configure` is therefore post-processed to relax both
   `umask 077` occurrences to `umask 022` (matching the fix this archive already
   carries for libpipeline).  With that single change configure/make succeed.
   This is a build-time transformation of a file we generate ourselves in the
   same step (`autoreconf --install`), not an edit of upstream content.

Crypto backend: upstream default (`--with-crypto-library=openssl`) is kept, so
hashed-DNSBL support is compiled in; `openssl` is therefore a declared (runtime,
dynamically linked) requirement, not an optional extra.

UPSTREAM TESTS
--------------
`Makefile.am` declares exactly three automake tests:

    TESTS = tests/clearlist tests/addlisting tests/removelisting

They are plain `/bin/sh` scripts that exercise rblcheck's **local** zone-list
machinery (`-c` clear, `-s <zone>` toggle, `-l` list-and-exit) — `-l` exits
before any address is checked, so **none of them touch the network or DNS**.
`build()` runs `make check`, i.e. the complete upstream test set:
`upstream_total = 3`.  Nothing is skipped, filtered or excluded.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, export_conandata_patches, get, replace_in_file, save
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class RblcheckConan(ConanFile):
    name = "rblcheck"
    version = "20231210"
    description = "Command-line interface to RBL-style (DNSBL) filters"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/rfc1036/rblcheck"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # libcrypto is linked into the binary (rblcheck_LDADD = $(CRYPTO_LIBS)), so
    # this is a real runtime dependency, not a build-only one.
    requires = "openssl/3.5.7"

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # The GitHub tag archive ships NO generated `configure` / `Makefile.in` /
        # `aclocal.m4` — upstream's .gitignore explicitly lists them as generated,
        # and `autogen.sh` bootstraps with `autoreconf --install`.  So build() must
        # bootstrap, and the CI worker has autoconf but NOT automake:
        #
        #     Can't exec "aclocal": No such file or directory
        #     autoreconf: error: aclocal failed with exit status: 2
        #
        # Same situation, same fix as afuse/0.5.0 and adcli/0.9.2 in this archive:
        # bring the missing bootstrap tools in as tool_requires (resolved with the
        # BUILD profile, so `conan create` needs both -pr:h and -pr:b).
        self.tool_requires("automake/1.18")
        # configure.ac calls PKG_PROG_PKG_CONFIG / PKG_CHECK_MODULES, so aclocal
        # must find `pkg.m4`.  The conan automake package does NOT ship it (its
        # share/aclocal contains only a README); the conan pkgconf package does.
        self.tool_requires("pkgconf/3.0.6")

    def validate(self):
        # R32: settings.os check must be an explicit allow-list
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"rblcheck supports Linux and OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _shell(self):
        # R5: OHOS has no guaranteed /bin/sh for complex scripts; use CONFIG_SHELL
        # (profile [buildenv]) and fall back to bash.
        return (os.environ.get("CONFIG_SHELL") or shutil.which("bash")
                or "/data/service/hnp/bin/bash")

    def generate(self):
        tc = AutotoolsToolchain(self)
        env = tc.environment()
        # Conan does NOT manage ACLOCAL_PATH (zero references to it anywhere in the
        # conan package), and aclocal only auto-searches its own --print-ac-dir.
        # Without this, `aclocal` (now coming from the tool_requires automake) would
        # not see pkg.m4 and autoreconf would die with
        #     error: possibly undefined macro: PKG_PROG_PKG_CONFIG
        # Expose every tool requirement's share/aclocal directory.
        aclocal_dirs = []
        for dep in self.dependencies.build.values():
            p = os.path.join(dep.package_folder, "share", "aclocal")
            if os.path.isdir(p):
                aclocal_dirs.append(p)
        if aclocal_dirs:
            env.define("ACLOCAL_PATH", os.pathsep.join(aclocal_dirs))
        tc.generate(env)
        # Writes openssl.pc — whose pkg-config *module name* is "openssl".
        PkgConfigDeps(self).generate()
        # configure.ac runs PKG_CHECK_MODULES(crypto, libcrypto), i.e. it asks for
        # a module literally named "libcrypto", which PkgConfigDeps does not emit
        # for this dependency (it emits "openssl").
        #
        # The conan openssl package does ship lib/pkgconfig/libcrypto.pc, but that
        # file is NOT usable: OpenSSL hardcodes an absolute prefix at build time
        # and the conan package does not relocate it.  On this machine the shipped
        # file still says
        #     prefix=/storage/Users/currentUser/.cache/conan2/p/b/opens62ecc5d1e9652/p
        # which does not exist, so pkg-config returns a bogus -I and the compile
        # fails with "openssl/sha.h file not found".
        #
        # Generate a correct libcrypto.pc instead, from the dependency's real
        # cpp_info paths.  PKG_CONFIG_PATH already points at the generators
        # folder, so pkg-config then resolves both "libcrypto" and "openssl".
        dep = self.dependencies["openssl"]
        pkg_root = dep.package_folder
        inc = dep.cpp_info.includedirs[0] if dep.cpp_info.includedirs else "include"
        lib = dep.cpp_info.libdirs[0] if dep.cpp_info.libdirs else "lib"
        inc_abs = inc if os.path.isabs(inc) else os.path.join(pkg_root, inc)
        lib_abs = lib if os.path.isabs(lib) else os.path.join(pkg_root, lib)
        save(self, os.path.join(self.generators_folder, "libcrypto.pc"),
             "# generated by the rblcheck recipe — see conanfile.py generate()\n"
             f"prefix={pkg_root}\n"
             "exec_prefix=${prefix}\n"
             f"libdir={lib_abs}\n"
             f"includedir={inc_abs}\n"
             "\n"
             "Name: OpenSSL-libcrypto\n"
             "Description: OpenSSL cryptography library\n"
             f"Version: {dep.ref.version}\n"
             "Libs: -L${libdir} -lcrypto\n"
             "Cflags: -I${includedir}\n")

    def _relax_config_status_umask(self, src):
        """Make config.status' scratch dir group-accessible (see module docstring).

        Autoconf creates it with `umask 077` (mode 700); on OHOS/HMDFS a 700
        directory is not writable even by its owner, so config.status dies with
        "can't create ./confXXXXXX/subs1.awk: Permission denied".
        """
        cfg = os.path.join(src, "configure")
        if not os.path.isfile(cfg):
            return
        replace_in_file(self, cfg, "umask 077", "umask 022")

    def build(self):
        shell = self._shell()
        # The release tarball ships no pre-generated `configure`.
        self.run(f"{shell} -c 'autoreconf --install'", cwd=self.source_folder)
        self._relax_config_status_umask(self.source_folder)

        autotools = Autotools(self)
        autotools.configure()
        autotools.make()
        # Complete upstream test set: the three automake TESTS scripts.
        autotools.make(target="check")

    def package(self):
        autotools = Autotools(self)
        # `make install` recurses into docs/ (SUBDIRS = docs .), whose
        # `install-data-local: rblcheck.txt` hook generates the manual from
        # rblcheck.sgml with `docbook2txt` (docbook-utils).  That tool does not
        # exist on OHOS, so the stock install target aborts:
        #     /bin/sh: docbook2txt: inaccessible or not found
        #     make[2]: *** [Makefile:428: rblcheck.txt] Error 127
        #
        # Overriding SUBDIRS to "." makes automake run only the local
        # install-am (i.e. install the rblcheck program) and skip the docs
        # recursion.  No binary, header or library is affected; the only thing
        # not installed is the generated DocBook text manual, which this
        # platform cannot produce.  Documented in notes.md.
        #
        # NOTE: Autotools.install() only injects DESTDIR=<package_folder> when
        # `args` is None, so it must be passed explicitly here — otherwise make
        # would install into the real "/bin" (Read-only file system on OHOS).
        autotools.install(args=[f"DESTDIR={self.package_folder}", "SUBDIRS=."])
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # rblcheck is a CLI tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
