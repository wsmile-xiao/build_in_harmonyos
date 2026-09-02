#!/usr/bin/env python3
"""Conan recipe for libtomcrypt 1.18.2 — modular cryptographic library.

Upstream: libtom/libtomcrypt (tag v1.18.2), dual-licensed WTFPL / public-domain
style (see LICENSE; the project is free for all purposes without any express
guarantee it works).

Upstream uses plain GNU makefiles (makefile for the static lib, makefile.shared
for libtool-based shared builds). This recipe builds the static library via
the plain `makefile` target `library`, then the official self-test binary via
target `test` and RUNS it (upstream `test` = the formal correctness suite,
a single executable with 21 registered suite entry points reporting
passed/failed/nop).

MPI provider: libtomcrypt has NO mandatory dependency. Without a math
provider all PK algorithms (RSA/DH/ECC/DSA/Katja, PKCS#1, parts of DER/MPI)
compile but self-report CRYPT_NOP. To deliver the full algorithm set we
link gmp (USE_GMP + GMP_DESC) — gmp/6.3.0 is published on the ohpcd remote
for OHOS aarch64 and its API matches what 1.18.2 expects (libtommath 1.3.0
is NOT published on ohpcd and additionally breaks libtomcrypt 1.18.2's
`mp_toradix` call signature — mp_to_radix gained a `size_t *written`
parameter — so gmp is both the available and the zero-patch choice).

Cross-compile notes (OHOS aarch64, clang 15 / musl):
  * CC/AR/RANLIB are passed explicitly on the make command line — never
    inherited from the host shell (R33). The makefile honors CC/AR/RANLIB
    verbatim when given on the command line; no upstream patch is needed
    (zero-patch build).
  * CFLAGS is fully overridden: upstream defaults inject -O3
    -funroll-loops -fomit-frame-pointer plus a large warning set; we keep
    the required -I./src/headers -DLTC_SOURCE, add -DUSE_GMP -DGMP_DESC
    and -fPIC, and use profile-mapped optimization instead.
  * EXTRALIBS is pointed at the Conan-packaged gmp (headers via -I, lib via
    -l) instead of the makefile's pkg-config auto-detection, which would
    probe the build host's system libtommath/tomsfastmath.
  * The upstream `install` target's install -p -d/-m group/owner handling
    and libtomcrypt.pc sed are reimplemented in package() (plain copies),
    so no root privileges or host `install` quirks are involved.

R9:  make -j1.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import Environment
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout


class LibtomcryptConan(ConanFile):
    name = "libtomcrypt"
    version = "1.18.2"
    description = (
        "LibTomCrypt — a modular, portable cryptographic toolkit "
        "(ciphers, hashes, MACs, modes, PRNGs, public key algorithms)"
    )
    license = "WTFPL"
    homepage = "https://github.com/libtom/libtomcrypt"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("crypto", "cryptography", "libtomcrypt")

    package_type = "library"
    languages = "C"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "with_gmp": [True, False],
    }
    default_options = {
        "shared": False,
        "with_gmp": True,
    }

    def export_sources(self):
        # Zero-patch build: no patches directory exists.
        pass

    def requirements(self):
        if self.options.with_gmp:
            self.requires("gmp/6.3.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ── Toolchain resolution (R33: from Conan conf / buildenv, not host shell) ──
    def _cc(self):
        # Profile config may carry a stale toolchain path (e.g.
        # an absolute compiler path that does not exist on the current host).
        # Verify the configured binary actually exists; otherwise fall
        # back to `clang` resolved from the Conan buildenv PATH, which on
        # OHOS is the real clang wrapper that auto-signs the ELF.
        comp_execs = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = comp_execs.get("c", "clang")
        if os.path.isabs(cc):
            return cc if os.path.exists(cc) else "clang"
        return cc if shutil.which(cc) else "clang"

    def _ar(self):
        return os.environ.get("AR", "ar")

    def _ranlib(self):
        return os.environ.get("RANLIB", "ranlib")

    # ── OHOS SDK linker runtime path (lld/libxml2.so.16) ──────────────
    # Same rationale as libscrypt: the OHOS clang driver spawns `lld`,
    # whose NEEDED list includes libxml2.so.16 resolved via its RUNPATH
    # ($ORIGIN/../lib → the SDK llvm/lib). An ambient LD_LIBRARY_PATH can
    # shadow that with an ABI-mismatched libxml2 and crash the link step.
    # Prepend the SDK's own llvm/lib around every self.run() in build().
    def _sdk_llvm_libdir(self):
        if str(self.settings.os) != "OHOS":
            return ""
        cc = self._cc()
        cc_resolved = shutil.which(cc) or cc
        cc_real = os.path.realpath(cc_resolved)
        llvm_lib = os.path.join(os.path.dirname(os.path.dirname(cc_real)), "lib")
        if os.path.isfile(os.path.join(llvm_lib, "libxml2.so.16")):
            return llvm_lib
        return ""

    def _build_environment(self):
        env = Environment()
        sdk_lib = self._sdk_llvm_libdir()
        if sdk_lib:
            self.output.info(
                f"Prepending OHOS SDK linker runtime path for lld: {sdk_lib}"
            )
            env.prepend_path("LD_LIBRARY_PATH", sdk_lib)
        return env

    def _opt_flags(self):
        bt = str(self.settings.build_type)
        return {
            "Debug": "-O0 -g",
            "Release": "-O2 -DNDEBUG",
            "RelWithDebInfo": "-O2 -g -DNDEBUG",
            "MinSizeRel": "-Os -DNDEBUG",
        }.get(bt, "-O2")

    def _cflags(self):
        # Required by the makefile for any in-tree build; -DLTC_SOURCE
        # exposes the internal API the tests use. USE_GMP/GMP_DESC select
        # the MPI provider (see src/headers/tomcrypt_custom.h).
        flags = [
            "-I./src/headers/",
            "-DLTC_SOURCE",
            "-fPIC",
            self._opt_flags(),
        ]
        if self.options.with_gmp:
            gmp = self.dependencies["gmp"]
            flags.append(f"-I{gmp.cpp_info.includedirs[0]}")
            flags.append("-DUSE_GMP")
            flags.append("-DGMP_DESC")
        return " ".join(flags)

    def _extralibs(self):
        if not self.options.with_gmp:
            return ""
        gmp = self.dependencies["gmp"]
        libdir = gmp.cpp_info.libdirs[0]
        return f"-L{libdir} -lgmp"

    def _make_args(self):
        args = [
            f'CC="{self._cc()}"',
            f'AR="{self._ar()}"',
            f'RANLIB="{self._ranlib()}"',
            f'CFLAGS="{self._cflags()}"',
            f'EXTRALIBS="{self._extralibs()}"',
            "-j1",
        ]
        return " ".join(args)

    def build(self):
        src = self.source_folder
        with self._build_environment().vars(self).apply():
            # 1) The deliverable: static library libtomcrypt.a.
            self.run(f"make -C {src} library {self._make_args()}")

            # 2) The official self-test binary (target `test` links
            #    TOBJECTS + libtomcrypt.a). NOT a deliverable.
            self.run(f"make -C {src} test {self._make_args()}")

            # 3) Execute the upstream formal test suite on the target.
            #    `./test` runs all 21 registered suites sequentially and
            #    prints a final
            #    "SUCCESS: passed=<p> failed=<f> nop=<n> duration=..."
            #    summary; exit code is nonzero if any suite fails.
            #    With gmp as MPI provider no suite is expected to nop.
            if can_run(self):
                self.run("./test", cwd=src)

    def package(self):
        # Headers: exactly the 13 public headers the upstream `make
        # install` installs (HEADERS in makefile_include.mk).
        copy(self, "tomcrypt.h", os.path.join(self.source_folder, "src", "headers"),
             os.path.join(self.package_folder, "include"), keep_path=False)
        copy(self, "tomcrypt_*.h", os.path.join(self.source_folder, "src", "headers"),
             os.path.join(self.package_folder, "include"), keep_path=False)
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)
        lib = os.path.join(self.package_folder, "lib")
        if self.options.shared:
            copy(self, "libtomcrypt.so*", self.source_folder, lib, keep_path=False)
        else:
            copy(self, "libtomcrypt.a", self.source_folder, lib, keep_path=False)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libtomcrypt")
        self.cpp_info.set_property("cmake_target_name", "libtomcrypt::libtomcrypt")
        self.cpp_info.set_property("pkg_config_name", "libtomcrypt")
        self.cpp_info.libs = ["tomcrypt"]
        if self.options.with_gmp:
            self.cpp_info.requires = ["gmp::gmp"]
        # musl: no separate libm for these code paths, but keep it for
        # consumers that use the float-timing test scaffolding.
        if str(self.settings.os) == "OHOS":
            self.cpp_info.system_libs = []
