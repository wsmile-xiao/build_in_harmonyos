#!/usr/bin/env python3
"""Conan recipe for accel-config 4.1.9 (intel/idxd-config) — Autotools.

Produces libaccel-config (shared library), public headers, pkg-config metadata
and the accel-config CLI.  Build prerequisites (automake/aclocal/libtoolize/
autoconf, pkg-config, clang OHOS toolchain) must be available on PATH.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class AccelConfigConan(ConanFile):
    name = "accel-config"
    version = "4.1.9"
    description = "Intel DSA/IAA accelerator configuration utility and library (libaccel-config)"
    license = "GPL-2.0"
    homepage = "https://github.com/intel/idxd-config"
    url = "https://github.com/intel/idxd-config"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}
    generators = "PkgConfigDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("json-c/0.17")
        self.requires("uuid/2.40.1")

    def build_requirements(self):
        # Autotools bootstrap tools (build context only, never runtime
        # requires).  CI clean PATH has SDK autoconf 2.72 / autoreconf / m4 /
        # perl (5.42.0) under /data/service/hnp/bin, but lacks
        # aclocal/automake/libtoolize.  automake/1.18 ships aclocal+automake
        # (with its own PERL5LIB pointing at its share dir) and libtool/2.5.4
        # ships libtoolize.  autoconf/2.72 and m4/1.4.19 are intentionally NOT
        # declared: autoconf's tool_requires would pull OHOS-built
        # perl/5.42.2 whose XS .so conflicts with the SDK perl 5.42.0
        # interpreter used by SDK autoreconf (Perl_my_cxt_init: symbol not
        # found), and SDK already provides both autoconf and m4.
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"Unsupported OS: {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _prepare_build_env(self):
        """Shared tmpdir + bash detection + pkg.m4 aclocal path.

        The Autotools bootstrap tools automake/1.18 and libtool/2.5.4 are
        declared in build_requirements(); their package_info/buildenv_info
        automatically provide PATH, ACLOCAL_PATH, _lt_pkgdatadir,
        autom4te_perllibdir etc. inside the conanbuild environment, so no
        $HOME/autotools or machine-specific path is referenced here.
        autoconf/m4 are provided by the SDK (/data/service/hnp/bin) rather
        than declared (declaring autoconf/2.72 would pull OHOS-built
        perl/5.42.2 whose XS .so conflicts with SDK perl 5.42.0).
        """
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.chmod(tmpdir, 0o755)
        os.environ["TMPDIR"] = tmpdir
        bash = shutil.which("bash") or "/bin/sh"
        os.environ.setdefault("CONFIG_SHELL", bash)
        os.environ.setdefault("SHELL", bash)

        # pkg-config's pkg.m4 (PKG_CHECK_MODULES) lives in the SDK pkg-config
        # install prefix, outside the conan tool graph; discover it instead of
        # hardcoding.  Also append libtool's aclocal dir from the tool graph
        # for robustness (buildenv_info already covers it via conanbuild).
        aclocal_dirs = []
        pkg_config = shutil.which("pkg-config")
        if pkg_config:
            import glob as _glob
            for cand in _glob.glob(os.path.join(
                    os.path.dirname(os.path.dirname(pkg_config)),
                    "pkg-config.org", "pkg-config_*", "share", "aclocal")):
                if os.path.isdir(cand):
                    aclocal_dirs.append(cand)
            cand = os.path.join(
                os.path.dirname(os.path.dirname(pkg_config)), "share", "aclocal")
            if os.path.isdir(cand):
                aclocal_dirs.append(cand)
        for dep in self.dependencies.build.values():
            if dep.ref.name == "libtool":
                cand = os.path.join(dep.package_folder, "share", "aclocal")
                if os.path.isdir(cand):
                    aclocal_dirs.append(cand)
        existing = os.environ.get("ACLOCAL_PATH", "")
        extra = ":".join(d for d in aclocal_dirs if d)
        os.environ["ACLOCAL_PATH"] = ":".join(
            [d for d in [extra, existing] if d])
        return bash

    def _gnu_triplet(self, arch=None):
        arch = str(arch or self.settings.arch)
        arch_triplets = {
            "armv8": "aarch64-unknown-linux-gnu",
            "armv8.3": "aarch64-unknown-linux-gnu",
            "aarch64": "aarch64-unknown-linux-gnu",
            "x86_64": "x86_64-unknown-linux-gnu",
        }
        triplet = arch_triplets.get(arch)
        if not triplet:
            raise ConanInvalidConfiguration(f"Unsupported arch: {arch}")
        return triplet

    def _create_mktemp_wrapper(self):
        """Build-only mktemp wrapper (never committed).

        config.status in the autogen-generated configure runs
        ``(umask 077 && mktemp -d "./confXXXXXX")``.  On OHOS/HMDFS the
        toybox mktemp creates drwx--S--- directories that the build user
        cannot write into, so configure aborts with "could not setup config
        files machinery" regardless of cwd.  The wrapper emulates ``mktemp
        -d`` with mkdir (drwxrws--x, writable) and prints the created path;
        non ``-d`` invocations and bad arguments are forwarded to the real
        mktemp, preserving exit codes.  It only affects the configure /
        autogen subprocesses via a PATH prepend scoped to the conanbuild
        environment; nothing is written to system dirs and no file outside
        the build folder is touched (R6: no generated file is modified).
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
            os.chmod(wrapper, 0o755)
        return wrapper_dir

    def generate(self):
        self._prepare_build_env()
        host_triplet = self._gnu_triplet()
        build_arch = self.settings_build.get_safe("arch") if self.settings_build else None
        build_triplet = self._gnu_triplet(build_arch or self.settings.arch)
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            f"--build={build_triplet}",
            f"--host={host_triplet}",
            "--disable-docs",
            "--disable-test",
            "--with-bash-completion-dir=no",
            "--disable-logging",
        ])
        if not self.options.shared:
            tc.configure_args.extend(["--disable-shared", "--enable-static"])
        env = tc.environment()
        env.prepend_path("PATH", self._create_mktemp_wrapper())
        tc.generate(env=env)

    def build(self):
        bash = self._prepare_build_env()
        # Apply source-tree patches (target files shipped in the tarball).
        apply_conandata_patches(self)
        # The upstream release tarball ships no generated configure; bootstrap
        # it.  Run autogen.sh with `-e` so autoreconf/aclocal failures abort
        # immediately (its `#!/bin/sh -e` shebang is bypassed by the explicit
        # `bash` interpreter) instead of continuing to a missing configure.
        autogen = os.path.join(self.source_folder, "autogen.sh")
        if not os.path.exists(os.path.join(self.source_folder, "configure")):
            self.run(f"{bash} -e {autogen}", cwd=self.source_folder, env="conanbuild")
        if not os.path.exists(os.path.join(self.source_folder, "configure")):
            raise ConanException(
                "autogen.sh did not produce configure; see build log")
        autotools = Autotools(self)
        autotools.configure()
        # Out-of-source quirk: Makefile.am uses `contrib/configs/*` glob
        # resolved against the build dir; mirror the source tree's contrib
        # configs into the build dir so `make` can find them.
        src_cfg = os.path.join(self.source_folder, "contrib", "configs")
        dst_cfg = os.path.join(self.build_folder, "contrib", "configs")
        if os.path.isdir(src_cfg):
            os.makedirs(dst_cfg, exist_ok=True)
            for name in sorted(os.listdir(src_cfg)):
                shutil.copy(os.path.join(src_cfg, name),
                            os.path.join(dst_cfg, name))
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "LICENSE_GPL_2_0", src=self.source_folder,
             dst=f"{self.package_folder}/licenses", keep_path=False)
        copy(self, "accfg/lib/LICENSE_LGPL_2_1", src=self.source_folder,
             dst=f"{self.package_folder}/licenses", keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["accel-config"]
        self.cpp_info.set_property("pkg_config_name", "libaccel-config")
        self.cpp_info.set_property("cmake_file_name", "accel-config")
        self.cpp_info.set_property("cmake_target_name", "accel-config::accel-config")
        # Public header includes <uuid/uuid.h>; CLI links libjson-c.
        self.cpp_info.requires = ["uuid::uuid", "json-c::json-c"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        self.conf_info.define("user.accel-config:cli", "accel-config")
