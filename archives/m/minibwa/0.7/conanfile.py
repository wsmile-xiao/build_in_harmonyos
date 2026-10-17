#!/usr/bin/env python3
"""Conan recipe for minibwa 0.7 — lh3's lightweight BWA aligner.

minibwa is a lightweight BWA re-implementation for short-read alignment.
Upstream (v0.7, r421) is a raw Makefile project producing:
  - minibwa        CLI binary (index/map/meth + legacy mem-style commands)
  - libminibwa.a   static library for the documented C API (minibwa.h)

Dependencies:
  - zlib/1.3.1.1  (gzip FASTA/Q input via kseq/KSEQ_INIT2 in bseq.c)

OHOS adaptations (all explained in notes.md):
  - ARCH=aarch64 is passed explicitly: the Makefile probes `uname -m`,
    which is only correct for native builds.
  - mimalloc malloc override disabled via the upstream `mimalloc=0`
    switch: on OHOS the override recurses in __emutls_get_address during
    emulated-TLS bootstrap and overflows the stack (SIGSEGV). kalloc is
    the upstream fallback allocator. (knowledge E210)
  - Serial make (-j1): the GNU make jobserver FIFO cannot live on the
    HMDFS workspace. (knowledge E074)
  - Package-time ELF self-signing with llvm-objcopy + binary-sign-tool,
    same as every other OHOS CLI package.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.layout import basic_layout


class MinibwaConan(ConanFile):
    name = "minibwa"
    version = "0.7"
    description = (
        "Lightweight BWA for short-read alignment (index/map/meth commands) "
        "with a static C library"
    )
    license = "MIT"
    homepage = "https://github.com/lh3/minibwa"
    url = "https://github.com/lh3/minibwa/tree/v0.7"
    topics = ("bioinformatics", "aligner", "sequencing", "bwa")

    # CLI application that also ships libminibwa.a + minibwa.h for the
    # documented C API. Upstream has no shared-library target.
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    options = {
        "with_gpl": [True, False],
        "with_mimalloc": [True, False],
    }
    default_options = {
        "with_gpl": True,        # upstream default (QSufSort/bwtgen IS index)
        "with_mimalloc": False,  # kalloc; mimalloc override crashes on OHOS
    }

    def requirements(self):
        self.requires("zlib/1.3.1.1")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"minibwa is only supported on Linux/OHOS, not "
                f"{self.settings.os}"
            )
        if self.info.options.with_mimalloc and self.settings.os == "OHOS":
            # mimalloc's malloc override (MI_MALLOC_OVERRIDE) enters the
            # allocator before emulated-TLS is bootstrapped on OHOS and
            # recurses in __emutls_get_address -> stack overflow (SIGSEGV).
            # Upstream provides the official mimalloc=0 switch (kalloc).
            raise ConanInvalidConfiguration(
                "minibwa mimalloc malloc override crashes on OHOS emulated "
                "TLS bootstrap; use -o with_mimalloc=False (default)"
            )

    def layout(self):
        basic_layout(self)
        # Build inside the source folder so the upstream Makefile's relative
        # object rules (pattern .c.o) keep working under the Conan layout.
        self.folders.build = "."

    def source(self):
        # URL + sha256 come from conandata.yml; the mirror list keeps
        # direct GitHub access from timing out in the OHOS environment.
        get(
            self,
            url=self.conan_data["sources"]["url"],
            sha256=self.conan_data["sources"]["sha256"],
            strip_root=True,
        )

    def generate(self):
        # Raw Makefile project: no toolchain generator is needed. The OHOS
        # compiler is injected through tools.build:compiler_executables.
        pass

    def build(self):
        apply_conandata_patches(self)

        # R33: compiler from Conan conf, never from shell env.
        compilers = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        ) or {}
        cc = compilers.get("c", "clang")

        # Feed the Conan-provided zlib into the raw Makefile build: upstream
        # LIBS is a bare -lz resolved from system linker paths, which do not
        # see the Conan package cache. The Makefile's INCLUDES and LDFLAGS
        # variables are the correct injection points.
        zlib = self.dependencies["zlib"]
        zlib_lib = os.path.join(zlib.package_folder, "lib")
        zlib_inc = os.path.join(zlib.package_folder, "include")

        ldflags = []
        if str(self.settings.os) == "OHOS":
            # Worker linker by default, local SDK override via conf/env
            # (same policy as cronutils 1.1).
            ld_path = self.conf.get("user.ohos:ld_path", default="", check_type=str)
            ld_path = ld_path or os.environ.get("OHOS_LD", "")
            if ld_path:
                ldflags.append(f'-fuse-ld="{ld_path}"')

        # Upstream Makefile notes (v0.7 r421):
        #   - CFLAGS on the command line IS the baseline (-std=c99 -g -Wall
        #     -O3); the Makefile appends -fopenmp and arch flags via
        #     `override CFLAGS+=`, so we must repeat the baseline here.
        #   - INCLUDES is appended to every compile line.
        #   - ARCH only matters for cross builds where uname -m is wrong.
        #   - mimalloc=0 clears MALLOC_O and adds -DHAVE_KALLOC (kalloc.o is
        #     already in LOBJS) — the upstream-supported allocator switch.
        #   - gpl=0 drops QSufSort.o/bwtgen.o from AOBJS and removes USE_GPL.
        make_vars = [
            f'CC="{cc}"',
            "AR=llvm-ar",
            f"ARCH={self._target_arch()}",
            f'INCLUDES=-I"{zlib_inc}"',
        ]
        ld_parts = [f'-L"{zlib_lib}"']
        if ldflags:
            ld_parts += ldflags
        make_vars.append("LDFLAGS=" + " ".join(ld_parts))
        if self.info.options.with_gpl:
            make_vars.append("gpl=1")
        else:
            make_vars.append("gpl=0")
        make_vars.append(
            "mimalloc=1" if self.info.options.with_mimalloc else "mimalloc=0"
        )

        # Serial make: the shared workspace filesystem cannot host the GNU
        # make jobserver FIFO (E074), and the build is small.
        self.run(
            "make -j1 clean all " + " ".join(make_vars),
            cwd=self.source_folder,
        )

    def package(self):
        copy(
            self,
            "minibwa",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "bin"),
            keep_path=False,
        )
        copy(
            self,
            "libminibwa.a",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "lib"),
            keep_path=False,
        )
        copy(
            self,
            "minibwa.h",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "include", "minibwa"),
            keep_path=False,
        )
        # kseq.h is required by the documented streaming API pattern in
        # minibwa.h's companion examples (KSEQ_INIT on a gzFile) — the
        # upstream api-test programs include it alongside minibwa.h.
        copy(
            self,
            "kseq.h",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "include", "minibwa"),
            keep_path=False,
        )
        copy(
            self,
            "LICENSE.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        # Ship the upstream test data (chrM index+map dataset) so the
        # consumer test can run the official README workflow without
        # re-downloading the release tarball.
        copy(
            self,
            "*.fa.gz",
            src=os.path.join(self.source_folder, "test"),
            dst=os.path.join(self.package_folder, "share", "minibwa", "test"),
            keep_path=False,
        )
        bin_path = os.path.join(self.package_folder, "bin", "minibwa")
        if os.path.isfile(bin_path):
            os.chmod(bin_path, 0o755)
            self._sign_ohos_binary(bin_path)

    def _sign_ohos_binary(self, path):
        if str(self.settings.os) != "OHOS":
            return

        signer = self.conf.get("user.ohos:sign_tool", default="", check_type=str)
        signer = (
            signer
            or os.environ.get("OHOS_SIGN_TOOL", "")
            or shutil.which("binary-sign-tool")
            or "/data/service/hnp/bin/binary-sign-tool"
        )
        if not os.path.isfile(signer):
            self.output.warning(
                "binary-sign-tool is unavailable; skipping OHOS ELF signing"
            )
            return

        objcopy = self.conf.get("user.ohos:objcopy", default="", check_type=str)
        objcopy = (
            objcopy
            or os.environ.get("OHOS_OBJCOPY", "")
            or shutil.which("llvm-objcopy")
            or "/data/service/hnp/bin/llvm-objcopy"
        )
        if os.path.isfile(objcopy):
            self.run(
                f'"{objcopy}" --remove-section .codesign "{path}"',
                ignore_errors=True,
            )

        signed = f"{path}.signed"
        self.run(
            f'"{signer}" sign -selfSign 1 -inFile "{path}" '
            f'-outFile "{signed}" -signAlg SHA256withECDSA'
        )
        if not os.path.isfile(signed):
            raise ConanException(
                f"binary-sign-tool produced no output for {path}"
            )
        os.replace(signed, path)
        os.chmod(path, 0o755)

    def package_info(self):
        # Application package: CLI on PATH; static library + public header
        # for consumers of the documented C API.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include/minibwa"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["minibwa"]
        self.cpp_info.system_libs = ["pthread", "m"]
        self.cpp_info.requires = ["zlib::zlib"]
        self.cpp_info.set_property("cmake_target_name", "minibwa::minibwa")
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )

    def _target_arch(self):
        arch = str(self.settings.arch)
        return {
            "armv8": "aarch64",
            "aarch64": "aarch64",
            "x86_64": "x86_64",
            "x86": "x86",
        }.get(arch, arch)
