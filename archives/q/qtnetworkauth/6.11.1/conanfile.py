#!/usr/bin/env python3
"""Conan recipe for Qt NetworkAuth 6.11.1 on HarmonyOS PC."""

import os
import shutil
import stat
import subprocess
import sys
import tempfile
import textwrap

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)


class QtnetworkauthConan(ConanFile):
    name = "qtnetworkauth"
    version = "6.11.1"
    description = "Qt NetworkAuth (OAuth1/OAuth2) module for HarmonyOS PC"
    license = "BSD-3-Clause AND LGPL-3.0-only AND GPL-3.0-only"
    homepage = "https://doc.qt.io/qt-6/qtnetworkauth-index.html"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    # Upstream Qt NetworkAuth auto-test subset. Chosen to be self-contained:
    # they exercise the public OAuth API and signature math without opening
    # sockets or spinning up a local HTTP server, so they are safe to run on
    # the OHOS SSH shell (no network permission, no AF_UNIX server).
    # NOTE: tst_abstractoauth is gated behind QT_FEATURE_private_tests (off by
    # default) so it is not built; tst_abstractoauth2 builds unconditionally.
    _upstream_test_targets = (
        "tst_oauth1signature",
        "tst_abstractoauth2",
    )

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os != "OHOS":
            raise ConanInvalidConfiguration(
                "qtnetworkauth/6.11.1 in this recipe is a HarmonyOS PC adaptation"
            )

    def requirements(self):
        # QtNetworkAuth depends on Qt::Core and Qt::Network, both packaged by
        # qtbase. Use the dependency-free 6.11.1 base (no external Conan deps,
        # verified to build offline on OHOS).
        self.requires("qtbase/6.11.1")

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # qtbase uses cmake_find_mode "none" and ships its own relocatable
        # Qt6Config.cmake files, so expose its package dir to CMake directly.
        qtbase_prefix = self.dependencies["qtbase"].package_folder
        tc.cache_variables["CMAKE_PREFIX_PATH"] = qtbase_prefix
        # qtbase's install carries Platform/HarmonyOS.cmake; without it CMake
        # treats HarmonyOS as an unknown platform and skips shared-library
        # SOVERSION/SONAME handling.
        qtbase_platforms = os.path.join(
            qtbase_prefix, "lib", "cmake", "Qt6", "platforms"
        )
        tc.cache_variables["CMAKE_MODULE_PATH"] = qtbase_platforms
        tc.cache_variables.update(
            {
                "QT_QMAKE_TARGET_MKSPEC": "harmonyos-clang",
                "BUILD_SHARED_LIBS": "ON" if self.options.shared else "OFF",
                "QT_BUILD_TESTS": "ON",
                "QT_BUILD_TESTS_BY_DEFAULT": "OFF",
                "QT_BUILD_EXAMPLES": "OFF",
                "QT_BUILD_EXAMPLES_BY_DEFAULT": "OFF",
            }
        )
        if str(self.settings.os) == "OHOS":
            # The OHOS Clang driver advertises ARM crypto features while the
            # platform arm_neon.h lacks the AES intrinsics used by Qt's hash
            # (OAuth signatures use QCryptographicHash/HMAC).
            tc.extra_cxxflags.append("-DQT_NO_ARM_AES_INTRINSICS")
            self.output.info(
                "ARM AES intrinsics unavailable; "
                "defining QT_NO_ARM_AES_INTRINSICS"
            )
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        self._materialize_cmake_symlink_library_rules()
        cmake.build()
        for target in self._upstream_test_targets:
            cmake.build(target=target)
        if can_run(self):
            test_env = Environment()
            test_env.define("QT_QPA_PLATFORM", "offscreen")
            test_env.define("QT_LOGGING_RULES", "qt.qpa.*=false")
            qtbase_lib = os.path.join(
                self.dependencies["qtbase"].package_folder, "lib"
            )
            build_lib = os.path.join(self.build_folder, "lib")
            test_env.append_path("LD_LIBRARY_PATH", qtbase_lib)
            test_env.append_path("LD_LIBRARY_PATH", build_lib)
            pattern = "^({})$".format("|".join(self._upstream_test_targets))
            with test_env.vars(self).apply():
                self.run(
                    f'ctest --output-on-failure -R "{pattern}"',
                    cwd=self.build_folder,
                    env="conanrun",
                )

    def _materialize_cmake_symlink_library_rules(self):
        """Replace CMake build-time symlinks with file copies on OHOS.

        HMDFS does not support symlinks; CMake's cmake_symlink_library rule
        fails with Permission denied when linking shared libraries. Replace it
        with a copy helper so libQt6NetworkAuth.so / .so.6 are real files.
        """
        if str(self.settings.os) != "OHOS":
            return

        script_path = os.path.join(
            self.build_folder, "conan_copy_library_links.py"
        )
        with open(script_path, "w", encoding="utf-8") as script:
            script.write(
                textwrap.dedent(
                    """\
                    import os
                    import shutil
                    import sys


                    def copy_link(source, destination):
                        if not destination or destination == source:
                            return
                        if os.path.lexists(destination):
                            if os.path.isdir(destination) and not os.path.islink(destination):
                                raise RuntimeError(
                                    f"Refusing to replace directory: {destination}"
                                )
                            os.unlink(destination)
                        shutil.copy2(source, destination)


                    if len(sys.argv) < 3:
                        raise SystemExit("usage: copy-library-links.py SOURCE LINK...")
                    for link in sys.argv[2:]:
                        copy_link(sys.argv[1], link)
                    """
                )
            )

        replacement = f'"{sys.executable}" "{script_path}"'
        needle = "$(CMAKE_COMMAND) -E cmake_symlink_library"
        patched = 0
        for root, _, filenames in os.walk(self.build_folder):
            for filename in filenames:
                if not filename.endswith(".make"):
                    continue
                path = os.path.join(root, filename)
                with open(path, "r", encoding="utf-8") as makefile:
                    content = makefile.read()
                if needle not in content:
                    continue
                with open(path, "w", encoding="utf-8") as makefile:
                    makefile.write(content.replace(needle, replacement))
                patched += 1
        if patched:
            self.output.info(
                f"Materialized {patched} CMake cmake_symlink_library rule(s)"
            )

    def _ensure_soname_link_copies(self):
        """Ensure .so / .so.6 entries exist without symlinks after install."""
        libdir = os.path.join(self.package_folder, "lib")
        if not os.path.isdir(libdir):
            return
        version_suffix = ".so.6"
        for root, _, filenames in os.walk(libdir):
            for filename in filenames:
                if not filename.startswith("libQt6") or not filename.endswith(
                    version_suffix
                ):
                    continue
                stem = filename[: -len(version_suffix)]
                for link_name in (f"{stem}.so.6", f"{stem}.so"):
                    link = os.path.join(root, link_name)
                    if os.path.islink(link):
                        os.unlink(link)
                    if not os.path.lexists(link):
                        shutil.copy2(os.path.join(root, filename), link)

    def package(self):
        cmake = CMake(self)
        cmake.install()
        self._ensure_soname_link_copies()
        if str(self.settings.os) == "OHOS":
            self._sign_installed_elfs()

    def _sign_installed_elfs(self):
        """Re-sign installed OHOS ELF executables and shared objects."""
        binaries = []
        for root, _, filenames in os.walk(self.package_folder):
            for filename in filenames:
                candidate = os.path.join(root, filename)
                if os.path.islink(candidate):
                    continue
                if self._elf_type(candidate) in (2, 3):  # ET_EXEC, ET_DYN
                    binaries.append(candidate)
        if not binaries:
            return
        objcopy = self._resolve_tool("OBJCOPY", "llvm-objcopy")
        objdump = self._resolve_tool("OBJDUMP", "llvm-objdump")
        signer = self._resolve_tool("BINARY_SIGN_TOOL", "binary-sign-tool")
        for binary in sorted(binaries):
            original_mode = stat.S_IMODE(os.stat(binary).st_mode)
            with tempfile.TemporaryDirectory(
                prefix=".conan-sign-", dir=os.path.dirname(binary)
            ) as temp_dir:
                unsigned = os.path.join(temp_dir, "unsigned")
                signed = os.path.join(temp_dir, "signed")
                shutil.copy2(binary, unsigned)
                if self._has_codesign_section(objdump, unsigned):
                    self._run_tool(
                        [objcopy, "--remove-section", ".codesign", unsigned],
                        f"remove the old code signature from {binary}",
                    )
                self._run_tool(
                    [
                        signer,
                        "sign",
                        "-inFile",
                        unsigned,
                        "-outFile",
                        signed,
                        "-selfSign",
                        "1",
                    ],
                    f"sign {binary}",
                )
                if not os.path.isfile(signed) or self._elf_type(signed) not in (2, 3):
                    raise ConanInvalidConfiguration(
                        f"Signing did not produce a runnable ELF file for {binary}"
                    )
                if not self._has_codesign_section(objdump, signed):
                    raise ConanInvalidConfiguration(
                        f"Signing did not add a .codesign section to {binary}"
                    )
                os.replace(signed, binary)
                os.chmod(binary, original_mode)

    def _has_codesign_section(self, objdump, path):
        section_table = self._run_tool(
            [objdump, "-h", path], f"inspect ELF sections in {path}"
        )
        return any(
            ".codesign" in line.split()
            for line in section_table.splitlines()
        )

    @staticmethod
    def _run_tool(command, action):
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=60,
            )
        except (OSError, subprocess.SubprocessError) as error:
            raise ConanInvalidConfiguration(f"Unable to {action}: {error}") from error
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip()
            raise ConanInvalidConfiguration(
                f"Unable to {action}: {detail or 'tool exited unsuccessfully'}"
            )
        return result.stdout

    @staticmethod
    def _elf_type(path):
        """Return the ELF e_type value, or None for a non-ELF file."""
        try:
            with open(path, "rb") as binary:
                header = binary.read(18)
        except OSError as error:
            raise ConanInvalidConfiguration(
                f"Unable to inspect installed file {path}: {error}"
            ) from error
        if len(header) < 18 or header[:4] != b"\x7fELF":
            return None
        byte_order = {1: "little", 2: "big"}.get(header[5])
        if byte_order is None:
            raise ConanInvalidConfiguration(
                f"Unsupported ELF byte order in installed file {path}"
            )
        return int.from_bytes(header[16:18], byte_order)

    @staticmethod
    def _resolve_tool(environment_variable, executable):
        configured = os.environ.get(environment_variable)
        candidate = configured or executable
        resolved = shutil.which(candidate)
        if (
            not resolved
            and os.path.isfile(candidate)
            and os.access(candidate, os.X_OK)
        ):
            resolved = os.path.abspath(candidate)
        if (
            not resolved
            or not os.path.isfile(resolved)
            or not os.access(resolved, os.X_OK)
        ):
            raise ConanInvalidConfiguration(
                f"Required tool {executable} was not found; set "
                f"{environment_variable} or add it to PATH"
            )
        return os.path.abspath(resolved)

    def package_info(self):
        # Qt installs complete, relocatable Qt6NetworkAuthConfig.cmake files.
        # Prevent CMakeDeps from shadowing them with an incomplete generated config.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]

        networkauth = self.cpp_info.components["networkauth"]
        networkauth.libs = ["Qt6NetworkAuth"]
        networkauth.requires = ["qtbase::core", "qtbase::network"]
        networkauth.set_property("cmake_target_name", "Qt6::NetworkAuth")
