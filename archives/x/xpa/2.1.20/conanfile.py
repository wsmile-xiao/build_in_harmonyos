#!/usr/bin/env python3
"""Conan recipe for xpa 2.1.20 — X Public Access message/passing library.

xpa (SAO/TDC) provides seamless communication between Unix programs,
built around a client/server model (xpans nameserver + access points).

OHOS adaptation notes:
  - pre-generated configure ships with the release archive; no
    autoreconf bootstrap needed.
  - the E114 umask-077 wrapper inside the generated configure trips on
    HMDFS setgid dirs (config.status cannot create confstat temp files)
    — stripped at build() time, same treatment as sockperf/toppred.
  - the ohos-aarch64 profile [buildenv] pins SHELL/CONFIG_SHELL to the
    hnp bash which getcwd-hangs inside HMDFS build dirs (E386,
    §12.70①) — aggregated env scripts rewritten in place.
  - triplet: only --build=aarch64-unknown-linux-gnu is passed.  The
    bundled config.sub rejects aarch64-unknown-linux-ohos
    ("machine `aarch64-unknown-linux' not recognized") and E007
    forbids working around detection with --host (it flips configure
    into cross-compiling mode and skips AC_RUN_IFELSE probes).  The
    build runs natively on the OHOS device, so --build alone keeps
    host==build and the runtime probes live (same shape as the
    libextractor 1.13 on-device configure).
  - Tcl and X11 probes auto-degrade when absent (no_tcl / have_x=no),
    so no explicit disable flags are required on OHOS.
  - no automake TESTS registration exists (TESTPROGS ctest/stest/rtest
    are plain make targets, `make check` is not defined); behavior is
    covered by the consumer test in test_package (R34).
"""
import glob
import os
import re

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, export_conandata_patches,
                              get, save)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

_HNP_BASH = "/data/service/hnp/bin/bash"

# POSIX sh, generated at build time by the recipe (CI only reads
# conanfile.py/conandata.yml/test_package/patches, so it must not be an
# archived file).  Upstream functional test per doc/examples.html.
_UPSTREAM_TESTS_SH = r"""#!/bin/sh
# xpa ships no automake TESTS/check target: the upstream test entry point is
# `make testall` (ctest/stest/rtest) plus the stest <-> xpaset/xpaget/ctest
# round trip documented in doc/examples.html.  Every client call is wrapped in
# a bounded wait so a dead socket fails the build instead of eating the whole
# W3 timeout budget.
set -eu

cd "$(dirname "$0")"
SCRATCH="${TMPDIR:-$HOME/tmp}/xpa-upstream-$$"
mkdir -p "$SCRATCH"
SP=""
NS=""

cleanup() {
    if [ -n "${NS:-}" ]; then
        kill "$NS" 2>/dev/null || true
        wait "$NS" 2>/dev/null || true
    fi
    if [ -n "$SP" ]; then
        kill "$SP" 2>/dev/null || true
        wait "$SP" 2>/dev/null || true
    fi
    # xpans daemonizes and records its pid; leave no nameserver behind for the
    # test_package run, which starts its own.
    if [ -f .xpansPID ]; then
        kill "$(cat .xpansPID)" 2>/dev/null || true
        rm -f .xpansPID
    fi
    rm -rf "$SCRATCH"
}
trap cleanup EXIT INT TERM

# run_bounded <seconds> <command...>
run_bounded() {
    _limit=$1
    shift
    "$@" &
    _pid=$!
    _i=0
    while kill -0 "$_pid" 2>/dev/null; do
        _i=$((_i + 1))
        if [ "$_i" -gt "$_limit" ]; then
            echo "FAIL: timed out after ${_limit}s: $*"
            kill -9 "$_pid" 2>/dev/null || true
            return 1
        fi
        sleep 1
    done
    wait "$_pid"
}

# xpans runs in the foreground on OHOS (a nameserver never exits on its
# own): launch it in the background and probe liveness instead of waiting
# for an exit that never comes (run_bounded would kill the build at 30s).
./xpans >"$SCRATCH/xpans.log" 2>&1 &
NS=$!
sleep 3
if ! kill -0 "$NS" 2>/dev/null; then
    echo "FAIL: xpans did not start"
    cat "$SCRATCH/xpans.log"
    exit 1
fi

# upstream test server: exposes access points xpa and xpa1
./stest >"$SCRATCH/stest.log" 2>&1 &
SP=$!
sleep 2
if ! kill -0 "$SP" 2>/dev/null; then
    echo "FAIL: stest exited immediately"
    cat "$SCRATCH/stest.log"
    exit 1
fi

run_bounded 60 sh -c 'cat xpa.c | ./xpaset xpa'
run_bounded 60 sh -c './xpaget xpa > "$1/get.log" 2>&1' sh "$SCRATCH"
if [ ! -s "$SCRATCH/get.log" ]; then
    echo "FAIL: xpaget xpa returned no data"
    exit 1
fi

run_bounded 90 sh -c './ctest -g -l 3 xpa > "$1/ctest.log" 2>&1' sh "$SCRATCH"
if ! grep -q "received from" "$SCRATCH/ctest.log"; then
    echo "FAIL: ctest produced no XPAGet result"
    cat "$SCRATCH/ctest.log"
    exit 1
fi
_nt=$(grep -c "received from" "$SCRATCH/ctest.log" || true)
echo "UPSTREAM XPA TESTS PASSED: stest + xpaset/xpaget round trip + ctest -g -l 3 (${_nt} XPAGet result lines)"
"""



def _drop_umask_077(path):
    """E114: HMDFS forces setgid on directories; `umask 077 && mktemp -d`
    creates a drwx--S--- temp dir whose files even the owner cannot
    write.  Strip every `(umask 077 && ...)` wrapper from the generated
    configure (matching generically across autoconf generations)."""
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()
    data = re.sub(r"\(umask 077 && ([^()]+)\)", r"\1", data)
    with open(path, "w", encoding="utf-8") as f:
        f.write(data)


def _route_hnp_bash_to_sh(generators_folder):
    """E386 (§12.70①): profile [buildenv] pins SHELL/CONFIG_SHELL to the
    hnp bash, which fails getcwd() inside HMDFS build dirs.  Rewrite the
    aggregated env scripts in place; never re-save_script("conanbuild")
    — a same-named second script sourced into itself recurses forever."""
    if not generators_folder or not os.path.isdir(generators_folder):
        return
    for sh in glob.glob(os.path.join(generators_folder, "**", "*.sh"),
                        recursive=True):
        with open(sh, "r", encoding="utf-8", errors="ignore") as f:
            data = f.read()
        if _HNP_BASH in data:
            with open(sh, "w", encoding="utf-8") as f:
                f.write(data.replace(_HNP_BASH, "/bin/sh"))
    for var in ("SHELL", "CONFIG_SHELL"):
        if os.environ.get(var, "").startswith(_HNP_BASH):
            os.environ[var] = "/bin/sh"


class XpaConan(ConanFile):
    name = "xpa"
    version = "2.1.20"
    description = ("xpa: X Public Access message/passing system for "
                   "seamless communication between Unix programs (SAO)")
    license = "LGPL-2.1-only"
    homepage = "https://github.com/ericmandel/xpa"
    url = ""  # CI fills this

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
        export_conandata_patches(self)

    def requirements(self):
        # socket/nsl/dl/pthread all resolve inside OHOS musl libc;
        # Tcl and X11 are optional upstream probes that degrade cleanly.
        pass

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"xpa is only supported on Linux/OHOS, not {self.settings.os}")

    def layout(self):
        # xpa's generated Makefile carries a "Makefile: Makefile.in" rule
        # with no VPATH support, so an out-of-source build dies with
        # "No rule to make target 'Makefile.in'".  Build in-source so
        # configure output and Makefile.in sit in the same directory
        # (same shape as the libextractor 1.13 recipe).
        basic_layout(self, src_folder=".", build_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # host must canonicalize to aarch64; keep the build triplet gnu
        # per workspace checklist.
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        # upstream default CFLAGS lack -fPIC for the static archive and
        # the release is 2019-era; keep the profile flags in charge.
        tc.generate()

    def build(self):
        _drop_umask_077(os.path.join(self.source_folder, "configure"))
        _route_hnp_bash_to_sh(self.generators_folder)
        autotools = Autotools(self)
        autotools.configure()
        # R9/E074: single job — parallel make hits HMDFS jobserver fifo EPERM
        autotools.make(args=["-j1"])
        # R51/AGENTS §10: upstream tests must really run inside build().
        # xpa has no `make check`; its test entry point is `make testall`
        # (ctest/stest/rtest) plus the stest round trip from examples.html.
        autotools.make(args=["-j1", "testall"])
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        sh = os.path.join(self.build_folder, "run_upstream_tests.sh")
        save(self, sh, _UPSTREAM_TESTS_SH)
        os.chmod(sh, 0o755)
        self.run("sh \"%s\"" % sh)

    def package(self):
        autotools = Autotools(self)
        # xpa's Makefile stages through its own INSTALL_ROOT variable
        # (Makefile.in:37, prepended to prefix/exec_prefix) and ignores
        # DESTDIR, so conan's default `make install DESTDIR=<pkg>` wrote
        # to //include and //lib ("mkdir: Permission denied", read-only fs).
        root = self.package_folder.replace("\\", "/")
        autotools.install(args=["INSTALL_ROOT=%s" % root])

    def package_info(self):
        self.cpp_info.libs = ["xpa"]
        # xpa also ships CLI tools (xpans/xpaget/xpaset/xpaaccess/xpainfo/
        # xpamb) in bin/.  VirtualRunEnv only aggregates a dependency's
        # cpp_info into the consumer PATH when the require is run=True
        # (tool/shared requires) — a plain library require never gets
        # there, so "command -v xpans" in a consumer test fails even with
        # the binaries installed.  runenv_info is the canonical channel:
        # VirtualRunEnv composes it unconditionally.
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.append_path(
            "PATH", os.path.join(self.package_folder, "bin"))
