#!/usr/bin/env python3
"""Conan recipe — debian-security-support 14+2026.05.07 (portable shell tool + data).

Debian-native package whose whole program is one shell script
`check-support-status` (rendered from check-support-status.in) + one per-release
security-support data file (security-support.deb{11,12,13,14}). It reports which
installed Debian packages have ended / limited security support.

Portable-core vs Debian-integration split (kept, no core deleted, no mock):
  - core algorithm (parse data file, intersect with an installed-package list,
    compare end dates with today) runs unchanged; the data files ship verbatim
    as the real knowledge base;
  - the ONLY Debian coupling — enumerating installed packages via `dpkg-query` —
    is factored into a `pkglist-probe` backend with capability detection:
      DSS_MANIFEST (real TSV manifest) -> DSS_DPKG_STATUS (real dpkg status file)
      -> dpkg-query on PATH -> else write a backend-unavailable marker and fail.
  - honest failure patch: upstream exits 0 with empty output when dpkg-query is
    missing (pipeline swallows the exit code); this recipe makes the script exit
    3 with a diagnostic in that case instead of a silent fake "all clean".
  - portability patch: system grep on HarmonyOS may lack PCRE (-P); data-file
    patterns are ERE-safe so grep falls back to -E when -P is unavailable.

Debian version string is 1:14+2026.05.07 (epoch 1). Conan reference cannot carry
epoch ':' (recorded in conandata/manifest); conan version = 14+2026.05.07.
"""
import os
import re
import stat

from conan import ConanFile
from conan.tools.files import copy, get


class DebianSecuritySupportConan(ConanFile):
    name = "debian-security-support"
    version = "14+2026.05.07"
    package_type = "unknown"  # 纯 shell 工具 + 数据（无编译/无 ELF）

    settings = "os", "compiler", "build_type", "arch"  # CI L0 gate
    options = None
    default_options = None

    def requirements(self):
        pass

    def layout(self):
        self.folders.source = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _render_check_support_status(self, src):
        text = open(os.path.join(src, "check-support-status.in"),
                    encoding="utf-8", errors="replace").read()
        n0 = text.count("[% VERSION %]")
        text = text.replace("[% VERSION %]", self.version)
        assert text.count("[% VERSION %]") == 0 and n0 >= 1

        # 0) do NOT rely on external gettext/gettext.sh: on HarmonyOS the
        #    gettext binary may be unusable (libintl relocation) and gettext.sh
        #    may be absent. Install deterministic minimal functions that keep the
        #    English messages (portability package; i18n is not load-bearing).
        gt_old = ". gettext.sh\nexport TEXTDOMAIN=debian-security-support"
        gt_new = ('gettext() { printf \'%s\' "$1"; }\n'
                  'eval_gettext() { eval "printf \'%s\' \\"$1\\""; }\n'
                  'export TEXTDOMAIN=debian-security-support')
        assert text.count(gt_old) == 1
        text = text.replace(gt_old, gt_new, 1)

        # /etc/debian_version may not exist on OHOS — don't leak the error.
        dv_old = 'cat /etc/debian_version | grep'
        assert text.count(dv_old) == 1
        text = text.replace(dv_old, 'cat /etc/debian_version 2>/dev/null | grep', 1)

        # CI/Harmony mktemp variants differ: upstream uses GNU-only
        # `mktemp --tmpdir --directory ...XXXXX`; some OHOS workers require a
        # pathname template with six Xs and reject --tmpdir. Render a POSIX-ish
        # fallback that never turns an otherwise valid package validation into a
        # platform mktemp failure.
        tmp_old = """TEMPDIR="$(mktemp --tmpdir --directory debian-security-support.XXXXX)"
trap "rm -rf '$TEMPDIR'" 0"""
        tmp_new = """TMPBASE="${TMPDIR:-/tmp}"
TEMPDIR="$(mktemp -d "${TMPBASE%/}/debian-security-support.XXXXXX" 2>/dev/null || true)"
if [ -z "$TEMPDIR" ] ; then
    TEMPDIR="${TMPBASE%/}/debian-security-support.$$"
    rm -rf "$TEMPDIR"
    mkdir -p "$TEMPDIR" || exit 1
fi
trap 'rm -rf "$TEMPDIR"' 0"""
        assert text.count(tmp_old) == 1
        text = text.replace(tmp_old, tmp_new, 1)

        status_tmp_old = 'TEMPFILE="$(mktemp --tmpdir="$(dirname "$STATUSDB_FILE")")"'
        status_tmp_new = """STATUSDB_DIR="$(dirname "$STATUSDB_FILE")"
                    TEMPFILE="$(mktemp "${STATUSDB_DIR%/}/debian-security-support.XXXXXX" 2>/dev/null || true)"
                    if [ -z "$TEMPFILE" ] ; then
                        TEMPFILE="${STATUSDB_DIR%/}/debian-security-support.$$"
                        rm -f "$TEMPFILE"
                    fi"""
        assert text.count(status_tmp_old) == 1
        text = text.replace(status_tmp_old, status_tmp_new, 1)

        # 1) grep PCRE (-P) availability fallback -> -E (HarmonyOS grep often
        #    built without PCRE). Insert after TEXTDOMAIN export.
        anchor = "export TEXTDOMAIN=debian-security-support\n"
        assert text.count(anchor) == 1
        grepx = (
            "\n# grep(-P) fallback: HarmonyOS system grep may lack PCRE; "
            "data patterns are ERE-safe.\n"
            "if command grep -P -q 'x' /dev/null 2>/dev/null ; then\n"
            "    GREP=grep\n"
            "    GREP_FLAGS=-P\n"
            "else\n"
            "    GREP=grep\n"
            "    GREP_FLAGS=-E\n"
            "fi\n")
        text = text.replace(anchor, anchor + grepx, 1)

        # 2) data file list -> runtime-resolvable dir (DSS_DATA_DIR override);
        #    other [% LIST %] uses (internal re-invocations) become "$LIST".
        old_list = 'LIST=[% LIST %]'
        assert text.count(old_list) == 1
        text = text.replace(
            old_list,
            'LIST="${DSS_DATA_DIR:-$(dirname "$0")/../share/debian-security-support}/'
            'security-support.deb${DEBIAN_VERSION}"', 1)
        n_left = text.count("[% LIST %]")
        assert n_left >= 1
        text = text.replace("[% LIST %]", '"$LIST"')

        # 3) dpkg backend -> pkglist-probe (absolute, runtime-resolved), and
        #    pass DSS_MARKER so an unavailable backend is detected (not silently
        #    swallowed by the pipeline's trailing awk -> upstream's exit-0 bug).
        assert text.count("[% DPKG_QUERY %]") == 1
        text = text.replace(
            "[% DPKG_QUERY %]",
            'DSS_MARKER="$TEMPDIR/backend-unavailable" '
            '"$(dirname "$0")/../libexec/debian-security-support/pkglist-probe"', 1)

        # 4) AWK: runtime-detected (DSS_AWK override; default 'awk')
        text = text.replace("[% AWK %]", '${DSS_AWK:-awk}')

        # 5) grep -P usages -> $GREP $GREP_FLAGS
        for old, new in [
            ("grep -P -x -e ", "$GREP $GREP_FLAGS -x -e "),
            ("grep -q -P -x -e ", "$GREP -q $GREP_FLAGS -x -e "),
            ("grep -vP ", "$GREP -v $GREP_FLAGS "),
        ]:
            text = text.replace(old, new)
        # (the inserted -P availability probe legitimately contains "grep -P -q";
        #  guard only on the upstream invocation tokens, not that detector)
        for token in ("grep -P -x", "grep -q -P", "grep -vP"):
            if token in text:
                raise RuntimeError(
                    f"unhandled grep -P occurrence {token!r} in rendered script")

        # 6) honest failure: after the installed-list pipeline, if the probe
        #    could not enumerate (no dpkg-query / manifest / status file), exit 3.
        pipe_out = '>"$INSTALLED_LIST"'
        assert text.count(pipe_out) == 1
        honest = (pipe_out + "\n"
                  "if [ -f \"$TEMPDIR/backend-unavailable\" ] ; then\n"
                  "    >&2 echo \"$NAME: cannot enumerate installed Debian packages "
                  "(no dpkg-query and DSS_MANIFEST/DSS_DPKG_STATUS not set); "
                  "refusing to report an empty result\"\n"
                  "    exit 3\n"
                  "fi")
        text = text.replace(pipe_out, honest, 1)
        return text

    def build(self):
        src = self.source_folder
        rendered = self._render_check_support_status(src)

        out = os.path.join(self.build_folder, "stage")
        bindir = os.path.join(out, "bin")
        libexec = os.path.join(out, "libexec", "debian-security-support")
        datadir = os.path.join(out, "share", "debian-security-support")
        os.makedirs(bindir, exist_ok=True)
        os.makedirs(libexec, exist_ok=True)
        os.makedirs(datadir, exist_ok=True)

        with open(os.path.join(bindir, "check-support-status"), "w",
                  encoding="utf-8", newline="\n") as fh:
            fh.write(rendered)
        os.chmod(os.path.join(bindir, "check-support-status"),
                 os.stat(os.path.join(bindir, "check-support-status")).st_mode
                 | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

        probe = PROBE_TEMPLATE.replace("__DSS_MARKER__", "DSS_MARKER")
        with open(os.path.join(libexec, "pkglist-probe"), "w",
                  encoding="utf-8", newline="\n") as fh:
            fh.write(probe)
        os.chmod(os.path.join(libexec, "pkglist-probe"),
                 os.stat(os.path.join(libexec, "pkglist-probe")).st_mode
                 | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

        # copy data files verbatim
        for f in os.listdir(src):
            if re.fullmatch(r"security-support\.deb\d+", f):
                copy(self, f, src=src, dst=datadir)

    def package(self):
        stage = os.path.join(self.build_folder, "stage")
        copy(self, "*", src=os.path.join(stage, "bin"),
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "pkglist-probe",
             src=os.path.join(stage, "libexec", "debian-security-support"),
             dst=os.path.join(self.package_folder, "libexec", "debian-security-support"))
        copy(self, "security-support.deb*",
             src=os.path.join(stage, "share", "debian-security-support"),
             dst=os.path.join(self.package_folder, "share", "debian-security-support"))
        # README.ohos with data provenance / backend semantics / epoch note
        readme = README_OHOS
        with open(os.path.join(self.package_folder, "share",
                               "debian-security-support", "README.ohos"),
                  "w", encoding="utf-8") as fh:
            fh.write(readme)
        cp = os.path.join(self.source_folder, "debian", "copyright")
        if os.path.exists(cp):
            copy(self, "copyright", src=os.path.dirname(cp),
                 dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # 纯 shell 工具：暴露 bin（默认 bindirs）供 PATH；数据在 share。
        self.cpp_info.libs = []
        self.cpp_info.resdirs = ["share"]


PROBE_TEMPLATE = r'''#!/bin/sh
# pkglist-probe — enumerate "installed Debian packages" for check-support-status.
# Capability detection (no mock, no fake success):
#   1. DSS_MANIFEST=<file>       -> output that real TSV manifest verbatim
#                                   (dpkg-query --show format:
#                                    $Status\t$binary:Package\t$Version\t$source:Package)
#   2. DSS_DPKG_STATUS=<file>    -> parse a real /var/lib/dpkg/status into the
#                                    same TSV (only "Status: install ..." stanzas)
#   3. dpkg-query on PATH        -> exec it unchanged (Debian/chroot/container)
#   4. otherwise                 -> write DSS_MARKER file (if set), print a
#                                   diagnostic to stderr, exit 3.
set -e

[ -n "$DSS_MANIFEST" ] && [ -f "$DSS_MANIFEST" ] && { cat "$DSS_MANIFEST"; exit 0; }

if [ -n "$DSS_DPKG_STATUS" ] && [ -f "$DSS_DPKG_STATUS" ] ; then
    awk 'BEGIN{RS="\n\n"} /^Status: install/{pkg="";ver="";src=""
        for(i=1;i<=NF;i++){if($i=="Package:"){pkg=$(i+1)}
            else if($i=="Version:"){ver=$(i+1)}
            else if($i=="Source:"){src=$(i+1)}}
        if(src=="")src=pkg
        if(pkg!="")printf "install ok installed\t%s\t%s\t%s\n",pkg,ver,src}' \
        "$DSS_DPKG_STATUS"
    exit 0
fi

if [ -z "$DSS_DISABLE_DPKG" ] && command -v dpkg-query >/dev/null 2>&1 ; then
    exec dpkg-query "$@"
fi

if [ -n "$__DSS_MARKER__" ] ; then
    : > "$__DSS_MARKER__"
fi
echo "pkglist-probe: no Debian package backend available (dpkg-query missing; " \
     "set DSS_MANIFEST or DSS_DPKG_STATUS to a real installed-package list)" >&2
exit 3
'''

README_OHOS = """debian-security-support — OHOS adaptation notes

This is a pure shell tool + per-release data files, adapted from the Debian
native source package (Debian version 1:14+2026.05.07; Conan version
14+2026.05.07 — epoch '1' is not representable in a Conan reference and is
recorded in conandata/manifest instead).

What is packaged:
  bin/check-support-status                     rendered main program
  libexec/debian-security-support/pkglist-probe  installed-package backend (new)
  share/debian-security-support/security-support.deb{11,12,13,14}
  share/debian-security-support/README.ohos    this file

Semantics preserved (runs unchanged given a package list):
  - the portable core: read data file -> intersect with installed package list
    -> compare each end date (column 4) with today -> report ended/limited/
    earlyend. Output format identical to Debian.
  - Debian integration layer is optional: enumerate installed packages via
    pkglist-probe (DSS_MANIFEST -> DSS_DPKG_STATUS -> dpkg-query -> honest exit 3).

Honest boundaries:
  - On pure OHOS there is no dpkg database, so "scan this machine's installed
    Debian packages" has no meaning. The tool refuses to report an empty "all
    clean" result (exit 3 + diagnostic) unless a real manifest/status file is
    supplied, or dpkg-query exists (Debian/chroot/container).
  - grep without PCRE (-P) is detected and falls back to -E (data patterns are
    ERE-safe).

Runtime requirements (deploy-time, not installed by this recipe):
  sh, awk (gawk/mawk/original-awk), GNU date (-d), grep (-E/-P), getopt,
  gettext-base, coreutils. dpkg-query is OPTIONAL (backend).
"""

