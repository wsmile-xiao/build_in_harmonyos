#!/usr/bin/env python3
"""Conan recipe — emacs-clang-complete-async 0.5

Emacs clang async code completion backend (clang-complete binary).
Uses libclang (from the system LLVM/Clang SDK) to parse C/C++ source code
and provide completion candidates to Emacs via a client-server protocol.

Build system: raw Makefile (uses llvm-config to find libclang).
Product: clang-complete executable (application, not a library).

Dependency note: libclang and llvm-config are provided by the OHOS system
SDK at /data/service/hnp/ (not a Conan package). The build uses llvm-config
to discover the include/lib paths automatically.
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class EmacsClangCompleteAsyncConan(ConanFile):
    name = "emacs-clang-complete-async"
    version = "0.5"
    description = "Emacs clang async code completion backend (clang-complete binary)"
    license = "MIT"
    homepage = "https://github.com/Golevka/emacs-clang-complete-async"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler from Conan conf, never from shell env vars.
        # tools.build:compiler_executables is a dict like {"c": "/path/clang", "cpp": "/path/clang++"}
        compilers = self.conf.get("tools.build:compiler_executables", check_type=dict) or {}
        cc = compilers.get("c", "clang")
        ar = compilers.get("ar", "llvm-ar")  # ar may not be in dict, fallback
        ranlib = compilers.get("ranlib", "llvm-ranlib")  # fallback

        # The Makefile uses llvm-config to find libclang cflags/ldflags.
        # On OHOS, llvm-config is provided by the system SDK at /data/service/hnp/bin/
        # (already in PATH via the Conan profile buildenv).
        llvm_config = "llvm-config"

        # Resolve the LLVM libdir via llvm-config (R33: no hardcoded glob paths).
        # NOTE: the result is also needed in package_info(), but Conan re-instantiates
        # the recipe for the test_package's runenv generation, so an instance var
        # set here does not survive. package_info() queries llvm-config directly
        # via subprocess (read-only, no Conan self.run side effects) instead.
        self._llvm_libdir = self._query_llvm_libdir(llvm_config)

        # R9: Always use -j1
        # Run make from the source folder since the Makefile is there.
        # Prepend the SDK llvm/lib to LD_LIBRARY_PATH so the lld linker (spawned
        # by clang for linking) loads the SDK's libxml2.so.16 instead of a
        # shadowed/incompatible one from the ambient environment (e.g.
        # ~/usr/local/lib), which otherwise fails with "Error loading shared
        # library libxml2.so.16 ... symbol not found" (see abr2gbr/1.0.2).
        ld_env = f'LD_LIBRARY_PATH="{self._llvm_libdir}:$LD_LIBRARY_PATH" ' if self._llvm_libdir else ""
        self.run(f'{ld_env}make CC=\"{cc}\" AR=\"{ar}\" RANLIB=\"{ranlib}\" LLVM_CONFIG=\"{llvm_config}\" -j1',
                 cwd=self.source_folder)

    def package(self):
        # Install the clang-complete binary to bin/
        # The binary is built in the source folder
        copy(self, "clang-complete", self.source_folder, os.path.join(self.package_folder, "bin"))

        # Sign the binary for OHOS execution (ELF must be signed).
        # R33: discover signing tools dynamically via PATH (shutil.which),
        # never hardcode absolute paths — release CI workers may differ.
        bindir = os.path.join(self.package_folder, "bin")
        binary = os.path.join(bindir, "clang-complete")
        if os.path.isfile(binary) and self.settings.os in ("Linux", "OHOS"):
            signer = shutil.which("binary-sign-tool")
            if signer is None:
                # Signing tool absent on this worker: skip (not a hard failure,
                # but record an explicit warning rather than silently swallowing).
                self.output.warning(
                    "binary-sign-tool not found in PATH; skipping binary signing "
                    "(clang-complete may fail to execute on OHOS)")
            else:
                # Pre-clean any existing .codesign section. Only run if the
                # stripping tool is present; do NOT ignore failures silently.
                objcopy = shutil.which("llvm-objcopy") or shutil.which("objcopy")
                if objcopy:
                    # Remove pre-existing signature section (idempotent prep step).
                    # A missing section is expected on a fresh build, so tolerate
                    # that single case but surface genuine tool errors.
                    self.run(
                        f'{objcopy} --remove-section .codesign "{binary}" || true',
                        ignore_errors=True)
                # Sign — failures here must abort the build (no ignore_errors).
                self.run(
                    f'{signer} sign -inFile "{binary}" -outFile "{binary}" -selfSign 1')

    def package_info(self):
        # Application package: the main artifact is the clang-complete binary.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        # libclang is a runtime dependency (provided by system SDK, not Conan)
        self.cpp_info.system_libs = ["m", "dl", "pthread"]
        # Runtime: libclang.so from system SDK. Query llvm-config for the
        # libdir here via subprocess (read-only, NOT self.run — package_info
        # must have no Conan side effects). R33: no hardcoded glob paths.
        # An instance var set in build() does NOT survive Conan's recipe
        # re-instantiation during test_package runenv generation, so we
        # resolve it directly here. Use append_path (not define) so
        # VirtualRunEnv serializes LD_LIBRARY_PATH into conanrun.sh.
        if self.settings.os in ("Linux", "OHOS"):
            llvm_libdir = self._query_llvm_libdir()
            if llvm_libdir:
                self.runenv_info.append_path("LD_LIBRARY_PATH", llvm_libdir)

    def _query_llvm_libdir(self, llvm_config="llvm-config"):
        """Query the LLVM library directory from llvm-config.

        Returns the libdir path as a string, or "" if llvm-config is
        unavailable / fails. Uses subprocess directly for a robust,
        Conan-version-independent return value (R33: no hardcoded paths).
        """
        exe = shutil.which(llvm_config)
        if not exe:
            self.output.warning(
                f"{llvm_config} not found in PATH; LD_LIBRARY_PATH will not be set")
            return ""
        try:
            res = subprocess.run(
                [exe, "--libdir"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, check=False)
            if res.returncode != 0:
                self.output.warning(
                    f"{llvm_config} --libdir failed (rc={res.returncode}); "
                    "LD_LIBRARY_PATH will not be set")
                return ""
            return res.stdout.strip()
        except Exception as e:
            self.output.warning(
                f"error running {llvm_config} --libdir ({e}); "
                "LD_LIBRARY_PATH will not be set")
            return ""
