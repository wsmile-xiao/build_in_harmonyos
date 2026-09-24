#!/usr/bin/env python3
"""Conan recipe — libaudec 0.3.4 (Meson).

libaudec is the audio file decoding/resampling wrapper library from the
Zrythm project. Its meson.build resolves libsndfile (>=1.0.25) and
libsamplerate (>=0.1.8) through pkg-config, with a CMake-subproject
fallback via `.wrap` files that is never taken here (MesonToolchain sets
wrap_mode=nofallback and both dependencies are published on ohpcd).
Upstream also bundles a minimp3-based decoder (ad_minimp3.c, header-only)
and the ffmpeg backend (ad_ffmpeg.c) is already commented out upstream, so
there is no ffmpeg dependency.

Adaptation points (rationale in notes.md, evidence in reports/):

- Static-only delivery: src/meson.build builds the library with
  both_libraries(), which unconditionally also builds a shared
  libaudec.so regardless of default_library. Linking that .so pulls
  libsamplerate.a, whose objects are non-PIC (llvm-readelf -r on the
  ohpcd libsamplerate/0.2.2 OHOS binary shows R_AARCH64_ABS64 absolute
  relocations in src_sinc.c.obj), which lld rejects for shared objects.
  Patch 0001 turns both_libraries() into static_library() (R26 static
  delivery); the installed `audec` CLI links the static library, so no
  functionality is lost.
- Tool discovery: no ambient meson on the OHOS device/worker —
  tool_requires meson + ninja from ohpcd. AR/AS/STRIP/NM/RANLIB are
  popped from the environment and the meson machine file gets absolute
  tool paths: the worker exports llvm-* bare names which meson cannot
  resolve ("Unknown linker(s): llvm-ar", same root cause as
  at-spi2-core).
- Dependency discovery: PkgConfigDeps generates sndfile.pc +
  libsamplerate.pc; meson's dependency('samplerate') looks for
  samplerate.pc, so a pkg_config_aliases entry bridges the name (the
  libsamplerate package sets no pkg_config_name). PKG_CONFIG_PATH is
  injected explicitly around configure/build (Conan does not add the
  generators folder by itself).
- Upstream tests: the 3 tests registered by tests/meson.build
  (wav_test, mp3_test, log_test) run in build() via `meson test`
  against the OHOS-built library (native device build).
- ELF re-sign after install: meson install rewrites RUNPATH, which
  breaks the linker's self-signed .codesign and makes OHOS fail to load
  the installed `audec` binary with EPERM (E077); strip + re-sign with
  the SDK binary-sign-tool, same pattern as at-spi2-core.
"""

import glob
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
)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LibaudecConan(ConanFile):
    name = "libaudec"
    version = "0.3.4"
    description = ("Audio file decoding and resampling wrapper library "
                   "over libsndfile and libsamplerate")
    license = "AGPL-3.0-or-later"
    homepage = "https://github.com/zrythm/libaudec"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("audio", "decoding", "resampling", "sndfile")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    # Static only: upstream's both_libraries() .so variant cannot link with
    # the non-PIC static libsamplerate delivered by ohpcd (see module
    # docstring); consumers get the static library via R26-style delivery.
    options = {"shared": [False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # W0 confirmed on ohpcd (exact OHOS armv8 Release binaries for this
        # profile): libsndfile/1.2.2 (fPIC=True) and libsamplerate/0.2.2.
        # Versions satisfy upstream's pkg-config minimums
        # (sndfile >=1.0.25, samplerate >=0.1.8).
        self.requires("libsndfile/1.2.2")
        self.requires("libsamplerate/0.2.2")

    def build_requirements(self):
        # No ambient meson/ninja on the OHOS device or the CI worker;
        # both are published on ohpcd with OHOS binaries (account-utils /
        # c-list precedent for the meson tool_requires).
        self.tool_requires("meson/1.11.0")
        self.tool_requires("ninja/1.12.1")

    def layout(self):
        # conan.tools.meson has no meson_layout in Conan 2.29; basic_layout
        # is the proven boxfort/bubblewrap pattern for meson recipes here.
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Dependency .pc files for meson's pkg-config resolver, plus a
        # `samplerate` alias: meson dependency('samplerate') searches
        # samplerate.pc while PkgConfigDeps emits libsamplerate.pc (the
        # libsamplerate package sets no pkg_config_name).
        pc = PkgConfigDeps(self)
        pc.set_property("libsamplerate", "pkg_config_aliases", ["samplerate"])
        pc.generate()

        # The worker environment exports AR/AS/STRIP/NM/RANLIB as llvm-*
        # bare names that meson cannot resolve; pop them and lock absolute
        # tool paths into the meson machine file (at-spi2-core pattern).
        for _var in ("AR", "AS", "STRIP", "NM", "RANLIB"):
            os.environ.pop(_var, None)
        tools = {name: shutil.which(name)
                 for name in ("ar", "as", "strip", "nm", "ranlib")}
        missing = [name for name, path in tools.items() if path is None]
        if missing:
            raise ConanInvalidConfiguration(
                "Required build tools not found in PATH: %s"
                % ", ".join(missing))

        tc = MesonToolchain(self)
        tc.ar = tools["ar"]
        tc.as_ = tools["as"]
        tc.strip = tools["strip"]
        tc.binaries["nm"] = tools["nm"]
        tc.binaries["ranlib"] = tools["ranlib"]
        # R26: static library delivery (options.shared only allows False).
        tc.project_options["default_library"] = "static"
        # Build the upstream tests (tests/meson.build guards its 3 tests on
        # the `tests` meson option, default true) so `meson test` runs them
        # against the OHOS-built library in build().
        tc.project_options["tests"] = "true"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        with self._build_environment().vars(self).apply():
            meson = Meson(self)
            meson.configure()
            meson.build()
            # Upstream test suite: the 3 tests registered by tests/meson.build
            # (wav_test, mp3_test, log_test).
            self.run('meson test -C "{}" --print-errorlogs'.format(
                self.build_folder))

    def package(self):
        with self._build_environment().vars(self).apply():
            Meson(self).install()
        copy(self, "COPYING*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        self._resign_elf()

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["audec"]
        # Static consumers must also link the wrapped libraries.
        self.cpp_info.requires = ["libsndfile::libsndfile",
                                  "libsamplerate::libsamplerate"]
        self.cpp_info.set_property("cmake_file_name", "libaudec")
        self.cpp_info.set_property("cmake_target_name", "libaudec::libaudec")
        # Matches the audec.pc file that upstream's pkgconfig module installs.
        self.cpp_info.set_property("pkg_config_name", "audec")

    # ── helpers ──────────────────────────────────────────────────────────

    def _build_environment(self):
        environment = Environment()
        # meson's dependency() resolves through pkg-config; Conan does not
        # add the generators folder to PKG_CONFIG_PATH by itself.
        environment.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        # /var/tmp does not exist on OHOS and root '/' is read-only; give
        # tools a writable temp area inside the build folder.
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        environment.define_path("TMPDIR", tmpdir)
        environment.define_path("TMP", tmpdir)
        environment.define_path("TEMP", tmpdir)
        # SDK lld depends on libxml2.so.16 in the SDK llvm/lib dir; without
        # it meson's linker probe fails. Prepend the SDK lib dir
        # (version-agnostic glob) so lld resolves its own libxml2.
        for sdk_lib in sorted(glob.glob(
                "/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib")):
            environment.prepend_path("LD_LIBRARY_PATH", sdk_lib)
        return environment

    def _resign_elf(self):
        """meson install rewrites RUNPATH and thereby breaks the linker's
        self-signed .codesign; OHOS then refuses to load the binary with
        EPERM (knowledge entry E077). Strip the stale section and re-sign
        with the SDK binary-sign-tool (at-spi2-core pattern)."""
        hnp = "/data/service/hnp/bin"
        objcopy = os.path.join(hnp, "llvm-objcopy")
        signer = os.path.join(hnp, "binary-sign-tool")
        if not os.path.isfile(objcopy) or not os.path.isfile(signer):
            self.output.warning("binary-sign-tool/llvm-objcopy unavailable, "
                                "skip ELF re-signing")
            return
        elfs = []
        for pat in ("bin/*", "libexec/*", "lib/*"):
            elfs += glob.glob(os.path.join(self.package_folder, pat))
        for f in sorted(set(elfs)):
            if not os.path.isfile(f):
                continue
            try:
                if open(f, "rb").read(4) != b"\x7fELF":
                    continue
            except OSError:
                continue
            self.run('{oc} --remove-section .codesign "{f}" '
                     '2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}.signed" '
                     '-selfSign 1'.format(sg=signer, f=f))
            if os.path.isfile(f + ".signed"):
                os.replace(f + ".signed", f)
                os.chmod(f, 0o755)
