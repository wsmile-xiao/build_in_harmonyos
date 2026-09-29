#!/usr/bin/env python3
"""Conan recipe for mklibs 0.1.46 — Debian installer library-reduction toolset.

Upstream: https://salsa.debian.org/installer-team/mklibs (Debian native source
package, no separate upstream tarball).  The source tree ships no generated
configure, so the recipe bootstraps it with autoreconf.

The package installs three command line tools plus the bundled Python package:
  * bin/mklibs-readelf : self-contained C++ ELF reader (libc/libstdc++ only)
  * bin/mklibs         : Python 3 library-reduction driver
  * bin/mklibs-copy    : Python 3 minimal-library-set copier
  * lib/mklibs/python/mklibs : Python package used by mklibs-copy

Build prerequisites (aclocal/automake/libtoolize) are declared as build-context
tool_requires; autoconf/m4/perl come from the OHOS SDK.  See notes.md.
"""
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get, replace_in_file)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class MklibsConan(ConanFile):
    name = "mklibs"
    version = "0.1.46"
    description = ("Debian installer tool that produces cut-down shared libraries "
                   "containing only the routines required by a set of executables")
    license = "GPL-2.0-or-later"
    homepage = "https://salsa.debian.org/installer-team/mklibs"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def build_requirements(self):
        # Autotools bootstrap tools, build context only.  The source tree has
        # no generated configure and the CI clean PATH provides SDK autoconf
        # 2.72 / autoreconf / m4 / perl under /data/service/hnp/bin, but no
        # aclocal/automake/libtoolize.  autoconf/m4 are intentionally NOT
        # declared: autoconf's tool_requires would pull the OHOS-built
        # perl/5.42.2 whose XS .so conflicts with the SDK perl 5.42.0
        # interpreter used by autoreconf (Perl_my_cxt_init: symbol not found).
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        # The Debian source tarball has a single top-level directory
        # (mklibs-0.1.46/), so strip it.
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------ build
    @staticmethod
    def _gnu_triplet(arch):
        triplet = {
            "armv8": "aarch64-unknown-linux-gnu",
            "armv8.3": "aarch64-unknown-linux-gnu",
            "aarch64": "aarch64-unknown-linux-gnu",
            "x86_64": "x86_64-unknown-linux-gnu",
        }.get(str(arch))
        if not triplet:
            raise ConanInvalidConfiguration(f"Unsupported arch: {arch}")
        return triplet

    def _make_shims(self):
        """Build-only helper scripts required by the upstream build.

        * dpkg-parsechangelog: configure.ac derives the package version with
          ``dpkg-parsechangelog | perl -ne ...``; this shim reads the first
          Version from debian/changelog so dpkg-dev is not needed at build time.
        * mktemp: on HMDFS ``mktemp -d`` yields directories the configure
          config.status machinery cannot write into; emulate ``mktemp -d`` with
          mkdir and forward every other invocation to the real mktemp.

        Both live in the Conan build folder and only affect the build
        subprocesses through a PATH prepend (R6: no generated file is edited).
        """
        shim_dir = os.path.join(self.build_folder, "shims")
        os.makedirs(shim_dir, exist_ok=True)

        parse_changelog = os.path.join(shim_dir, "dpkg-parsechangelog")
        with open(parse_changelog, "w", encoding="utf-8") as f:
            f.write('#!/bin/sh\n'
                    "# minimal dpkg-parsechangelog replacement (Version field only)\n"
                    'sed -n "1s/^[^(]*(\\\\([^)]*\\\\)).*/Version: \\\\1/p" debian/changelog\n')
        os.chmod(parse_changelog, 0o755)

        mktemp = os.path.join(shim_dir, "mktemp")
        with open(mktemp, "w", encoding="utf-8") as f:
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
  if (umask 077 && mkdir -p "$cand" 2>/dev/null); then out="$cand"; fi
  i=$((i+1))
done
if [ -n "$out" ]; then
  echo "$out"
  exit 0
fi
exit 1
""")
        os.chmod(mktemp, 0o755)
        return shim_dir

    def generate(self):
        tc = AutotoolsToolchain(self)
        # config.guess (automake 1.18) does not recognise HarmonyOS, so give
        # configure explicit GNU triplets instead of relying on uname probing.
        host = self._gnu_triplet(self.settings.arch)
        build_arch = self.settings_build.get_safe("arch") if self.settings_build else None
        build = self._gnu_triplet(build_arch or self.settings.arch)
        tc.configure_args.extend([f"--build={build}", f"--host={host}"])
        env = tc.environment()
        env.prepend_path("PATH", self._make_shims())
        tc.generate(env=env)

    def build(self):
        apply_conandata_patches(self)
        if not os.path.exists(os.path.join(self.source_folder, "configure")):
            self.run("autoreconf -fi", cwd=self.source_folder, env="conanbuild")
        if not os.path.exists(os.path.join(self.source_folder, "configure")):
            raise ConanException("autoreconf did not produce configure; see build log")
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # Upstream ships two Python entry points with different shebangs
        # (`#! /usr/bin/env python3` and `#!/usr/bin/python3`).  Debian rewrites
        # both via dh_python3; normalise the hard-coded absolute one so the
        # installed tools resolve the interpreter through PATH.
        for name in ("mklibs", "mklibs-copy"):
            script = os.path.join(self.package_folder, "bin", name)
            if os.path.isfile(script):
                replace_in_file(self, script, "#!/usr/bin/python3",
                                "#!/usr/bin/env python3", strict=False)
        copy(self, "debian/copyright", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = []
        # mklibs-copy imports the bundled `mklibs.utils.main` package, which is
        # installed under lib/mklibs/python.
        self.runenv_info.prepend_path(
            "PYTHONPATH",
            os.path.join(self.package_folder, "lib", "mklibs", "python"))
