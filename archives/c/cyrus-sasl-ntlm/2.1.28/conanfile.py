#!/usr/bin/env python3
"""Conan recipe — cyrus-sasl-ntlm 2.1.28 (Autotools).

NTLM mechanism package for Cyrus SASL on HarmonyOS PC (aarch64).

Same upstream 2.1.28 release tarball as cyrus-sasl, configured for the
NTLM authentication mechanism (plugins/ntlm.c, enabled via --enable-ntlm;
NTLM is derived from SMB/CIFS and implements the LM/NTLM/NTLMv2
challenge-response family). Unlike the other dependency-free members of
this family (LOGIN/PLAIN/ANONYMOUS/CRAM/DIGEST-MD5), ntlm.c needs a
crypto provider for MD4/HMAC-MD5/DES: it is built against OpenSSL 3.x
(--with-openssl=<prefix>, HMAC_*/MD4/DES_* from libcrypto) so the package
declares openssl/3.5.6 as its single Conan dependency.

The library is delivered as a static libsasl2.a (shared=False) with NTLM
in the compile-time mechanism table (upstream STATIC_NTLM), so consumers
need no runtime SASL_PATH/dlopen plugin search — the same shape as
cyrus-sasl-login/2.1.28. Any shared artefact is purged in package().

OHOS notes (cyrus-sasl/2.1.28.3 + cyrus-sasl-login/2.1.28 precedent):
  - configure's config.guess (2018-02-24) does not know the "HarmonyOS"
    uname the platform reports, so configure aborts with "cannot guess
    build type". patches/0001+0002 teach config.guess/config.sub the
    aarch64-unknown-linux-ohos triplet (platform detection, no
    --build/--host override).
  - HMDFS + setgid: autoconf creates ./confXXXXXX under `umask 077`,
    which yields an owner-unwritable directory and config.status then
    dies with "can't create ./conf*/subs1.awk: Permission denied".
    patches/0003 relaxes the generated configure to `umask 022`
    (platform truth: a single-user build filesystem).
  - configure probes the *build* compiler via AC_PROG_CC_FOR_BUILD and
    bare-searches gcc/cc/cl.exe, but OHOS only ships clang, so
    CC_FOR_BUILD/CPP_FOR_BUILD are pinned to clang (native build:
    build == host).
  - TMPDIR is redirected into the build folder: the platform /tmp is
    read-only (E002), which breaks autoconf's mktemp/conftest probes.
  - lib/Makefile symlinks the static mechanism sources into lib/ before
    compiling them; HMDFS does not serve those symlinks to the build, so
    plugins/ntlm.c and sasldb/db_none.c are copied over instead.
  - The upstream tarball ships generated autotools files whose mtimes can
    make make(1) try to re-run aclocal/automake (absent on OHOS); all
    source timestamps are normalised so the shipped files are used.
  - libsasl2.a carries ntlm.o with undefined HMAC_*/MD4_*/DES_* symbols.
    NTLM_LIBS is only used by the shared module plugins/libntlm.la, so
    the other link targets (testsuite/dbconverter-2/pluginviewer) would
    fail with "undefined symbol: HMAC_*". AutotoolsDeps feeds the
    OpenSSL libdir/libs through LIBS, which lands after the objects on
    every automake link line.
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get, rm)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class CyrusSaslNtlmConan(ConanFile):
    name = "cyrus-sasl-ntlm"
    version = "2.1.28"
    description = ("Cyrus SASL NTLM authentication mechanism "
                   "(libsasl2 with NTLM/OpenSSL support)")
    license = "BSD-Attribution-HPND-disclaimer"
    homepage = "https://www.cyrusimap.org/sasl/"
    url = "https://github.com/cyrusimap/cyrus-sasl"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def export_sources(self):
        # Export the patches declared in conandata.yml so that
        # apply_conandata_patches() can find them in the source folder.
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "cyrus-sasl-ntlm is only supported on Linux/OHOS, not %s"
                % self.settings.os
            )

    def requirements(self):
        # ntlm.c computes P16/P21/P24/V2 with MD4 + HMAC-MD5 + DES from
        # libcrypto, so OpenSSL is a hard build and link dependency.
        self.requires("openssl/3.5.6")

    def layout(self):
        basic_layout(self, src_folder=".")
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)
        self._normalize_autotools_timestamps()

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Old codebase: clang 15 promotes implicit-function-declaration /
        # int-conversion to errors; demote to warnings (standard practice
        # for building legacy C, same as cyrus-sasl/2.1.28).
        tc.extra_cflags.append("-Wno-error=implicit-function-declaration")
        tc.extra_cflags.append("-Wno-error=int-conversion")
        tc.configure_args.extend(self._configure_args())
        tc.generate()
        # CPPFLAGS/LDFLAGS/LIBS for openssl; LIBS is what supplies the
        # -lcrypto closure that libsasl2.a's ntlm.o needs (see module
        # docstring). openssl/3.5.6 ships static archives only, so no
        # runtime search path is required.
        AutotoolsDeps(self).generate()

    def build(self):
        self._prepare_ohos_env()
        autotools = Autotools(self)
        autotools.configure()
        # HMDFS does not serve the lib/Makefile `linksrcs` symlinks to the
        # compiler; copy the static mechanism sources instead.
        self._copy_linksrcs_for_ohos(self.source_folder)
        autotools.make(args=["-j1"])

    def package(self):
        self._prepare_ohos_env()
        autotools = Autotools(self)
        autotools.install()
        rm(self, "*.la", self.package_folder, recursive=True)
        if not self.options.shared:
            self._purge_shared_artefacts_for_ohos()
        # Pure library package (R38): upstream installs bin/pluginviewer, a
        # developer-only plugin inspector that is useless without the removed
        # sasldb backend.  It is linked against libsasl2.so.3 (DT_NEEDED,
        # RUNPATH //lib) while a static-only package purges every shared
        # artefact, so the shipped executable cannot load at all - measured on
        # device: "Error loading shared library libsasl2.so.3" / rc=127.
        # Drop bin/ and sbin/ entirely, exactly like cyrus-sasl/2.1.28.3, so
        # the delivered package is a genuine library and needs no
        # commands.json.
        for _exe_dir in ("bin", "sbin"):
            _path = os.path.join(self.package_folder, _exe_dir)
            if os.path.isdir(_path):
                shutil.rmtree(_path, ignore_errors=True)
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["sasl2"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "cyrus-sasl-ntlm")
        self.cpp_info.set_property(
            "cmake_target_name", "cyrus-sasl-ntlm::cyrus-sasl-ntlm")
        self.cpp_info.set_property("pkg_config_name", "libsasl2")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["dl", "resolv", "pthread"]

    # ── helpers ───────────────────────────────────────────────────────────

    def _configure_args(self):
        args = [
            "--prefix=/",
            "--disable-dependency-tracking",
            "--disable-sample",
        ]
        if self.options.shared:
            args.extend(["--enable-shared", "--disable-static"])
        else:
            args.extend([
                "--disable-shared",
                "--enable-static",
                "--with-staticsasl",
            ])
        args.extend([
            "--disable-staticdlopen",
            "--disable-alwaystrue",
            "--disable-anon",
            "--disable-cram",
            "--disable-digest",
            "--disable-gssapi",
            "--disable-httpform",
            "--disable-krb4",
            "--disable-ldapdb",
            "--disable-login",
            "--disable-otp",
            "--disable-passdss",
            "--disable-sia",
            "--disable-sql",
            "--disable-srp",
            "--disable-srp-setpass",
            "--enable-ntlm",
            "--with-openssl=%s" % self.dependencies["openssl"].package_folder,
            "--without-saslauthd",
            "--without-authdaemond",
            "--without-des",
            "--without-gdbm",
            "--without-ldap",
            "--without-mysql",
            "--without-opie",
            "--without-pam",
            "--without-pgsql",
            "--without-pwcheck",
            "--without-sqlite",
            "--without-sqlite3",
            "--disable-auth-sasldb",
            "--with-dblib=none",
        ])
        return args

    def _prepare_ohos_env(self):
        # E002: /tmp is read-only on the platform; autoconf's mktemp/conftest
        # require a writable TMPDIR. Keep it inside the conan build folder.
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMP"] = tmpdir
        os.environ["TEMP"] = tmpdir
        # AC_PROG_CC_FOR_BUILD (native include/makemd5 helper) only looks for
        # gcc/cc/cl.exe; OHOS ships clang only. Use the PATH-visible name so
        # no build-machine absolute path is baked into the generated Makefile.
        os.environ["CC_FOR_BUILD"] = "clang"
        os.environ["CPP_FOR_BUILD"] = "clang -E"

    def _copy_linksrcs_for_ohos(self, source_folder):
        # Static build: lib/Makefile.am compiles $(SASL_STATIC_SRCS) after
        # symlinking them into lib/. HMDFS does not serve those symlinks, so
        # copy the sources the same way cyrus-sasl/2.1.28.1 does.
        links = {
            "plugins/ntlm.c": "lib/ntlm.c",
            "sasldb/db_none.c": "lib/db_none.c",
        }
        for source, target in links.items():
            src = os.path.join(source_folder, source)
            if not os.path.isfile(src):
                raise ConanInvalidConfiguration(
                    "expected upstream source missing: %s" % source
                )
            shutil.copy2(src, os.path.join(source_folder, target))

    def _purge_shared_artefacts_for_ohos(self):
        # Static-only package: purge any shared artefacts so downstream
        # -lsasl2 can only resolve to libsasl2.a. A stale libsasl2.so in
        # the package bakes DT_NEEDED libsasl2.so.3 into the consumer.
        import fnmatch
        libdir = os.path.join(self.package_folder, "lib")
        if not os.path.isdir(libdir):
            return
        for root, _dirs, files in os.walk(libdir):
            for name in files:
                if (fnmatch.fnmatch(name, "*.so*")
                        or fnmatch.fnmatch(name, "*.la")):
                    stale = os.path.join(root, name)
                    try:
                        os.remove(stale)
                        self.output.info(
                            "removed stale shared artefact: %s" % stale)
                    except OSError as exc:
                        self.output.warning(
                            "cannot remove %s: %s" % (stale, exc))

    def _normalize_autotools_timestamps(self):
        # The release tarball ships generated autotools files whose mtimes
        # can make make(1) try to re-run aclocal/automake/autoconf (automake
        # is not installed on OHOS -> "aclocal-1.16: inaccessible or not
        # found", Error 127). Giving every source entry the same mtime makes
        # no target look out of date, so the shipped files are used as-is.
        fixed = 1700000000
        for root, dirs, files in os.walk(self.source_folder):
            for name in files + dirs:
                try:
                    os.utime(os.path.join(root, name), (fixed, fixed))
                except OSError:
                    pass
