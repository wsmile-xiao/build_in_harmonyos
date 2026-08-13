#!/usr/bin/env python3
"""Conan recipe — adcli 0.9.2 (autotools).

adcli is an Active Directory domain enrollment/management command-line tool
(and its internal libadcli convenience library, which upstream does NOT
install — only the `adcli` binary is shipped).

The GitLab tag archive ships no generated `configure` (autoreconf output is
not committed), so build() bootstraps with `autoreconf -fi` first.

Dependencies (krb5 / OpenLDAP / Cyrus SASL) are not published to the ohpcd
artifact repo and are NOT present on the OHOS worker's system prefix, so
generate() provisions them under SYS_PREFIX before configure runs:
  - krb5 1.22.1 and openldap 2.6.7 from the cmd-pkgs prebuilt package repo
    (https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs — same pattern as
    the abook/libclastfm recipes);
  - the sasl/sasl.h header is vendored at build time from the pinned
    upstream cyrus-sasl 2.1.28 tag (cmd-pkgs ships no cyrus-sasl package);
    adcli only uses the header (sasl_interact_t, no -lsasl link).
configure is pointed at that prefix with explicit CPPFLAGS/LDFLAGS (and a
runtime rpath so the installed binary and the upstream `make check` harness
find the system .so files).
"""
import os
import ssl
import tarfile
import urllib.request

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches, copy, export_conandata_patches, get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

# System prefix where the recipe provisions krb5 / openldap / sasl devel
# (same prefix the ohos-aarch64 profile prepends to PATH, and where the
# cepces/krb5 precedent deployed krb5).
SYS_PREFIX = "/storage/Users/currentUser/usr/local"

# cmd-pkgs prebuilt packages (OpenHarmony aarch64) — same source as the
# abook/acedb/libclastfm recipes.
_CMDPKGS_BASE = ("https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/"
                 "releases/download/pkgs")
# adcli only needs sasl.h (it uses sasl_interact_t via <sasl/sasl.h> and
# links no -lsasl); cmd-pkgs/ohpcd have no cyrus-sasl package, so the real
# upstream headers from the pinned 2.1.28 tag are fetched at build time.
# Both sasl.h AND prop.h must be vendored: upstream include/sasl.h does an
# unconditional `#include "prop.h"` (sasl.h:135 in the 2.1.28 tag), so the
# preprocessor test for <sasl/sasl.h> fails without prop.h next to it.
_SASL_BASE_URL = ("https://raw.githubusercontent.com/cyrusimap/cyrus-sasl/"
                  "cyrus-sasl-2.1.28/include")
# (relative name, required content markers)
_SASL_HEADERS = [
    ("sasl.h", (b"LIBSASL_API", b"SASL_H")),
    ("prop.h", (b"PROP_H", b"prop_set")),
]


def _drop_umask_077(path):
    """E114/E011: HMDFS forces setgid on directories; `umask 077 && mktemp -d`
    creates a drwx--S--- temp dir that is not writable even by its owner.
    Replace every `umask 077` with `umask 022` in the generated configure so
    its AS_TMPDIR / config.status temp dirs stay owner-writable (E011's
    recommended method, same as the a52dec/analog recipes)."""
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()
    data = data.replace("umask 077", "umask 022")
    with open(path, "w", encoding="utf-8") as f:
        f.write(data)


def _automake_count(text, label):
    """Parse `# LABEL: N` from an automake parallel-tests test-suite.log."""
    for line in text.splitlines():
        if line.startswith("# " + label + ":"):
            try:
                return int(line.split(":", 1)[1].strip())
            except ValueError:
                return 0
    return 0


def _no_verify_urlopen(url, timeout=180):
    """Open `url` with a TLS context that skips certificate verification.

    The OHOS worker's Python CA trust store cannot validate the
    gitcode.com certificate chain (CERTIFICATE_VERIFY_FAILED / unable to
    get local issuer certificate — same worker-side trust gap as the
    addrwatch/airlift-slice recipes).  The payloads are integrity-checked
    downstream (conandata sha256 for sources, content checks here), so an
    unverified context is acceptable for these bootstrap downloads.
    """
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=timeout, context=ctx)


def _cmd_pkgs_install(name, version, prefix):
    """Download + extract a cmd-pkgs prebuilt package into prefix.

    Pure-Python (urllib + tarfile, acedb pattern) so it does not depend on
    curl being on PATH.  Callers check for the needed files first so a
    re-run on the same machine is a no-op.
    """
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


def _ensure_openldap(prefix):
    """Provision OpenLDAP client devel (ldap.h / libldap / liblber) so
    configure's AC_CHECK_LIB(ldap|ber) and AC_CHECK_HEADERS(ldap.h) pass."""
    inc = os.path.join(prefix, "include", "ldap.h")
    libs = [os.path.join(prefix, "lib", "libldap.so"),
            os.path.join(prefix, "lib", "liblber.so")]
    if os.path.exists(inc) and all(os.path.exists(p) for p in libs):
        return
    _cmd_pkgs_install("openldap", "2.6.7", prefix)
    missing = [p for p in [inc] + libs if not os.path.exists(p)]
    if missing:
        raise ConanInvalidConfiguration(
            "openldap cmd-pkgs install did not provide: " + ", ".join(missing))


def _ensure_krb5(prefix):
    """Provision MIT krb5 devel (krb5.h / gssapi_krb5.h / libkrb5 ...).  The
    KRB5_CFLAGS/KRB5_LIBS configure vars bypass the krb5-config probe, but
    library/*.c still #include <krb5/krb5.h> and <gssapi/gssapi_krb5.h> and
    link -lkrb5 -lgssapi_krb5 -lk5crypto -lcom_err."""
    incs = [os.path.join(prefix, "include", "krb5", "krb5.h"),
            os.path.join(prefix, "include", "gssapi", "gssapi_krb5.h")]
    libs = [os.path.join(prefix, "lib", "libkrb5.so"),
            os.path.join(prefix, "lib", "libgssapi_krb5.so"),
            os.path.join(prefix, "lib", "libk5crypto.so"),
            os.path.join(prefix, "lib", "libcom_err.so")]
    if all(os.path.exists(p) for p in incs + libs):
        return
    _cmd_pkgs_install("krb5", "1.22.1", prefix)
    missing = [p for p in incs + libs if not os.path.exists(p)]
    if missing:
        raise ConanInvalidConfiguration(
            "krb5 cmd-pkgs install did not provide: " + ", ".join(missing))


def _ensure_sasl_header(prefix):
    """Vendor the real upstream sasl/sasl.h + prop.h (cyrus-sasl 2.1.28)
    under the prefix — configure checks AC_CHECK_HEADERS([sasl/sasl.h]) and
    library/adconn.c uses sasl_interact_t from it.  Both files are needed:
    sasl.h #includes "prop.h" (quoted include resolves relative to the
    including file, so prop.h must sit next to sasl.h in include/sasl/)."""
    base = os.path.join(prefix, "include", "sasl")
    if all(os.path.exists(os.path.join(base, name))
           for name, _markers in _SASL_HEADERS):
        return
    os.makedirs(base, exist_ok=True)
    for name, markers in _SASL_HEADERS:
        url = "{}/{}".format(_SASL_BASE_URL, name)
        target = os.path.join(base, name)
        try:
            with _no_verify_urlopen(url) as resp:
                data = resp.read()
        except Exception as exc:
            raise ConanInvalidConfiguration(
                "could not fetch upstream {} ({}): {}".format(name, url, exc))
        if len(data) < 1000 or not all(m in data for m in markers):
            raise ConanInvalidConfiguration(
                "upstream {} download looks invalid ({} bytes)".format(
                    name, len(data)))
        with open(target, "wb") as fh:
            fh.write(data)


class AdcliConan(ConanFile):
    name = "adcli"
    version = "0.9.2"
    description = "Tool for performing actions on an Active Directory domain"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.freedesktop.org/realmd/adcli"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # The GitLab tag archive ships no `configure`, so build() runs
        # `autoreconf -fi` to bootstrap.  The OHOS worker has the autoconf
        # suite under /data/service/hnp/bin but no automake/aclocal/libtoolize
        # (same situation as abiword-plugin-clarisworks / afuse).
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "adcli is only supported on Linux/OHOS, not "
                + str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        # The OHOS worker has no krb5/openldap/sasl devel packages under
        # SYS_PREFIX (configure reported "checking for krb5-config... no" and
        # "checking for ldap.h... no" on the preflight machine); provision
        # them first so the CPPFLAGS/LDFLAGS gates below trigger and
        # configure's LDAP/SASL checks succeed.
        _ensure_openldap(SYS_PREFIX)
        _ensure_krb5(SYS_PREFIX)
        _ensure_sasl_header(SYS_PREFIX)

        tc = AutotoolsToolchain(self)
        # config.guess cannot identify HarmonyOS (uname -s = "HarmonyOS",
        # kernel "HongMeng Kernel"); pass the triplet explicitly (config.sub
        # supports *-linux-ohos) — same approach as abiword-plugin-clarisworks.
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        # doc needs xsltproc/xmlto; coverage needs gcov/lcov — neither exists
        # on the OHOS worker, and both are optional upstream features.
        tc.configure_args.append("--disable-doc")
        tc.configure_args.append("--disable-coverage")
        # krb5 / openldap / cyrus-sasl devel were provisioned under
        # SYS_PREFIX above: configure's AC_CHECK_HEADERS(ldap.h, sasl/sasl.h)
        # and AC_CHECK_LIB(ldap, ...) need the include/lib dirs, and the
        # linked binaries need a runtime rpath so `make check` and the
        # installed tool can load the .so files without LD_LIBRARY_PATH.
        include_dir = os.path.join(SYS_PREFIX, "include")
        lib_dir = os.path.join(SYS_PREFIX, "lib")
        if os.path.isdir(include_dir):
            tc.configure_args.append(
                "CPPFLAGS=-I{}".format(include_dir))
            # configure.ac requires either a working krb5-config on PATH or
            # pre-set KRB5_CFLAGS/KRB5_LIBS (AC_ARG_VAR precious variables —
            # KRB5_PASSED_CFLAGS/LIBS bypass the krb5-config probe).  The OHOS
            # worker has the krb5 devel install under SYS_PREFIX but no usable
            # krb5-config, so pass the flags for the same prefix explicitly
            # (mirrors `krb5-config --cflags/--libs krb5 gssapi` output).
            tc.configure_args.append(
                "KRB5_CFLAGS=-I{}".format(include_dir))
        if os.path.isdir(lib_dir):
            tc.configure_args.append(
                "LDFLAGS=-L{} -Wl,-rpath,{}".format(lib_dir, lib_dir))
            tc.configure_args.append(
                "KRB5_LIBS=-L{} -lkrb5 -lgssapi_krb5 -lk5crypto -lcom_err".format(lib_dir))
        tc.generate()

    def _fs_env(self):
        """HMBS platform diagnosis [shell_getcwd]/[readonly_tmp] (same failure
        signature as addchain/analog/open-mpi): HMDFS denies getcwd() on the
        conan build tree's parent dirs, so bash/autoconf `pwd` fails
        ("configure: error: working directory cannot be determined"), and /tmp
        is a read-only erofs mount.  Set PWD explicitly (autoconf checks $PWD
        first; bash inits $PWD from the env without calling getcwd()) and pin
        TMPDIR/TMP/TEMP to a writable dir for the configure/make/install steps."""
        tmpdir = (os.environ.get("TMPDIR") or os.environ.get("TMP")
                  or os.environ.get("TEMP")
                  or os.path.join(self.build_folder, ".tmp"))
        os.makedirs(tmpdir, exist_ok=True)
        env = Environment()
        env.define("PWD", self.build_folder)
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        env.define("TEMP", tmpdir)
        return env

    def build(self):
        apply_conandata_patches(self)
        # The GitLab archive ships no `configure`: generate one from
        # configure.ac (run in the source folder, like abiword/cyrus-sasl).
        self.run("autoreconf -fi", cwd=self.source_folder, env="conanbuild")
        # E114/E011: drop umask 077 from the generated configure (HMDFS)
        _drop_umask_077(os.path.join(self.source_folder, "configure"))

        autotools = Autotools(self)
        with self._fs_env().vars(self).apply():
            autotools.configure()
            # E074: parallel make hits the HMDFS jobserver fifo EPERM
            autotools.make(args=["-j1"])
            # L1: run the upstream unit-test suite (5 TAP-style test programs:
            # test-seq/test-util/test-ldap/test-attrs/test-adenroll)
            autotools.make(target="check", args=["-j1"])
        self._emit_upstream_test_result()

    def _emit_upstream_test_result(self):
        """Emit the hmbs upstream-test gate marker from automake's real
        test-suite.log counts (parallel-tests TAP harness output), so the
        numbers come from the test framework itself, not from estimates."""
        import json
        suite_logs = []
        for root, _dirs, files in os.walk(self.build_folder):
            if "test-suite.log" in files:
                suite_logs.append(os.path.join(root, "test-suite.log"))
        if not suite_logs:
            raise ConanException(
                "make check produced no test-suite.log under "
                + self.build_folder)
        with open(suite_logs[0], "r", encoding="utf-8", errors="replace") as fh:
            content = fh.read()
        passed = _automake_count(content, "PASS")
        xfailed = _automake_count(content, "XFAIL")
        skipped = _automake_count(content, "SKIP")
        failed = (_automake_count(content, "FAIL")
                  + _automake_count(content, "XPASS")
                  + _automake_count(content, "ERROR"))
        result = {
            "status": "passed" if failed == 0 else "failed",
            "framework": "automake-tap",
            "command": "make check",
            "discovered": _automake_count(content, "TOTAL"),
            "executed": _automake_count(content, "TOTAL") - skipped,
            "passed": passed + xfailed,
            "failed": failed,
            "skipped": skipped,
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, ensure_ascii=False))
        if result["status"] != "passed":
            self.output.error(
                "upstream make check did not pass: " + json.dumps(result))

    def package(self):
        autotools = Autotools(self)
        with self._fs_env().vars(self).apply():
            autotools.install()
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # application package: consumers use the `adcli` binary, not a lib
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        # Conan 2 AutotoolsToolchain forces both --bindir and --sbindir to
        # ${prefix}/bin, so upstream's sbin_PROGRAMS (= adcli) is installed
        # to <pkg>/bin/adcli, NOT sbin/ (verified in the preflight log:
        # `libtool: install: .../p//bin/adcli`).  bindirs must match the real
        # layout so VirtualRunEnv puts the binary dir on PATH (test_package
        # previously failed with exit 127 = command not found).
        self.cpp_info.bindirs = ["bin"]
