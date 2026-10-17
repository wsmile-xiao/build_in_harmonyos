#!/usr/bin/env python3
"""Conan recipe for LPRng 3.8.b on HarmonyOS PC (OHOS, aarch64).

LPRng is a print spooler suite: it installs programs (lpr, lpq, lprm,
lpstat, lpc, checkpc, lprng_certs, lprng_index_certs) plus runtime
config files under etc/lpd, not a linkable library.

Platform adaptations (evidence in notes.md and manifest.yaml):
- E490 restore-known-autotools-script-modes: HMDFS extraction loses +x
  on autotools helper scripts; restore bits before configure.
- HMDFS 0700-dir ACL defect: a directory created with owner-only mode
  (toybox mkdtemp, or an autoconf config.status tmp dir made under
  umask 077) is born with a broken ACL: even the owner cannot write
  and chmod cannot repair it.  config.status then silently loses EVERY
  generated file (Makefile, config.h, ...) while still exiting 0.
  Fix with a recipe-local mktemp shim (E528-style env closure): the
  shim recreates the temp dir under a FRESH name with mode 755 and
  verifies a probe write before reporting success.  The shim dir is
  injected into PATH via an inline command prefix (mirrors the
  libunwind 1.6.2 recipe pattern).
- clang 15 defaults to -fno-common while LPRng 3.8.B (2003) defines
  globals in headers (lp.h): build with -fcommon, else the link stage
  fails with multiple-definition errors (vars.o / checkpc).
- An install shim is provided because the autoconf-detected
  BSD-install may resolve to a bare install name that does not exist
  on OHOS runners; ginstall from coreutils is the working backend.
"""
import os
import shlex

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

MKTEMP_SHIM = """#!/bin/sh
# OHOS/HMDFS: dirs created with owner-only mode are born unwritable.
# Recreate under a FRESH name with mode 755 and probe-verify; on failure
# exit 1 so callers with a mkdir fallback can proceed.
REAL=/usr/bin/mktemp
isdir=0
for a in "$@"; do
  case "$a" in
  -d|--directory) isdir=1 ;;
  --) break ;;
  esac
done
if [ "$isdir" = 0 ]; then
  exec "$REAL" "$@"
fi
T=".mktemp_shim_out.$$"
"$REAL" "$@" > "$T"
rc=$?
if [ "$rc" -ne 0 ]; then rm -f "$T"; exit "$rc"; fi
read out < "$T"
rm -f "$T"
if [ -z "$out" ]; then
  exit 1
fi
rmdir "$out" 2>/dev/null
new=$out.mshim
mkdir -m 755 "$new" || exit 1
ok=0
for try in 1 2 3 4 5; do
  if echo x > "$new/.shim_probe" 2>/dev/null; then ok=1; break; fi
  sleep 1
done
rm -f "$new/.shim_probe" 2>/dev/null
if [ "$ok" = 0 ]; then
  rmdir "$new" 2>/dev/null
  exit 1
fi
echo "$new"
"""

LN_SHIM = """#!/bin/sh
# OHOS/HMDFS shim: hard links fail with Operation not permitted.
# Turn ln into a copy.  Flags (-f -s ...) are dropped; the common
# 2-operand form (ln src dst) and the N-operand into-dir form map to cp.
operands=
for a in "$@"; do
  case "$a" in
  -*) ;;
  *) operands="$operands $a" ;;
  esac
done
set -- $operands
if [ "$#" -lt 2 ]; then
  echo "lprng recipe ln shim: expected at least 2 operands" >&2
  exit 1
fi
if [ "$#" -eq 2 ]; then
  if [ -d "$2" ]; then
    cp "$1" "$2/" || exit 1
  else
    cp "$1" "$2" || exit 1
  fi
  exit 0
fi
dst=$3
shift 2
for src in "$@"; do
  cp "$src" "$dst/" || exit 1
done
exit 0
"""

INSTALL_SHIM = """#!/bin/sh
# lprng recipe install shim - ordered fallback chain (CI workers may
# carry neither `install` nor `ginstall`).  Every candidate is probed
# before exec; the chosen backend is logged so CI logs show the hop.
log_backend() {
  echo "lprng recipe install shim: backend=$1" >&2
}
# 1) install (GNU semantics) - first PATH hit OUTSIDE the wrapper dir.
#    The wrapper dir is PREPENDED to PATH so the Makefile resolves
#    `install` to this very shim; exec-ing the probe hit would recurse
#    forever (busy-spin seen in G2, 2026-09-28), so walk PATH by hand
#    and skip the directory this shim lives in.
cand=
self_dir=${0%/*}
if [ "$self_dir" = "$0" ]; then
  self_dir=
fi
oldIFS=$IFS
IFS=:
for d in $PATH; do
  if [ -n "$d" ] && [ "$d" != "$self_dir" ] && [ -x "$d/install" ]; then
    cand=$d/install
    break
  fi
done
IFS=$oldIFS
if [ -n "$cand" ]; then
  log_backend "$cand"
  exec "$cand" "$@"
fi
# 2) ginstall - GNU coreutils alternate name (B device keeps it at
#    $HOME/usr/local/bin/ginstall, outside PATH).
if [ -x "$HOME/usr/local/bin/ginstall" ]; then
  log_backend "$HOME/usr/local/bin/ginstall"
  exec "$HOME/usr/local/bin/ginstall" "$@"
fi
if command -v ginstall >/dev/null 2>&1; then
  log_backend ginstall
  exec ginstall "$@"
fi
if [ -x /usr/bin/ginstall ]; then
  log_backend /usr/bin/ginstall
  exec /usr/bin/ginstall "$@"
fi
# 3) busybox install - minimal (Alpine-style) workers; --list proves
#    the applet is compiled in.
if command -v busybox >/dev/null 2>&1 && busybox --list 2>/dev/null | grep -q "^install$"; then
  log_backend busybox-install
  exec busybox install "$@"
fi
# 4) toybox install - applet probe; unknown applet exits non-zero.
if command -v toybox >/dev/null 2>&1 && toybox install --help >/dev/null 2>&1; then
  log_backend toybox-install
  exec toybox install "$@"
fi
# 5) pure-sh fallback: mkdir -p the target dir, cp -p, then chmod
#    755/644 by source mode (-m MODE wins when given).  The LPRng
#    Makefile call surface is only `-c ...` and `-c -m MODE ...`
#    (INSTALL_PROGRAM=${INSTALL}, INSTALL_DATA=${INSTALL} -m 644);
#    -d is handled anyway and bare two-operand calls are accepted.
#    No $() anywhere: same erofs-/tmp constraint as test_package.
log_backend pure-sh-fallback
mode=
dirs=0
while [ "$#" -gt 0 ]; do
  case "$1" in
  -c) ;;
  -m) mode=$2; shift ;;
  -d) dirs=1 ;;
  -*) ;;  # tolerated no-ops outside the call surface (-s -p -b -g -o)
  *) break ;;
  esac
  shift
done
if [ "$dirs" = 1 ]; then
  if [ "$#" -lt 1 ]; then
    echo "lprng recipe install shim: fallback -d needs operands" >&2
    exit 2
  fi
  for d in "$@"; do
    mkdir -p "$d" || exit 1
  done
  exit 0
fi
if [ "$#" -lt 2 ]; then
  echo "lprng recipe install shim: fallback needs src and dst" >&2
  exit 2
fi
n=$#
i=0
dst=
for a in "$@"; do
  i=$((i+1))
  if [ "$i" -eq "$n" ]; then
    dst=$a
  fi
done
rc=0
i=0
for a in "$@"; do
  i=$((i+1))
  if [ "$i" -eq "$n" ]; then
    continue
  fi
  if [ -d "$dst" ]; then
    base=${a##*/}
    target=$dst/$base
  elif [ "$n" -gt 2 ]; then
    echo "lprng recipe install shim: fallback: $dst is not a directory" >&2
    exit 1
  else
    target=$dst
  fi
  dir=${target%/*}
  if [ "$dir" = "$target" ]; then
    dir=.
  fi
  mkdir -p "$dir" || exit 1
  cp -p "$a" "$target" || { rc=1; continue; }
  if [ -n "$mode" ]; then
    chmod "$mode" "$target" || rc=1
  elif [ -x "$a" ]; then
    chmod 755 "$target" || rc=1
  else
    chmod 644 "$target" || rc=1
  fi
done
exit $rc
"""


class LprngConan(ConanFile):
    name = "lprng"
    version = "3.8.b"
    description = "LPRng - an extended scalable print spooler for UNIX-like systems"
    license = "GPL-2.0-or-later OR Artistic"
    homepage = "https://lprng.sourceforge.net"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # kerberos and tcp-wrappers are off by default upstream; ssl and
        # nls are cut to avoid openssl/gettext dependencies.
        tc.configure_args.append("--disable-ssl")
        tc.configure_args.append("--disable-nls")
        # E: multiple-definition at link with clang 15 (-fno-common default)
        tc.extra_cflags = ["-fcommon"]
        tc.generate()
        self._configure_args = list(tc.configure_args)

        if self.settings.os != "OHOS":
            return
        self._write_wrappers()

    def _wrapper_dir(self):
        return os.path.join(self.build_folder, "ohc-wrappers").replace("\\\\", "/")

    def _write_wrappers(self):
        wrapper_dir = self._wrapper_dir()
        os.makedirs(wrapper_dir, exist_ok=True)
        for name, body in (("mktemp", MKTEMP_SHIM), ("install", INSTALL_SHIM), ("ln", LN_SHIM)):
            path = os.path.join(wrapper_dir, name)
            with open(path, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(body)
            os.chmod(path, 0o755)

    def _ohos_env_prefix(self):
        return "PATH={}:$PATH".format(shlex.quote(self._wrapper_dir()))

    def _restore_helper_exec_bits(self):
        names = [
            "configure",
            "config.guess",
            "config.sub",
            "install-sh",
            "missing",
            "depcomp",
            "mkinstalldirs",
        ]
        for name in names:
            path = os.path.join(self.source_folder, name)
            if os.path.isfile(path):
                os.chmod(path, 0o755)

    def build(self):
        apply_conandata_patches(self)
        if self.settings.os == "OHOS":
            self._restore_helper_exec_bits()
            self._write_wrappers()
            configure = os.path.join(self.source_folder, "configure").replace("\\\\", "/")
            args = " ".join(shlex.quote(str(a)) for a in self._configure_args)
            self.run(
                "{} sh {} {}".format(self._ohos_env_prefix(), shlex.quote(configure), args),
                cwd=self.build_folder,
                env="conanbuild",
            )
            self.run(
                "{} make -j1".format(self._ohos_env_prefix()),
                cwd=self.build_folder,
                env="conanbuild",
            )
        else:
            autotools = Autotools(self)
            autotools.configure()
            autotools.make(args=["-j1"])

    def package(self):
        if self.settings.os == "OHOS":
            # conan 2 toolchain configures with --prefix=/ ; the standard
            # relocatable install is DESTDIR=package_folder (bin, sbin, etc
            # land at the package root).
            destdir = "DESTDIR={}".format(shlex.quote(self.package_folder))
            self.run(
                "{} make install {}".format(self._ohos_env_prefix(), destdir),
                cwd=self.build_folder,
                env="conanbuild",
            )
        else:
            Autotools(self).install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
