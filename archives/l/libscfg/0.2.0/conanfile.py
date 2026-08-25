#!/usr/bin/env python3
"""Conan recipe for libscfg 0.2.0 — Meson build system.

libscfg is a simple configuration file format library by emersion.
It builds a shared library (libscfg.so) with meson and has no external
dependencies. The library provides functions to parse and format a
scfg configuration file (directive-based, block-scoped syntax).

Upstream: https://codeberg.org/emersion/libscfg
License: MIT
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LibscfgConan(ConanFile):
    name = "libscfg"
    version = "0.2.0"
    description = "Simple configuration file format library"
    license = "MIT"
    homepage = "https://codeberg.org/emersion/libscfg"

    package_type = "library"
    export_conandata_patches = True
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        sources = dict(self.conan_data["sources"])
        mirror_urls = sources.pop("mirror_urls", [])
        mirror_sha256 = sources.pop("mirror_sha256", None)
        # Whether the source tree has been successfully fetched. Every
        # successful path sets this True; failures raise and never set it.
        # apply_conandata_patches must run exactly once, after any of the
        # fetch paths below — so no success path may return early.
        fetched = False
        try:
            get(self, **sources, strip_root=True)
            fetched = True
        except Exception as error:
            if not mirror_urls or not mirror_sha256:
                raise
            self.output.warning(f"Primary source failed ({error}); trying verified mirrors")
            for mirror_url in mirror_urls:
                try:
                    get(self, url=mirror_url, sha256=mirror_sha256, strip_root=True)
                    fetched = True
                    break
                except Exception as mirror_error:
                    self.output.warning(f"Mirror source failed ({mirror_error}): {mirror_url}")
            if not fetched:
                raise
        # Single exit: patches apply once regardless of which fetch path
        # succeeded. A bare ``return`` in the mirror branch previously
        # skipped this and left pristine upstream source (e.g. missing the
        # OHOS open_memstream fflush fix), breaking scfg:format at runtime.
        apply_conandata_patches(self)

    def _resolve_archiver(self):
        """Resolve a real, on-disk archiver for Meson's ``[binaries] ar``.

        MesonToolchain defaults ``ar`` from the ``AR`` env var, which on OHOS
        CI resolves to a bare ``llvm-ar`` that is not on PATH, crashing Meson
        configure with "Unknown linker(s): [['llvm-ar']]". This picks an
        archiver that actually exists, never a bare name that may be missing.
        """
        candidates = []

        # 1. An explicitly exported AR wins (it is the user's intent).
        env_ar = os.environ.get("AR")
        if env_ar:
            candidates.append(env_ar)

        # 2. Look next to the Conan-configured C compiler: the archiver from
        #    the same LLVM/SDK toolchain bin dir is the correct match.
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        )
        cc = compiler_executables.get("c", "")
        cc_path = shutil.which(cc) or cc
        if cc_path:
            compiler_dir = os.path.dirname(cc_path)
            candidates.extend([
                os.path.join(compiler_dir, "llvm-ar"),
                os.path.join(compiler_dir, "ar"),
            ])

        # 3. PATH fallbacks (bare names resolved through shutil.which below).
        candidates.extend([
            "llvm-ar",
            "ar",
            "llvm-ar-15",
            "aarch64-linux-ohos-ar",
        ])

        for candidate in candidates:
            if not candidate:
                continue
            resolved = shutil.which(candidate)
            if resolved and os.path.isfile(resolved):
                return resolved
            if os.path.isabs(candidate) and os.path.isfile(candidate):
                return candidate

        raise ConanInvalidConfiguration(
            "Unable to locate an archiver required by Meson on OHOS"
        )

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        # Suppress -Werror on "linker input unused": the OHOS profile injects
        # -Wl,--code-sign into CFLAGS (a linker flag). When clang compiles .c->.o
        # it warns "-Wl,--code-sign: linker input unused". Upstream meson.build
        # sets werror=true, which makes that warning fatal. Add the no-error
        # suppression so the (harmless during compilation) linker flag does not
        # break the build. The flag still takes effect at link time.
        tc.c_args = list(tc.c_args) + ["-Wno-error=unused-command-line-argument"]
        # OHOS: MesonToolchain defaults ``ar`` to the bare ``AR`` env value
        # (``llvm-ar``), which is absent from the CI worker PATH. Resolve a
        # real archiver so conan_meson_native.ini carries an existing path.
        if self.settings.os == "OHOS":
            tc.ar = self._resolve_archiver()
        tc.generate()

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # OHOS XPM requires code-signed ELF binaries (dlopen'd .so and
        # exec'd executables). Signing is a content hash stored in a
        # .codesign section — it must happen AFTER link and BEFORE any
        # byte-modifying post-processing (strip/patchelf/relink).
        # Guarded: no-op on non-OHOS (tools don't exist there).
        if self.settings.os != "OHOS":
            return
        import glob
        targets = glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so"), recursive=True)
        targets += glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so.*"), recursive=True)
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in os.listdir(bindir):
                p = os.path.join(bindir, name)
                if os.path.isfile(p) and not os.path.islink(p) and self._is_elf(p):
                    targets.append(p)
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        for f in targets:
            if os.path.islink(f):
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        self.cpp_info.libs = ["scfg"]
        self.cpp_info.set_property("cmake_file_name", "libscfg")
        self.cpp_info.set_property("cmake_target_name", "libscfg::libscfg")
        self.cpp_info.set_property("pkg_config_name", "scfg")
