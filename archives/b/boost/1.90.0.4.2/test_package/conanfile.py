#!/usr/bin/env python3
"""Consumer test for Boost Morpheus components + OHOS-specific validation."""

import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class BoostMorpheusComponentsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    # ── OHOS-specific validation (boost/1.90.0.4.2) ────────────────────────────
    #
    # 1. Python-side package layout check:
    #    - no libboost_*.so.<digits> versioned soname links (HMDFS-incompatible;
    #      this is exactly what the recipe's 0001-cmake-avoid-versioned-soname-links
    #      patch + BOOST_INSTALL_NO_VERSIONED_LIBS=TRUE remove);
    #    - every libboost_*.so carries a .codesign section (required for the OHOS
    #      loader; the recipe signs all shared libraries in package()).
    # 2. C++ dlopen consumer (test_boost_ohos_dlopen): dlopen each compiled
    #    component lib, dlsym a real exported symbol and CALL it.
    #
    # OHOS HMDFS quirk handled here: on this filesystem (hmmac=use_task) a signed
    # .so whose signature state has been invalidated by read/copy operations is
    # rejected by the loader ("symbol not found"/"Permission denied"). Re-signing
    # in place refreshes it, so we re-sign the package libs before running any
    # consumer. On a fresh conan create the libs are freshly signed by package()
    # and load fine even if in-place re-signing is not possible.

    def test(self):
        if not can_run(self):
            self.output.warning("Cross-built consumer cannot run on the build host.")
            return

        if self.settings.os == "OHOS":
            # Order matters on OHOS HMDFS (hmmac=use_task): READING a signed .so
            # (e.g. the llvm-objcopy .codesign probe below, or any other reader)
            # invalidates its loader-visible signature state, and the loader then
            # rejects it ("symbol not found"/"Permission denied"). So run the
            # read-only layout check FIRST, then re-sign in place to refresh.
            self._check_package_layout()
            self._refresh_package_lib_signatures()

        suffix = ".exe" if str(self.settings.os) == "Windows" else ""
        executable_names = (
            "test_boost_morpheus_components",
            "test_boost_unit_test_framework",
            "test_boost_ohos_dlopen",
        )
        for executable_name in executable_names:
            executable = os.path.join(
                self.cpp.build.bindirs[0], executable_name + suffix
            )
            if self.settings.os == "OHOS":
                self._sign_executable(executable)
            if self.settings.os == "OHOS" and executable_name == "test_boost_ohos_dlopen":
                self.run(
                    f'BOOST_PACKAGE_LIB_DIR="{self._package_lib_dir()}" "{executable}"',
                    env="conanrun",
                    cwd=self.build_folder,
                )
            else:
                self.run(f'"{executable}"', env="conanrun", cwd=self.build_folder)

    # ── helpers ────────────────────────────────────────────────────────────────

    def _package_lib_dir(self):
        dependency = self.dependencies.get("boost")
        if dependency is None or dependency.package_folder is None:
            raise ConanInvalidConfiguration(
                "boost dependency package_folder is unavailable in test_package"
            )
        return os.path.join(dependency.package_folder, "lib")

    def _refresh_package_lib_signatures(self):
        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            self.output.warning(
                "OHOS signing tools unavailable; skipping in-place re-sign of package libs"
            )
            return
        lib_dir = self._package_lib_dir()
        re_signed = 0
        for lib in sorted(os.listdir(lib_dir)):
            path = os.path.join(lib_dir, lib)
            if not lib.endswith(".so") or os.path.islink(path):
                continue
            try:
                self._sign_elf_atomically(path, objcopy, signer)
                re_signed += 1
            except Exception as exc:  # noqa: BLE001 - best-effort refresh
                self.output.warning(f"in-place re-sign failed for {lib}: {exc}")
        self.output.info(
            f"[ohos] refreshed .codesign signatures for {re_signed} package shared libraries"
        )

    def _check_package_layout(self):
        lib_dir = self._package_lib_dir()
        if not os.path.isdir(lib_dir):
            raise ConanInvalidConfiguration(
                f"[ohos] package lib dir missing: {lib_dir}"
            )

        all_entries = sorted(os.listdir(lib_dir))
        libs = sorted(
            name
            for name in all_entries
            if name.startswith("libboost_") and name.endswith(".so")
        )
        if not libs:
            raise ConanInvalidConfiguration(
                f"[ohos] no libboost_*.so found under {lib_dir}"
            )

        versioned = sorted(
            name
            for name in all_entries
            if name.startswith("libboost_") and re.search(r"\.so\.\d", name)
        )
        if versioned:
            raise ConanInvalidConfiguration(
                "[ohos] versioned boost soname links found "
                f"(HMDFS-incompatible, patch + BOOST_INSTALL_NO_VERSIONED_LIBS should "
                f"have removed them): {versioned}"
            )

        objcopy = self._find_ohos_tool("llvm-objcopy")
        if not objcopy:
            raise ConanInvalidConfiguration(
                "[ohos] llvm-objcopy required for .codesign layout check"
            )
        dump = os.path.join(self.build_folder, ".codesign-check.out")
        missing = []
        for lib in libs:
            path = os.path.join(lib_dir, lib)
            if os.path.islink(path):
                continue
            if not self._has_codesign_section(objcopy, path, dump):
                missing.append(lib)
        if missing:
            raise ConanInvalidConfiguration(
                f"[ohos] libboost_*.so missing .codesign section: {missing}"
            )

        self.output.info(
            f"[ohos] package layout OK: {len(libs)} libboost_*.so, "
            "0 versioned soname links, every .so carries a .codesign section"
        )

    def _has_codesign_section(self, objcopy, path, dump):
        if os.path.exists(dump):
            os.remove(dump)
        try:
            rc = self.run(
                f'"{objcopy}" --dump-section .codesign="{dump}" "{path}"',
                quiet=True,
            )
        except Exception:  # noqa: BLE001
            return False
        return rc == 0 and os.path.isfile(dump) and os.path.getsize(dump) > 0

    def _sign_executable(self, executable):
        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            raise ConanInvalidConfiguration(
                "OHOS consumer execution requires llvm-objcopy and binary-sign-tool"
            )
        self._sign_elf_atomically(executable, objcopy, signer)

    def _sign_elf_atomically(self, path, objcopy, signer):
        original_mode = os.stat(path).st_mode
        temporary = f"{path}.signing"
        try:
            shutil.copy2(path, temporary)
            self.run(f'"{objcopy}" --remove-section .codesign "{temporary}"')
            self.run(
                f'"{signer}" sign -inFile "{temporary}" '
                f'-outFile "{temporary}" -selfSign 1'
            )
            os.chmod(temporary, original_mode)
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.remove(temporary)

    def _find_ohos_tool(self, name):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler_dir = os.path.dirname(compilers.get("cpp", ""))
        candidates = [
            os.path.join(compiler_dir, name) if compiler_dir else "",
            os.path.join("/data/service/hnp/bin", name),
            shutil.which(name) or "",
        ]
        return next((path for path in candidates if os.path.isfile(path)), "")
