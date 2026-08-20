#!/usr/bin/env python3
"""Conan recipe for epeg 0.9.3 — Enlightenment JPEG thumbnailer library.

epeg is an insanely fast JPEG/JPG thumbnail scaling library built on
libjpeg-turbo and libexif.  Build system is Autotools (configure.ac +
Makefile.am + autogen.sh); the GitHub tag archive ships NO pre-generated
configure script, so autogen.sh (aclocal → autoheader → autoconf →
libtoolize → automake) must run first with NOCONFIGURE=1 to generate
configure, then Autotools.configure() invokes it.

HarmonyOS adaptations:
  - The 2003-era config.guess does not recognize OHOS; pass
    --build=aarch64-unknown-linux-gnu (native build, compatible tuple).
  - CONFIG_SHELL / SHELL pointed at the SDK bash so autotools-generated
    scripts execute via bash instead of the shebang interpreter.
  - TMPDIR set to a writable build-local dir (HMDFS /tmp is read-only).
  - An mktemp wrapper forces autoconf's config.status temp-dir creation to
    use mkdir with sane permissions (toybox mktemp -d creates drwx--S---
    dirs that the build user cannot write into on HMDFS).
  - The generated configure/Makefile.in use umask 077 for temp dirs; patched
    to umask 022 to prevent Permission denied on HMDFS (same fix as
    libiconv/eb E011).
  - ACLOCAL/AUTOMAKE/AUTOCONF/AUTOHEADER/AUTOM4TE set to ':' (no-op) after
    configure generation so make cannot trigger aclocal.m4 rebuild rules
    that would invoke missing aclocal-1.16 (not installed on CI worker).
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class EpegConan(ConanFile):
    name = "epeg"
    version = "0.9.3"
    description = "Insanely fast JPEG/JPG thumbnail scaling library"
    license = "MIT-ENNA"
    homepage = "https://github.com/mattes/epeg"
    url = "https://github.com/mattes/epeg"
    topics = ("jpeg", "thumbnail", "image", "scaling", "enlightenment")
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires(
            "libjpeg-turbo/3.2.0",
            transitive_headers=True,
            transitive_libs=True,
        )
        self.requires(
            "libexif/0.6.26.1",
            transitive_headers=True,
            transitive_libs=True,
        )

    def build_requirements(self):
        # GitHub tag archive ships no pre-generated configure; autogen.sh
        # (aclocal/autoheader/autoconf/libtoolize/automake) needs automake
        # (aclocal+automake) and libtool (libtoolize).  autoconf/m4 are
        # provided by the SDK (/data/service/hnp/bin); declaring autoconf
        # would pull OHOS-built perl whose XS .so conflicts with SDK perl.
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("epeg supports Linux and OHOS only")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(
            self,
            **self.conan_data["sources"],
            filename="epeg-0.9.3.tar.gz",
            strip_root=True,
        )

    # ── OHOS build helpers ──────────────────────────────────────────

    def _gnu_build_triplet(self):
        arch = str(self.settings.arch)
        triplets = {
            "armv8": "aarch64-unknown-linux-gnu",
            "armv8.3": "aarch64-unknown-linux-gnu",
            "aarch64": "aarch64-unknown-linux-gnu",
            "x86_64": "x86_64-unknown-linux-gnu",
        }
        triplet = triplets.get(arch)
        if not triplet:
            raise ConanInvalidConfiguration(f"Unsupported arch: {arch}")
        return triplet

    def _create_mktemp_wrapper(self):
        """Build-only mktemp wrapper for HMDFS permission fix.

        config.status in the autogen-generated configure runs
        ``(umask 077 && mktemp -d "./confXXXXXX")``.  On OHOS/HMDFS the
        toybox mktemp creates drwx--S--- directories that the build user
        cannot write into, so configure aborts.  The wrapper emulates
        ``mktemp -d`` with mkdir (writable) and prints the path; non -d
        calls are forwarded to the real mktemp.  Scoped to conanbuild PATH.
        """
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
  exec mktemp "$@"
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
        AutotoolsDeps(self).generate()

        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(
            [
                "--prefix=/",
                "--enable-static",
                "--disable-shared",
            ]
        )

        env = tc.environment()

        # OHOS loader has no default search path for conan-cached shared
        # libs (libjpeg-turbo ships libjpeg.so as shared). configure's
        # conftest runs compiled programs, which fail with "Error loading
        # shared library libjpeg.so.62" unless LD_LIBRARY_PATH points at
        # the dependency lib dirs.
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                env.prepend_path("LD_LIBRARY_PATH", libdir)

        if self.settings.os == "OHOS":
            # The 2003 config.guess does not recognize HarmonyOS; native
            # build so a compatible build tuple is sufficient.
            tc.configure_args.append(f"--build={self._gnu_build_triplet()}")

            bash = (
                os.environ.get("CONFIG_SHELL")
                or shutil.which("bash")
                or "/data/service/hnp/bin/bash"
            )
            tc.configure_args.append(f"SHELL={bash}")

            tmpdir = os.path.join(self.build_folder, "tmp")
            os.makedirs(tmpdir, exist_ok=True)
            os.chmod(tmpdir, 0o755)
            env.define_path("TMPDIR", tmpdir)
            env.define_path("CONFIG_SHELL", bash)
            env.define_path("SHELL", bash)

            # mktemp wrapper: force sane perms on HMDFS
            env.prepend_path("PATH", self._create_mktemp_wrapper())

        tc.generate(env=env)

        # Also persist TMPDIR/SHELL/CONFIG_SHELL/LD_LIBRARY_PATH for the
        # autoreconf run which happens before Autotools.configure().
        if self.settings.os == "OHOS":
            bash = (
                os.environ.get("CONFIG_SHELL")
                or shutil.which("bash")
                or "/data/service/hnp/bin/bash"
            )
            tmpdir = os.path.join(self.build_folder, "tmp")
            os.makedirs(tmpdir, exist_ok=True)
            os.chmod(tmpdir, 0o755)
            env2 = Environment()
            env2.define_path("TMPDIR", tmpdir)
            env2.define_path("CONFIG_SHELL", bash)
            env2.define_path("SHELL", bash)
            env2.prepend_path("PATH", self._create_mktemp_wrapper())
            for dep in self.dependencies.values():
                for libdir in dep.cpp_info.libdirs:
                    env2.prepend_path("LD_LIBRARY_PATH", libdir)
            env2.vars(self).save_script("epeg_build_env")

    def build(self):
        apply_conandata_patches(self)

        # The GitHub tag archive ships no pre-generated configure; the
        # upstream autogen.sh calls bare `aclocal`/`automake` (binary names,
        # not $ACLOCAL/$AUTOMAKE), which resolves to broken system copies
        # (aclocal-1.16/1.17 without matching share/aclocal-1.18 dirs).
        # Use `autoreconf -fi` instead — it honours the ACLOCAL/AUTOMAKE env
        # vars set by the automake/1.18 tool_require, and runs the same
        # aclocal → autoheader → autoconf → libtoolize → automake sequence.
        if not os.path.isfile(os.path.join(self.source_folder, "configure")):
            self.run(
                "autoreconf -fi",
                cwd=self.source_folder,
                env=["conanbuild", "epeg_build_env"],
            )
        if not os.path.isfile(os.path.join(self.source_folder, "configure")):
            raise ConanInvalidConfiguration(
                "autoreconf did not produce configure; see build log"
            )

        # E011: autotools-generated configure uses umask 077 for temp dirs,
        # causing Permission denied on HMDFS. Patch to umask 022.
        for fname in ["configure"]:
            fpath = os.path.join(self.source_folder, fname)
            if os.path.isfile(fpath):
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read()
                if "umask 077" in content:
                    replace_in_file(self, fpath, "umask 077", "umask 022")

        # Prevent make from triggering aclocal.m4 / configure rebuild rules
        # that invoke missing aclocal-1.16 (not installed on CI worker).
        os.environ["ACLOCAL"] = ":"
        os.environ["AUTOMAKE"] = ":"
        os.environ["AUTOCONF"] = ":"
        os.environ["AUTOHEADER"] = ":"
        os.environ["AUTOM4TE"] = ":"

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = ["epeg"]
        # libjpeg-turbo and libexif declare no explicit components; in
        # Conan 2.x the implicit component name equals the package name,
        # so reference them as package::package for transitive linking.
        self.cpp_info.requires = ["libjpeg-turbo::libjpeg-turbo", "libexif::libexif"]
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.set_property("cmake_file_name", "epeg")
        self.cpp_info.set_property("cmake_target_name", "epeg::epeg")
        self.cpp_info.set_property("pkg_config_name", "epeg")
