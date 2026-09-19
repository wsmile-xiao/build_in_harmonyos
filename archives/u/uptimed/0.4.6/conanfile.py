#!/usr/bin/env python3
"""Conan recipe for uptimed 0.4.6 — uptime record daemon + uprecords (Autotools).

Upstream: https://github.com/rpodgorny/uptimed (tag v0.4.6, GPL-2.0)
Binaries: bin/uprecords (query tool), bin/uptimed (record daemon).

OHOS adaptation (termrec/0.19 + dhcpoptinj/0.5.3 precedents):
- The git-tag archive ships no generated configure — bootstrap with
  upstream autogen.sh (libtoolize/aclocal/autoheader/automake/autoconf).
  tool_requires automake+libtool; autoconf/m4 come from the SDK PATH
  (declaring autoconf pulls an OHOS perl whose XS conflicts with the SDK
  perl used by autom4te — accel-config/termrec precedent).
- configure.ac has no AC_CANONICAL_HOST of its own but AM_PROG_LIBTOOL pulls
  canonicalization in; config.guess cannot classify the OHOS uname, so both
  --build and --host are pinned to aarch64-unknown-linux-gnu. The explicit
  `-linux-` triplet makes configure.ac's `case "$host" in *-linux*)` define
  PLATFORM_LINUX — required for the /proc/uptime boot-time reader in
  libuptimed (urec.c).
- HMDFS: config.status's ``(umask 077 && mktemp -d ...)`` creates unwritable
  0700 dirs (E011) — PATH-scoped mktemp wrapper in the build folder, plus the
  sanctioned `umask 077 -> 022` relax inside the generated configure.
- E386 (§12.38): profile SHELL/CONFIG_SHELL point at hnp bash whose getcwd
  fails in HMDFS build dirs; unset CONFIG_SHELL and route SHELL=/bin/sh.
- `make install` is replaced by explicit pure-Python packaging (HMDFS
  install-sh/chmod class issues, dhcpoptinj precedent).
- Upstream ships no test suite (no tests/ dir; Makefile.am registers no
  check_PROGRAMS/TESTS — audit in test_package/MANIFEST.yml). build() still
  runs the (empty) automake `check` target to prove its shape, and the
  consumer test exercises both packaged binaries for real.
"""
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class UptimedConan(ConanFile):
    name = "uptimed"
    version = "0.4.6"
    description = "Uptime record daemon (uptimed) and top-uptime query tool (uprecords)"
    license = "GPL-2.0-only"
    homepage = "https://github.com/rpodgorny/uptimed"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("uptime", "daemon", "procfs")

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "uptimed is built for Linux/OHOS only")

    def build_requirements(self):
        # Autotools bootstrap tools; autoconf/m4 intentionally from SDK PATH
        # (termrec/accel-config precedent: OHOS perl XS conflict).
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")
        # configure.ac *-linux* branch runs PKG_PROG_PKG_CONFIG.
        self.tool_requires("pkgconf/3.0.5")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _gnu_triplet(self):
        return "aarch64-unknown-linux-gnu"

    def _create_mktemp_wrapper(self):
        """Build-only mktemp wrapper (termrec/0.19 precedent, never committed)."""
        wrapper_dir = os.path.join(self.build_folder, "mktemp-wrapper")
        os.makedirs(wrapper_dir, exist_ok=True)
        wrapper = os.path.join(wrapper_dir, "mktemp")
        if not os.path.exists(wrapper):
            with open(wrapper, "w", encoding="utf-8") as f:
                f.write("""#!/bin/sh
mode=""
for a in "$@"; do
  case "$a" in
    -d) mode="-d" ;;
  esac
done
if [ "$mode" != "-d" ]; then
  exec /usr/bin/mktemp "$@"
fi
dir=""
for a in "$@"; do
  case "$a" in
    -d) ;;
    *)  dir="$a" ;;
  esac
done
[ -n "$dir" ] || dir="./tmp.XXXXXX"
base=$(dirname "$dir")
pat=$(basename "$dir")
out=""
i=0
while [ -z "$out" ] && [ $i -lt 100 ]; do
  cand="$base/$(echo "$pat" | sed "s/XXXXXX/$$-$RANDOM/")"
  if (umask 022 && mkdir -p "$cand" 2>/dev/null); then out="$cand"; fi
  i=$((i+1))
done
if [ -n "$out" ]; then
  echo "$out"
  exit 0
fi
exit 1
""")
            os.chmod(wrapper, 0o755)
        return wrapper_dir

    def generate(self):
        VirtualBuildEnv(self).generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            f"--build={self._gnu_triplet()}",
            f"--host={self._gnu_triplet()}",
        ])
        # Static libuptimed so both binaries are self-contained: OHOS musl
        # ignores DT_RUNPATH, a shared libuptimed would need LD_LIBRARY_PATH
        # everywhere (termrec/0.19 precedent).
        tc.configure_args.extend(["--disable-shared", "--enable-static"])
        env = tc.environment()
        env.prepend_path("PATH", self._create_mktemp_wrapper())
        # E386 (§12.38): route the autotools shell away from hnp bash.
        env.unset("CONFIG_SHELL")
        env.define("SHELL", "/bin/sh")
        tc.generate(env=env)

    def build(self):
        apply_conandata_patches(self)
        # The tag archive has no generated configure: bootstrap it first
        # (autogen.sh is autoreconf-based; explicit /bin/sh, E386).
        if not os.path.exists(os.path.join(self.source_folder, "configure")):
            self.run(
                "env -u CONFIG_SHELL SHELL=/bin/sh /bin/sh -e ./autogen.sh",
                cwd=self.source_folder,
                env="conanbuild",
            )
        if not os.path.exists(os.path.join(self.source_folder, "configure")):
            raise ConanException("autogen.sh did not produce configure")
        # E011/E114 (§12.1): relax config.status umask 077 -> 022 (HMDFS
        # 0700 temp dirs unwritable); build-time only, nothing committed.
        replace_in_file(
            self,
            os.path.join(self.source_folder, "configure"),
            "umask 077",
            "umask 022",
        )
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # Upstream has no tests (no check_* registration); run the (empty)
        # automake check target to prove its shape — R51 honesty: 0 executed.
        autotools.make(target="check")

    def package(self):
        # libtool leaves wrapper scripts in src/ while the real ELFs land in
        # src/.libs/ — package the real binaries (wrapper would fail at
        # runtime pointing into the removed build tree).
        for tool in ("uptimed", "uprecords"):
            src = os.path.join(self.build_folder, "src", ".libs")
            if not os.path.isfile(os.path.join(src, tool)):
                src = os.path.join(self.build_folder, "src")
            copy(self, tool, src=src,
                 dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "*.8", src=os.path.join(self.source_folder, "man"),
             dst=os.path.join(self.package_folder, "share", "man", "man8"),
             keep_path=False)
        copy(self, "*.1", src=os.path.join(self.source_folder, "man"),
             dst=os.path.join(self.package_folder, "share", "man", "man1"),
             keep_path=False)
        copy(self, "uptimed.conf-dist",
             src=os.path.join(self.source_folder, "etc"),
             dst=os.path.join(self.package_folder, "share", "doc", "uptimed"),
             keep_path=False)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
