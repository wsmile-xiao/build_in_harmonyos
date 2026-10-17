#!/usr/bin/env python3
"""Conan recipe — ldapvi 1.8 (Autotools).

ldapvi: interactive LDAP client for Unix terminals (vipw(1) for LDAP),
written by David Lichteblau.  GPL-2.0, autotools (configure + GNUmakefile).

Dependency strategy (repo precedent: abook/adcli):
  - ncurses/6.4 IS published to the ohpcd artifact repo with headers
    (term.h / curses.h) and static wide-char libs — consume it via
    conan requires (moon-buggy precedent).
  - openldap / readline / popt / glib / openssl / pcre2 are NOT published
    to ohpcd, so generate() provisions them from the cmd-pkgs prebuilt
    package repo into SYS_PREFIX (adcli/abook precedent) and points
    configure's CPPFLAGS/LDFLAGS/PKG_CONFIG_PATH at that prefix.

OHOS adaptations (patches):
  - configure: umask 077 → 022 (E114/E011, HMDFS temp-dir permissions);
  - GNUmakefile.in: test1/test2 link lines need $(LDFLAGS) so the upstream
    unit tests can link against the provisioned prefix;
  - upstream test files: open_memstream/tmpfile/fmemopen link but fail at
    runtime on OHOS (E302/E320, fclose EBADF / stream never published);
    replaced with named temp files via mkstemp/fopen — assertions,
    data and expected values are UNCHANGED;
  - /tmp is read-only on OHOS (E002) — temp templates moved to relative
    paths in the build directory;
  - CFLAGS=-fsigned-char: ARM64 AAPCS64 makes plain `char` unsigned, but
    upstream test expectations assume signed char (print_mode_ascii
    expects 0xC3 0xA9 to be treated as non-readable → base64).
"""

import os
import re
import tarfile
import urllib.request

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches, copy, export_conandata_patches, get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

# System prefix where cmd-pkgs deps are provisioned (same prefix the
# ohos-aarch64 profile prepends to PATH).
SYS_PREFIX = os.environ.get("DEFAULT_PREFIX") or os.path.join(
    os.path.expanduser("~"), "usr", "local")

_CMDPKGS_BASE = ("https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/"
                 "releases/download/pkgs")

# (cmd-pkgs name, version, marker files that prove the dep is present)
_CMDPKGS_DEPS = [
    ("openldap", "2.6.7",
     ["include/ldap.h", "include/lber.h",
      "lib/libldap.so", "lib/liblber.so"]),
    ("readline", "8.2",
     ["include/readline/readline.h", "lib/libreadline.so"]),
    ("popt", "1.16",
     ["include/popt.h", "lib/libpopt.a"]),
    ("pcre2", "10.40",
     ["include/pcre2.h", "lib/libpcre2-8.so"]),
    ("glib", "2.88.0",
     ["include/glib-2.0/glib.h", "lib/libglib-2.0.a",
      "lib/pkgconfig/glib-2.0.pc"]),
    ("openssl", "3.5.6",
     ["include/openssl/ssl.h", "lib/libssl.so",
      "lib/pkgconfig/openssl.pc"]),
]


def _no_verify_urlopen(url, timeout=300):
    """Open a URL with TLS verification disabled (worker CA gap, same as
    the addrwatch/airlift-slice/adcli recipes)."""
    import ssl
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers={"User-Agent": "conan/ohpc"})
    return urllib.request.urlopen(req, timeout=timeout, context=ctx)


def _cmd_pkgs_install(name, version, prefix):
    """Download + extract a cmd-pkgs prebuilt package into prefix."""
    url = "{}/{}-{}-ohos-aarch64.tar.gz".format(_CMDPKGS_BASE, name, version)
    os.makedirs(prefix, exist_ok=True)
    tarball = os.path.join(prefix, ".install-{}-{}.tar.gz".format(name, version))
    try:
        with _no_verify_urlopen(url) as resp:
            with open(tarball, "wb") as fh:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    fh.write(chunk)
        with tarfile.open(tarball, "r:gz") as tf:
            tf.extractall(prefix)
    except Exception as exc:
        raise ConanInvalidConfiguration(
            "cmd-pkgs install failed for {}-{}: {}".format(name, version, exc))
    finally:
        if os.path.exists(tarball):
            os.unlink(tarball)


def _ensure_cmd_pkgs(prefix):
    """Provision all system deps from cmd-pkgs if their marker files are
    missing.  Re-runs on the same machine are no-ops."""
    for name, version, markers in _CMDPKGS_DEPS:
        missing = [m for m in markers if not os.path.exists(
            os.path.join(prefix, m))]
        if missing:
            _cmd_pkgs_install(name, version, prefix)
            still_missing = [m for m in markers if not os.path.exists(
                os.path.join(prefix, m))]
            if still_missing:
                raise ConanInvalidConfiguration(
                    "cmd-pkgs {} {} did not provide: {}".format(
                        name, version, ", ".join(still_missing)))
    # The prebuilt packages carry .pc files with whatever prefix their
    # build machine used; normalize them to SYS_PREFIX so pkg-config
    # (glib-2.0 / openssl / lber / ldap / readline) resolves correctly.
    pc_dir = os.path.join(prefix, "lib", "pkgconfig")
    if os.path.isdir(pc_dir):
        for name in os.listdir(pc_dir):
            if not name.endswith(".pc"):
                continue
            path = os.path.join(pc_dir, name)
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                data = fh.read()
            data = re.sub(r"(?m)^prefix=.*$", "prefix=" + prefix, data)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(data)


class LdapviConan(ConanFile):
    name = "ldapvi"
    version = "1.8"
    description = "Interactive LDAP client for Unix terminals"
    license = "GPL-2.0-only"
    homepage = "http://www.lichteblau.com/ldapvi/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Published to ohpcd with headers (term.h/curses.h) + static libs.
        self.requires("ncurses/6.4", options={"shared": False})

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "ldapvi is only supported on Linux/OHOS, not "
                + str(self.settings.os))

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        # ldapvi's GNUmakefile is designed for in-source builds: configure
        # must run inside the source tree.  All compile flags are therefore
        # carried via os.environ in build() (exploratory-build verified).
        _ensure_cmd_pkgs(SYS_PREFIX)

    def build(self):
        apply_conandata_patches(self)
        top = self.source_folder
        tmpdir = os.path.join(self.build_folder, ".tmp")
        os.makedirs(tmpdir, exist_ok=True)

        include_dir = os.path.join(SYS_PREFIX, "include")
        lib_dir = os.path.join(SYS_PREFIX, "lib")
        # ncurses comes from the conan dependency: its include/lib dirs
        # live in the conan cache, not under SYS_PREFIX.
        ncurses = self.dependencies["ncurses"]
        nc_pkg = ncurses.package_folder or ""
        nc_inc_dir = os.path.join(nc_pkg, "include")
        nc_lib_dir = os.path.join(nc_pkg, "lib")
        cppflags = "-I" + include_dir
        if os.path.isdir(nc_inc_dir):
            cppflags += " -I" + nc_inc_dir
        ldflags = "-L{0} -Wl,-rpath,{0}".format(lib_dir)
        if os.path.isdir(nc_lib_dir):
            ldflags += " -L" + nc_lib_dir
        pc_dir = os.path.join(lib_dir, "pkgconfig")

        os.environ["CC"] = "/data/service/hnp/bin/clang"
        os.environ["TMPDIR"] = tmpdir
        os.environ["PWD"] = top
        os.environ["CONFIG_SHELL"] = "/data/service/hnp/bin/bash"
        os.environ["CPPFLAGS"] = cppflags
        os.environ["LDFLAGS"] = ldflags
        # tigetstr lives in libncursesw (AC_SEARCH_LIBS only tries
        # -lcurses/-lncurses), and ARM64 `char` is unsigned by default
        # (AAPCS64) while upstream tests assume signed char.
        os.environ["LIBS"] = "-lncursesw"
        os.environ["CFLAGS"] = "-fsigned-char"
        if os.path.isdir(pc_dir):
            os.environ["PKG_CONFIG_PATH"] = pc_dir

        self.run("cd {top} && ./configure --prefix=/".format(top=top))
        self.run("cd {top} && make -j1".format(top=top))
        # upstream unit tests: test1 (247 cases) + test2 (17 cases)
        self.run("cd {top} && make test -j1".format(top=top))

    def package(self):
        top = self.source_folder
        self.run("cd {top} && make install "
                 "DESTDIR={dst}".format(top=top, dst=self.package_folder))
        copy(self, "COPYING", src=top,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # application package: consumers use the `ldapvi` binary
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
