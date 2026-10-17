#!/usr/bin/env python3
"""Conan recipe — liberasurecode 1.1.1

liberasurecode is an Erasure Code API library in C with pluggable backends.
Autotools project; the upstream v1.1.1 tag tarball ships no generated
configure, so the recipe bootstraps it with autogen.sh (autoreconf) in
build() before configure/make.  On OHOS the SDK config.guess cannot guess
the HarmonyOS build type and toybox mktemp creates unwritable temp dirs,
so the recipe passes explicit --build/--host triplets and prepends a
mktemp wrapper (same pattern as accel-config 4.1.9).
"""
import glob as _glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LiberasurecodeConan(ConanFile):
    name = "liberasurecode"
    version = "1.1.1"
    description = "liberasurecode 1.1.1"
    license = "MIT"
    homepage = "https://github.com/openstack/liberasurecode"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"Unsupported OS: {self.settings.os}")

    def build_requirements(self):
        # Bootstrap tools for autogen.sh (autoreconf).  CI clean PATH lacks
        # aclocal/automake/libtoolize (same rationale as accel-config 4.1.9).
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        # In-source build: upstream test/Makefile links tests against
        # $(top_srcdir)/src/liberasurecode.la, which only resolves when the
        # build happens in the source tree (kismet pattern).
        basic_layout(self, src_folder=".", build_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _prepare_build_env(self):
        """Shared tmpdir + bash detection for autogen/configure subprocesses."""
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.chmod(tmpdir, 0o755)
        os.environ["TMPDIR"] = tmpdir
        bash = shutil.which("bash") or "/bin/sh"
        os.environ.setdefault("CONFIG_SHELL", bash)
        os.environ.setdefault("SHELL", bash)
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
        files machinery".  The wrapper emulates ``mktemp -d`` with mkdir
        (writable) and prints the created path; non ``-d`` invocations are
        forwarded to the real mktemp.  Scoped to the conanbuild environment
        via PATH prepend; nothing outside the build folder is touched.
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
        self._prepare_build_env()
        host_triplet = self._gnu_triplet()
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            f"--build={host_triplet}",
            f"--host={host_triplet}",
        ])
        if not self.options.shared:
            # Upstream plugin architecture dlopen()s backend shared libraries
            # (libnullcode.so.1, libXorcode.so.1, ...) at runtime even for a
            # statically-linked main library; keep building both so the
            # packaged backends remain loadable (verified: with only
            # --disable-shared, instance_create() fails with
            # EBACKENDNOTAVAIL=-204 because the backend .so is absent).
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--enable-shared")
        env = tc.environment()
        env.prepend_path("PATH", self._create_mktemp_wrapper())
        tc.generate(env=env)

    def build(self):
        self._prepare_build_env()
        apply_conandata_patches(self)
        # Upstream tag tarball has no generated configure; bootstrap it.
        configure = os.path.join(self.source_folder, "configure")
        if not os.path.exists(configure):
            self.run("bash -e autogen.sh", cwd=self.source_folder,
                     env="conanbuild")
        if not os.path.exists(configure):
            raise ConanException("autogen.sh did not produce configure")
        # OHOS/HMDFS: autoreconf-generated helpers must be executable.
        for helper in ("configure", "config.guess", "config.sub",
                       "install-sh", "missing", "depcomp", "ltmain.sh"):
            p = os.path.join(self.source_folder, helper)
            if os.path.exists(p):
                os.chmod(p, 0o755)
        # E114: config.status creates tmp dirs via ``(umask 077 && mktemp -d
        # "./confXXXXXX")``; on OHOS/HMDFS that yields drwx--S--- dirs the
        # build user cannot write into ("could not setup config files
        # machinery").  Replace with a mkdir-based tmp creation (4ti2
        # pattern), scoped to the generated configure only.
        _configure = os.path.join(self.source_folder, "configure")
        if self.settings.os == "OHOS" and os.path.exists(_configure):
            with open(_configure, "r", encoding="utf-8", errors="ignore") as f:
                _text = f.read()
            _old = 'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&\n  test -d "$tmp"'
            _new = 'tmp="./conf$$-$RANDOM"\n  (mkdir "$tmp" 2>/dev/null)\n  test -d "$tmp"'
            if _old in _text:
                _text = _text.replace(_old, _new)
                with open(_configure, "w", encoding="utf-8") as f:
                    f.write(_text)
            else:
                self.output.warn("OHOS tmp patch: pattern not found in configure")
        # E063: upstream -Wall -Werror turns set-but-unused / unused locals
        # in the test harness into hard errors under SDK clang 15.  Keep
        # -Werror but downgrade exactly those two categories (upstream tests
        # are untouched; warnings remain).
        if self.settings.os == "OHOS" and os.path.exists(_configure):
            with open(_configure, "r", encoding="utf-8", errors="ignore") as f:
                _text = f.read()
            _old_w = 'werror_flag="-Werror"'
            _new_w = ('werror_flag="-Werror '
                      '-Wno-error=unused-but-set-variable '
                      '-Wno-error=unused-variable"')
            if _old_w in _text:
                _text = _text.replace(_old_w, _new_w, 1)
                with open(_configure, "w", encoding="utf-8") as f:
                    f.write(_text)
            else:
                self.output.warn("E063 werror patch: pattern not found")
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=f"{self.package_folder}/licenses", keep_path=False)
        copy(self, "COPYING", src=self.source_folder,
             dst=f"{self.package_folder}/licenses", keep_path=False)
        # Upstream builds the top-level lib as ``liberasurecode.la`` so the
        # installed archive lacks the conventional ``lib`` prefix; CMakeDeps
        # consumers (find_library) only resolve lib-prefixed names.  Rename
        # to the standard name and drop libtool *.la wrappers (Conan 2
        # copy() has no delete= argument; same cleanup as a52dec).
        _lib_dir = os.path.join(self.package_folder, "lib")
        _bare = os.path.join(_lib_dir, "liberasurecode.a")
        _prefixed = os.path.join(_lib_dir, "libliberasurecode.a")
        if os.path.exists(_bare) and not os.path.exists(_prefixed):
            os.rename(_bare, _prefixed)
        # backends/xor pulls xor_code symbols from the builtin xor_codes
        # archive; normalize that one too so consumers link ALL internal
        # static archives (declared in package_info) by lib-prefixed names.
        _rsv = os.path.join(_lib_dir, "liberasurecode_rs_vand.a")
        _rsv_p = os.path.join(_lib_dir, "libliberasurecode_rs_vand.a")
        if os.path.exists(_rsv) and not os.path.exists(_rsv_p):
            os.rename(_rsv, _rsv_p)
        for _la in _glob.glob(os.path.join(_lib_dir, "*.la")):
            os.remove(_la)

    def package_info(self):
        # Static archives reference each other (flat_xor_hd in the main lib
        # uses xor_code symbols from builtin/xor_codes, etc.), so consumers
        # must link the full internal archive set in dependency order.
        self.cpp_info.libs = ["liberasurecode", "Xorcode", "nullcode",
                              "liberasurecode_rs_vand"]
        self.cpp_info.system_libs = ["dl", "pthread", "m"]
        self.cpp_info.includedirs = ["include"]
        # Runtime dlopen() of the backend shared libraries needs the package
        # lib dir on LD_LIBRARY_PATH inside the conanrun environment.
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))