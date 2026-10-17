#!/usr/bin/env python3
"""Conan recipe - cyrus-sasl 2.1.28.3 (Cyrus SASL / libsasl2, autotools).

Target platform: OpenHarmony / HarmonyOS PC (aarch64).

Scope of this recipe
--------------------
A self-contained build of the libsasl2 framework: shared ``libsasl2.so.3``
plus the mechanism plugins, with ``--with-dblib=none`` and every external
authentication backend (saslauthd, PAM, LDAP, SQL, Kerberos, OpenSSL, DES,
OPIE, GDBM) disabled. The shipped library therefore has **no conan runtime
dependency** and ``libsasl2.so.3`` links only against system libraries
(DT_NEEDED = libc.so).

``package_type`` is ``library`` and the delivered package is a **pure
library**: ``package()`` removes every installed executable (upstream
``bin/pluginviewer``, plus ``sbin/`` tooling) and all ``.la`` files, so the
package contains only ``lib/``, ``include/``, ``lib/pkgconfig`` and
``licenses/``. A pure library must not declare ``commands.json`` (R38).

Version decision (R37 / L0j)
----------------------------
Upstream release is 2.1.28. The artifact repository ``ohpcd`` already holds
``cyrus-sasl/2.1.28``, ``cyrus-sasl/2.1.28.1`` and ``cyrus-sasl/2.1.28.2``
(all built from the same 2.1.28 tarball). cnb.cool rejects a second recipe
revision for an existing version, so this adaptation-revision is bumped to
``2.1.28.3``.

HarmonyOS adaptations (see notes.md for the full log)
-----------------------------------------------------
* patches/0001 - autoconf temp dir umask 077 -> 022. On HMDFS the 0700
  ``./confXXXXXX`` created by ``configure``/``config.status`` is not
  writable, so config.status aborts with "Permission denied".
* ``TMPDIR`` is redirected into the build folder: the platform ``/tmp`` is
  read-only (E002), which breaks autoconf's ``mktemp``/conftest probes.
* ``CC_FOR_BUILD``/``CPP_FOR_BUILD`` are pinned to PATH-visible ``clang``:
  configure uses ``AC_PROG_CC_FOR_BUILD`` for the native ``include/makemd5``
  helper and only searches for ``gcc``/``cc``/``cl.exe`` after stripping the
  host prefix, none of which exist on OHOS.
* The upstream tarball's ``configure.ac`` is newer than ``aclocal.m4``, so
  ``make`` tries to re-run ``aclocal``/``automake`` (not present on OHOS).
  All source timestamps are normalised to a single value so the generated
  autotools files are used as shipped.
* ``make -j1``: the HMDFS build directory cannot create the GNU make
  jobserver FIFO ("mkfifo ... Operation not permitted").
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get, rm)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class CyrusSaslConan(ConanFile):
    name = "cyrus-sasl"
    version = "2.1.28.3"
    description = "Cyrus SASL authentication framework (libsasl2)"
    license = "BSD-4-Clause"
    homepage = "https://www.cyrusimap.org/sasl/"
    url = "https://github.com/cyrusimap/cyrus-sasl"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": True,
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
                "cyrus-sasl is only supported on Linux/OHOS, not "
                + str(self.settings.os))

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)
        self._normalize_autotools_timestamps()

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(self._configure_args())
        tc.generate()

    def build(self):
        self._prepare_ohos_env()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        self._prepare_ohos_env()
        autotools = Autotools(self)
        autotools.install()
        # libtool .la files embed build-machine absolute paths in
        # dependency_libs/libdir; the link information is already carried by
        # the pkg-config file and cpp_info, so drop them. rm() defaults to
        # recursive=False (only the package root is scanned), so the plugins
        # under lib/sasl2/ would survive without recursive=True.
        rm(self, "*.la", self.package_folder, recursive=True)
        # Pure library package: the delivered tree must contain no
        # executables, and this recipe therefore declares no commands.json
        # (R38). Upstream installs bin/pluginviewer (plus sbin/ tooling when
        # saslauthd/sasldb are enabled); with --with-dblib=none the sasldb CLI
        # tools are not built at all and pluginviewer is a developer-only
        # plugin inspector that is useless without the removed sasldb backend.
        # Drop both directories entirely so the package is a genuine library.
        import shutil
        for _exe_dir in ("bin", "sbin"):
            _path = os.path.join(self.package_folder, _exe_dir)
            if os.path.isdir(_path):
                shutil.rmtree(_path, ignore_errors=True)
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["sasl2"]
        self.cpp_info.set_property("cmake_file_name", "cyrus-sasl")
        self.cpp_info.set_property("cmake_target_name", "cyrus-sasl::cyrus-sasl")
        self.cpp_info.set_property("pkg_config_name", "libsasl2")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["dl", "resolv", "pthread"]
        # Mechanism/auxprop plugins are dlopen'ed at run time. The compiled-in
        # default plugin directory is /lib/sasl2 (prefix=/), which does not
        # resolve inside a relocatable conan package, so expose the packaged
        # plugin directory through the run environment.
        self.runenv_info.define_path(
            "SASL_PATH", os.path.join(self.package_folder, "lib", "sasl2"))
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))

    # ── helpers ───────────────────────────────────────────────────────────

    def _configure_args(self):
        args = []
        if self.settings.os == "OHOS":
            # The release tarball's config.guess (2018-02-24) does not know
            # the "HarmonyOS" uname reported by the platform, so configure
            # aborts with "cannot guess build type". Feed the canonical
            # aarch64 triplet explicitly (native build: build == host).
            args.extend([
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-gnu",
            ])
        if self.options.shared:
            args.extend(["--enable-shared", "--disable-static"])
        else:
            args.extend(["--disable-shared", "--enable-static"])
        args.extend([
            "--disable-dependency-tracking",
            "--disable-sample",
            "--with-dblib=none",
            "--without-saslauthd",
            "--disable-gssapi",
            "--disable-ldapdb",
            "--disable-krb4",
            "--disable-sql",
            "--without-openssl",
            "--without-des",
            "--without-pam",
            "--without-pwcheck",
            "--without-authdaemond",
            "--without-ldap",
            "--without-mysql",
            "--without-pgsql",
            "--without-sqlite",
            "--without-sqlite3",
            "--without-opie",
            "--without-gdbm",
            "--disable-ntlm",
            "--disable-srp",
            "--disable-srp-setpass",
            "--disable-otp",
            "--disable-login",
            "--disable-staticdlopen",
            "--disable-sia",
            "--disable-passdss",
            "--disable-httpform",
            "--disable-alwaystrue",
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
