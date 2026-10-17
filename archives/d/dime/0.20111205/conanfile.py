#!/usr/bin/env python3
"""Conan recipe for dime 0.20111205 (Coin3D DXF library).

DIME ("DXF Import, Manipulation and Export") is a C++ class library for
reading, constructing, manipulating, and writing DXF (Drawing eXchange
Format) files, from the Coin3D / Kongsberg family.

Version 0.20111205 is the 2011-12-05 upstream snapshot (Mercurial r187 of
bitbucket.org/Coin3D/dime, the last change before the repository went
dormant).  The snapshot was never released as a GitHub tag, so the source
URL pins the equivalent git commit edcbe949ae67; the tree is byte-identical
to the Debian 0.20111205.orig tarball (verified: 209 files, only
.hg_archival.txt absent).  The last tagged upstream release, dime-0.9.1
(2002), is much older and misses 9 years of fixes.

Build system: autoconf/automake/libtool 1.5 era, pre-generated configure
shipped in the tarball (no autoreconf needed).  Package content is the
library only: dxf2vrml and dxfsphere are noinst example programs and are
not installed by `make install`.

OHOS adaptations (mirroring the device-validated celt 1.0.0 recipe):
  - generic linux-gnu build/host triplets (2009-era config.guess/config.sub
    accept neither aarch64 nor linux-ohos; dime has no OS-specific code)
  - -fuse-ld=<ld.lld> so configure's compiler/link probes succeed (OHOS
    ships ld.lld only, and clang does not search PATH for linkers)
  - build-local ld/ld.aarch64 shims and build-local TMPDIR (patch 0001;
    OHOS /tmp is read-only)
  - configure run under bash (mksh mishandles config.status temp files)
  - patch 0002 removes the C++17-removed `register` storage class
"""

import hashlib
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    download,
    export_conandata_patches,
    rm,
    unzip,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

# GitHub codeload builds tar.gz archives on the fly and the gzip framing
# of this commit is not byte-stable: two variants were observed on
# 2026-09-12 (plain curl vs conan's python downloader), both holding the
# identical git tree of edcbe949ae67 (209 files, per-file sha256 equal to
# the Debian dime_0.20111205.orig tarball).  source() verifies against
# this set explicitly -- the check is never skipped.
_SOURCE_SHA256 = (
    "6d9f7d0c1ba20f5815c585a33589943d6ba969bc53587269b735c64703c9f3a6",
    "065a7d74d4e1f15244d3a467f8b92e37908f33d4824a528d468379ea868a9914",
)


class DimeConan(ConanFile):
    name = "dime"
    version = "0.20111205"
    description = "DIME - DXF Import, Manipulation and Export (Coin3D C++ library)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/coin3d/dime"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    # R32: platform check must accept OHOS alongside Linux
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        src = self.conan_data["sources"][self.version]
        archive = "dime-0.20111205-src.tar.gz"
        # download() without an in-flight hash, then verify explicitly
        # against _SOURCE_SHA256 (see comment there), then extract.
        download(self, src["url"], archive)
        with open(archive, "rb") as f:
            computed = hashlib.sha256(f.read()).hexdigest()
        if computed not in _SOURCE_SHA256:
            raise ConanException(
                f"dime source archive sha256 {computed} matches neither "
                "known GitHub codeload framing of commit edcbe949ae67 "
                f"({_SOURCE_SHA256[0]} / {_SOURCE_SHA256[1]}); if this is a "
                "new framing variant, verify the tree equals the Debian "
                "dime_0.20111205.orig tarball and extend _SOURCE_SHA256"
            )
        unzip(self, archive, strip_root=True)
        os.remove(archive)
        apply_conandata_patches(self)

    def _compiler_dir(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = executables.get("cpp") or executables.get("c") or "clang++"
        return os.path.dirname(os.path.abspath(cc))

    def _lld_path(self):
        lld = os.path.join(self._compiler_dir(), "ld.lld")
        if os.path.isfile(lld):
            return lld
        import shutil
        for name in ("ld.lld", "ld.aarch64", "ld"):
            found = shutil.which(name)
            if found:
                return found
        return "lld"  # let the compiler report the failure verbatim

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Doxygen HTML docs are off by default; make it explicit.
        tc.configure_args.append("--disable-html")
        # Upstream defaults to AM_DISABLE_STATIC (shared only); select the
        # requested library type explicitly in both directions.
        if self.options.shared:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        else:
            tc.configure_args.append("--disable-shared")
            tc.configure_args.append("--enable-static")
        if str(self.settings.os) == "OHOS":
            # 2009-era config.guess/config.sub recognise neither OHOS nor
            # linux-ohos.  Pin the generic GNU triplet for both build and
            # host; dime is portable C++ with no OS-specific code paths.
            tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
            tc.configure_args.append("--host=aarch64-unknown-linux-gnu")
            # OHOS only ships ld.lld, and clang does not search PATH for
            # linkers, so configure's "compiler works" probe needs the
            # linker spelled out (dime's probes run in C++ mode).  The
            # 2009-era configure rejects unknown -f... command line
            # options, so route the flag through the flags lists instead
            # (configure's probes compile+link in one step, so the flag
            # reaches the linker through CXXFLAGS/CFLAGS/LDFLAGS).
            fuse_ld = f"-fuse-ld={self._lld_path()}"
            tc.extra_cflags.append(fuse_ld)
            tc.extra_cxxflags.append(fuse_ld)
            tc.extra_ldflags.append(fuse_ld)
        tc.generate()
        # Save configure args for build() to replay when running configure
        # under bash on OHOS (see build()).
        args_file = os.path.join(self.build_folder, "conan", "configure_args.txt")
        os.makedirs(os.path.dirname(args_file), exist_ok=True)
        with open(args_file, "w", encoding="utf-8") as f:
            f.write(" ".join(tc.configure_args))

    def build(self):
        autotools = Autotools(self)
        if str(self.settings.os) == "OHOS":
            lld = self._lld_path()
            # Create ld/ld.aarch64 links in a build-local bin/ for any
            # tool that probes for bare "ld" (e.g. make, libtool).
            # Linker selection for configure itself is handled by the
            # -fuse-ld=<path> configure arg set in generate().
            local_bin = os.path.join(self.build_folder, "bin")
            os.makedirs(local_bin, exist_ok=True)
            if os.path.isfile(lld):
                for name in ("ld", "ld.aarch64"):
                    link = os.path.join(local_bin, name)
                    if not os.path.lexists(link):
                        os.symlink(lld, link)
            os.environ["PATH"] = local_bin + os.pathsep + os.environ.get("PATH", "")
            # OHOS /tmp is read-only; patch 0001 makes configure honour
            # $TMPDIR for its temp directories.
            tmpdir = os.path.join(self.build_folder, "tmp")
            os.makedirs(tmpdir, exist_ok=True)
            os.environ["TMPDIR"] = tmpdir
            # On OHOS /bin/sh is mksh, which cannot handle temp files in
            # config.status.  Run configure under bash so config.status
            # (bash shebang) inherits a working environment.
            configure_cmd = os.path.join(self.source_folder, "configure")
            args_file = os.path.join(self.build_folder, "conan", "configure_args.txt")
            with open(args_file, encoding="utf-8") as f:
                configure_args = f.read().strip()
            self.run(f'bash "{configure_cmd}" {configure_args}', env="conanbuild")
        else:
            autotools.configure()
        autotools.make()

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        rm(self, "*.la", folder=os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["dime"]
        self.cpp_info.set_property("pkg_config_name", "dime")
