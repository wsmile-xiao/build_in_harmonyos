#!/usr/bin/env python3
"""Conan recipe for skypat 3.2.0 — C++ performance-analyzing and unit-testing
framework that combines perf_events with plain unit tests (Autotools build).

OHOS adaptation notes:
  * The upstream GitHub archive is a git snapshot: it ships configure.ac and
    Makefile.am but no generated `configure`.  CI clean PATH provides SDK
    autoconf/autoreconf/m4 but lacks aclocal/automake/libtoolize, therefore
    automake/1.18 (aclocal+automake) and libtool/2.5.4 (libtoolize) are
    declared as build_requirements and autogen.sh bootstraps the tree.
  * config.guess cannot identify HarmonyOS (E007): explicit --build/--host
    triplets are passed so configure does not guess.
  * HMDFS quirk: toybox `mktemp -d` creates directories the build user cannot
    write into, which aborts the config.status temporary-directory machinery.
    A build-local mktemp shim (scoped to the conanbuild environment) replaces
    it during configure.
  * zlib is optional upstream and unused by any source file: --without-zlib
    keeps the package free of a link-level dependency on the system zlib.
  * perf_event_open is compiled in (headers are present in the OHOS sysroot)
    but denied at run time with EACCES, so the portability patches turn the
    timed/PERFORM path into a runtime capability probe with a real
    clock-based fallback and honest zero counters instead of reading
    uninitialized buffers.
  * The OHOS profile compiles with -std=c++17, which enforces exception
    specification matching: Mutex::tryLock() lacked the 'throw()' from its
    declaration, so a patch restores the match (upstream declares lock/
    unlock/tryLock all with throw()).
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class SkypatConan(ConanFile):
    name = "skypat"
    version = "3.2.0"
    description = ("C++ performance analyzing and testing framework "
                   "(perf_events + unit tests)")
    license = "BSD-3-Clause"
    homepage = "https://github.com/skymizer/SkyPat"
    url = "https://github.com/skymizer/SkyPat"
    topics = ("testing", "unit-test", "performance", "framework")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "skypat supports Linux/OHOS only (Unix/posix sources)")

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # Autotools bootstrap tools (build context only).  CI clean PATH has
        # SDK autoconf/autoreconf/m4 but no aclocal/automake/libtoolize;
        # automake/1.18 ships aclocal+automake and libtool/2.5.4 ships
        # libtoolize for autogen.sh.
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _mktemp_wrapper_dir(self):
        """Return a directory holding a `mktemp` shim for the conanbuild PATH.

        toybox `mktemp -d` on HMDFS creates dirs (drwx--S---) the build user
        cannot write into, so config.status aborts with "could not setup
        config files machinery".  The shim emulates `mktemp -d` with mkdir
        (writable dirs) and forwards everything else to the real mktemp.
        """
        real = shutil.which("mktemp") or "/usr/bin/mktemp"
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
  exec %s "$@"
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
  cand="$base/$(echo "$pat" | sed "s/XXXXXX/$$-$i/")"
  if mkdir -p "$cand" 2>/dev/null; then out="$cand"; fi
  i=$((i+1))
done
if [ -n "$out" ]; then
  echo "$out"
  exit 0
fi
exit 1
""" % real)
            os.chmod(wrapper, 0o755)
        return wrapper_dir

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--build=aarch64-unknown-linux-gnu",
            "--host=aarch64-unknown-linux-gnu",
            "--without-zlib",
            "--enable-clock_gettime",
        ])
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--enable-static", "--disable-shared"])

        env = tc.environment()
        env.prepend_path("PATH", self._mktemp_wrapper_dir())
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env.define("TMPDIR", tmpdir)
        bash = shutil.which("bash") or "/bin/sh"
        env.define("CONFIG_SHELL", bash)
        env.define("SHELL", bash)
        tc.generate(env=env)

    def build(self):
        apply_conandata_patches(self)
        # Git-snapshot archive: bootstrap configure with autogen.sh.  Run it
        # through `bash -e` so aclocal/automake/libtoolize failures abort
        # instead of continuing to a missing configure.
        bash = shutil.which("bash") or "/bin/sh"
        configure = os.path.join(self.source_folder, "configure")
        if not os.path.exists(configure):
            autogen = os.path.join(self.source_folder, "autogen.sh")
            self.run(f"{bash} -e {autogen}", cwd=self.source_folder,
                     env="conanbuild")
        if not os.path.exists(configure):
            raise ConanException(
                "autogen.sh did not produce configure; see build log")

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        autotools = Autotools(self)
        autotools.install()
        for la in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(la)

    def package_info(self):
        self.cpp_info.libs = ["skypat"]
        self.cpp_info.set_property("cmake_file_name", "skypat")
        self.cpp_info.set_property("cmake_target_name", "skypat::skypat")
        self.cpp_info.set_property("pkg_config_name", "skypat")
