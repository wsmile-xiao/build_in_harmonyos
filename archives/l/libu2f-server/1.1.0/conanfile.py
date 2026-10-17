#!/usr/bin/env python3
"""Conan recipe — libu2f-server 1.1.0

Yubico U2F/FIDO2 server-side library for hardware key authentication.
Build system: GNU Autotools (tarball lacks configure, needs autoreconf).
Produces: libu2f-server (shared/static library) + u2f-server (CLI utility).

OHOS specifics:
  - Tarball from GitHub archive lacks generated configure; bootstrap with
    autoreconf --install (tool_requires automake/1.18 + libtool/2.5.4).
  - musl libc lacks arc4random and __fd_chk symbols present in json-c and
    openssl shared libs; LDFLAGS=-Wl,--allow-shlib-undefined relaxes the
    linker so build succeeds at link time.
  - Patch 0001 adds TRUE/FALSE macro definitions for newer json-c compat.
  - HMDFS: mktemp -d creates dirs with broken perms; mktemp wrapper forces
    mkdir fallback (same pattern as accel-config/dar recipes).
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class Libu2fServerConan(ConanFile):
    name = "libu2f-server"
    version = "1.1.0"
    description = "Yubico U2F/FIDO2 server-side library for hardware key authentication"
    license = "BSD-2-Clause"
    homepage = "https://github.com/Yubico/libu2f-server"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    generators = "PkgConfigDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("json-c/0.17")
        self.requires("openssl/1.1.1w")

    def build_requirements(self):
        # autoreconf needs automake (aclocal+automake) and libtool (libtoolize).
        # autoconf and m4 are provided by the SDK.
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
        """Set up writable TMPDIR and CONFIG_SHELL for HMDFS compatibility."""
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.chmod(tmpdir, 0o755)
        os.environ["TMPDIR"] = tmpdir
        bash = shutil.which("bash") or "/bin/sh"
        os.environ.setdefault("CONFIG_SHELL", bash)
        os.environ.setdefault("SHELL", bash)

        # Discover pkg-config's pkg.m4 for aclocal (PKG_CHECK_MODULES)
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

    def _create_mktemp_wrapper(self):
        """Build-only mktemp wrapper for HMDFS compatibility.

        config.status runs (umask 077 && mktemp -d) which creates dirs
        with broken permissions on HMDFS. The wrapper emulates mktemp -d
        with mkdir (drwxrws--x, writable).
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
        tc = AutotoolsToolchain(self)
        # Relax linker for musl libc missing symbols (arc4random, __fd_chk)
        tc.extra_ldflags.append("-Wl,--allow-shlib-undefined")
        if not self.options.shared:
            tc.configure_args.extend(["--enable-static", "--disable-shared"])
        # config.guess cannot recognize HarmonyOS; pass triplet explicitly.
        if str(self.settings.os) == "OHOS":
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-gnu",
            ])
        env = tc.environment()
        env.prepend_path("PATH", self._create_mktemp_wrapper())
        # configure.ac checks for libssl/libcrypto via pkg-config, but conan's
        # openssl package provides openssl.pc.  Set the env vars to bypass.
        openssl = self.dependencies["openssl"]
        openssl_inc = os.path.join(openssl.package_folder, "include")
        openssl_lib = os.path.join(openssl.package_folder, "lib")
        env.define("LIBSSL_CFLAGS", f"-I{openssl_inc}")
        env.define("LIBSSL_LIBS", f"-L{openssl_lib} -lssl -lcrypto -ldl -lpthread")
        env.define("LIBCRYPTO_CFLAGS", f"-I{openssl_inc}")
        env.define("LIBCRYPTO_LIBS", f"-L{openssl_lib} -lcrypto -ldl -lpthread")
        # json-c 0.17 installs headers under include/json-c/ but the .pc file
        # only exports -I${includedir}.  Provide the subdirectory so that
        # #include <json.h> resolves correctly.
        jsonc = self.dependencies["json-c"]
        jsonc_inc = os.path.join(jsonc.package_folder, "include")
        jsonc_inc_sub = os.path.join(jsonc_inc, "json-c")
        jsonc_lib = os.path.join(jsonc.package_folder, "lib")
        env.define("LIBJSON_CFLAGS", f"-I{jsonc_inc} -I{jsonc_inc_sub}")
        env.define("LIBJSON_LIBS", f"-L{jsonc_lib} -ljson-c")
        tc.generate(env=env)

    def build(self):
        bash = self._prepare_build_env()
        apply_conandata_patches(self)
        # Tarball from GitHub archive lacks generated configure; bootstrap.
        if not os.path.exists(os.path.join(self.source_folder, "configure")):
            self.run(f"{bash} -e autoreconf --install",
                     cwd=self.source_folder, env="conanbuild")
        if not os.path.exists(os.path.join(self.source_folder, "configure")):
            raise ConanException(
                "autoreconf did not produce configure; see build log")
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["u2f-server"]
        self.cpp_info.set_property("pkg_config_name", "libu2f-server")
        self.cpp_info.set_property("cmake_file_name", "libu2f-server")
        self.cpp_info.set_property("cmake_target_name", "libu2f-server::libu2f-server")
        self.cpp_info.requires = ["json-c::json-c", "openssl::openssl"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
