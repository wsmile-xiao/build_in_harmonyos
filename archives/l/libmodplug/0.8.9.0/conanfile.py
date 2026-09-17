#!/usr/bin/env python3
"""Conan recipe — libmodplug 0.8.9.0 (OpenHarmony PC aarch64).

libmodplug is Konstanty Bialkowski's module music library (MOD/XM/S3M/IT
and ~20 more tracker formats), a pure C++ library with a C API declared
in src/modplug.h. Upstream build facts (verified against the 0.8.9.0
tarball, SHA256 457ca5a6...):

  - Pure autotools, no third-party build-time dependencies
    (configure.ac has no AC_CHECK_LIB beyond -lm / no *_REQUIRES).
  - AC_DISABLE_STATIC: upstream never builds a static libmodplug.
    This recipe keeps default shared=True; a static option would fight
    the upstream build system, so it is rejected instead of pretending.
  - C++ is the implementation language (AC_LANG([C++])), built with
    -fno-exceptions -Wall -ffast-math -fno-common -D_REENTRANT.
  - SONAME: src/Makefile.am sets MODPLUG_LIBRARY_VERSION=1:0:0 →
    libtool delivers libmodplug.so.1.0.0 with SONAME libmodplug.so.1.
  - Headers install to include/libmodplug/ (modplug.h + the three
    public headers dir); pkg-config file libmodplug.pc is installed.

Upstream ships no test suite (evidence in test_package/MANIFEST.yml),
so per TEST_QUALITY_SPEC the consumer + HarmonyOS-specific tiers fully
replace the upstream tier.

OHOS specifics:
  - 0001/0002 patches teach the 2015-era config.guess/config.sub about
    aarch64-unknown-linux-ohos (uname -s = "HarmonyOS").
  - configure creates its temp dirs with `umask 077` under HMDFS, where
    the UID mapping makes those dirs unwritable mid-build (E011); the
    same in-place rewrite as lame/3.100 is applied.
  - Shared libraries get a .codesign section before packaging
    (libpng 1.6.58.2 signing pattern).
"""
import os
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, get, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibmodplugConan(ConanFile):
    name = "libmodplug"
    version = "0.8.9.0"
    description = "Module music library (MOD/XM/S3M/IT/...) with a C API"
    license = "Public Domain"  # COPYING: dedicated to the public domain
    homepage = "https://modplug-xmms.sourceforge.net/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def layout(self):
        basic_layout(self, src_folder=".")

    def export_sources(self):
        copy(self, "*.patch", src=self.recipe_folder, dst=self.export_sources_folder)

    def configure(self):
        # Upstream configure.ac has AC_DISABLE_STATIC: libtool will not
        # produce libmodplug.a. The static option is not offered rather
        # than silently packaging whatever libtool happens to emit.
        if not self.options.shared:
            raise ConanInvalidConfiguration(
                "libmodplug 0.8.9.0 upstream disables static libraries "
                "(AC_DISABLE_STATIC); only shared=True is supported"
            )
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "libmodplug supports OHOS armv8 only"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # fastmix.cpp's SNDMIX_BEGINSAMPLELOOP8/16 macros declare
        # `register MODCHANNEL * const pChn` (2 uses); C++17 removed the
        # register storage class, and the repo profile pins cppstd=17.
        # Same situation and fix as autodocksuite 4.2.6 / freeimage 3.18.0.
        tc.extra_cxxflags = ["-Wno-register"]
        if str(self.settings.os) == "OHOS":
            # AutotoolsToolchain derives --host/--build from the profile
            # triplet; the patched config.sub accepts it (0002 patch).
            tc.configure_args.extend([
                "--build=aarch64-linux-ohos",
                "--host=aarch64-linux-ohos",
            ])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # E011: configure's `umask 077 && mktemp` dance creates dirs that
        # HMDFS UID-mapping makes unwritable; switch to 022 like lame.
        replace_in_file(self, os.path.join(self.source_folder, "configure"),
                        "umask 077", "umask 022")
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()
        # Upstream ships no test suite: no `check` target exists in
        # Makefile.am/Makefile.in (grep TESTS/check = 0 hits, no tests/
        # dir in the 72-file tarball, no test framework referenced).
        # Running `make check` would be a no-op claim; evidence recorded
        # in test_package/MANIFEST.yml instead.

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)
        if str(self.settings.os) == "OHOS":
            self._sign_ohos_shared_libraries()

    def package_info(self):
        self.cpp_info.libs = ["modplug"]
        self.cpp_info.includedirs = ["include"]  # public: include/libmodplug/*.h

    # ── OHOS signing (libpng 1.6.58.2 pattern) ──────────────────────────

    def _sign_ohos_shared_libraries(self):
        libdir = Path(self.package_folder, "lib")
        if not libdir.is_dir():
            raise ConanException("package lib/ not found for OHOS signing")
        # Sign every real ELF file (regular file, not a symlink); the
        # install tree has libmodplug.so.1.0.0 + .so.1/.so symlinks.
        candidates = []
        for path in sorted(libdir.iterdir()):
            if path.is_symlink() or not path.is_file():
                continue
            with open(path, "rb") as fh:
                if fh.read(4) != b"\x7fELF":
                    continue
            candidates.append(path)
        if not candidates:
            raise ConanException("no ELF artifacts found to sign")
        for path in candidates:
            self._sign_elf(path)

    def _sign_elf(self, executable):
        executable = Path(executable)
        objcopy = self._resolve_tool("objcopy")
        readelf = self._resolve_tool("readelf")
        signer = self._resolve_tool("binary-sign-tool", llvm=False)
        temporary = executable.with_name(
            f"{executable.name}.signing-{os.getpid()}"
        )
        try:
            shutil.copy2(executable, temporary)
            sections = subprocess.run(
                [readelf, "-SW", str(temporary)],
                check=True, capture_output=True, text=True,
            ).stdout
            if ".codesign" in sections:
                subprocess.run(
                    [objcopy, "--remove-section", ".codesign", str(temporary)],
                    check=True,
                )
            subprocess.run(
                [signer, "sign", "-inFile", str(temporary),
                 "-outFile", str(temporary), "-selfSign", "1"],
                check=True,
            )
            signed_sections = subprocess.run(
                [readelf, "-SW", str(temporary)],
                check=True, capture_output=True, text=True,
            ).stdout
            if signed_sections.count(".codesign") != 1:
                raise ConanException(f"signer did not add .codesign: {executable}")
            os.chmod(temporary, (os.stat(temporary).st_mode & 0o777) | 0o755)
            os.replace(temporary, executable)
        finally:
            if temporary.exists():
                temporary.unlink()

    def _resolve_tool(self, tool, llvm=True):
        # Resolve LLVM/binary tools relative to the configured compiler
        # (libpng 1.6.58.2 pattern) — no hardcoded /data/service/hnp/bin.
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        compiler = executables.get("c") or shutil.which("cc")
        compiler_dir = os.path.dirname(shutil.which(compiler) or compiler) if compiler else ""
        compiler_name = os.path.basename(compiler) if compiler else ""
        suffix = (
            compiler_name[len("clang"):]
            if compiler_name.startswith("clang")
            else ""
        )
        candidates = [executables.get(tool)]
        if compiler_dir:
            if llvm:
                candidates.extend(
                    [
                        os.path.join(compiler_dir, f"llvm-{tool}{suffix}"),
                        os.path.join(compiler_dir, f"llvm-{tool}"),
                    ]
                )
            candidates.append(os.path.join(compiler_dir, tool))
        if llvm and suffix:
            candidates.append(f"llvm-{tool}{suffix}")
        if llvm:
            candidates.append(f"llvm-{tool}")
        candidates.append(tool)
        for candidate in candidates:
            if candidate:
                resolved = shutil.which(candidate)
                if resolved:
                    return resolved
        raise ConanInvalidConfiguration(f"required OHOS tool was not found: {tool}")
