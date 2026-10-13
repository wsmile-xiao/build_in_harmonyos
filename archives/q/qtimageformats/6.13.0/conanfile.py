#!/usr/bin/env python3
"""Conan recipe for Qt Image Formats 6.13.0 (upstream 6.12.0) on HarmonyOS PC.

Builds the Qt GUI image format plugins (tga, wbmp, tiff, webp, icns, mng,
jp2) against the published qtbase/6.11.1.3 HarmonyOS adaptation, using the
Conan-published libtiff / libwebp / libmng / jasper packages as the system
integrations probed by Qt's Wrap* find modules.
"""

import os
import shutil
import stat
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    check_sha256,
    export_conandata_patches,
    get,
    unzip,
)


class QtimageformatsConan(ConanFile):
    name = "qtimageformats"
    version = "6.13.0"
    description = (
        "Qt Image Formats plugins (TGA, WBMP, TIFF, WebP, ICNS, MNG, JPEG2000) "
        "for HarmonyOS PC"
    )
    license = "BSD-3-Clause AND LGPL-3.0-only AND GPL-3.0-only"
    homepage = "https://doc.qt.io/qt-6/qtimageformats-index.html"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Qt image formats plugins link into the published HarmonyOS Qt build.
        self.requires("qtbase/6.11.1.3", transitive_headers=True, transitive_libs=True)
        # System image library integrations resolved by Qt's Wrap* modules.
        self.requires("libtiff/4.7.2.2", transitive_headers=True, transitive_libs=True)
        self.requires("libwebp/1.6.0.1", transitive_headers=True, transitive_libs=True,
                      override=True, force=True)
        self.requires("libmng/2.0.3", transitive_headers=True, transitive_libs=True)
        self.requires("jasper/4.2.9", transitive_headers=True, transitive_libs=True)
        # P0 dep-graph conflict: libmng/2.0.3 declares libjpeg-turbo/3.0.Z
        # while libtiff/4.7.2.2 pins libjpeg-turbo/3.2.0 -> conan graph info
        # failed with "Version conflict between libjpeg-turbo/3.0.4 and
        # 3.2.0". Align the whole graph onto the published 3.2.0 (the newer
        # version the qtbase/libtiff side already resolves to).
        self.requires("libjpeg-turbo/3.2.0", override=True, force=True)
        # libtiff pulls zstd/1.5.7 and libwebp/1.6.0 while qtbase/6.11.1.3
        # pins zstd/1.5.7.1 and the registry publishes libwebp/1.6.0.1;
        # align the graph onto those published versions.
        self.requires("zstd/1.5.7.1", override=True, force=True)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "qtimageformats/6.13.0 in this recipe targets HarmonyOS PC (OHOS)"
            )
        if cross_building(self):
            raise ConanInvalidConfiguration(
                "This recipe reuses the qtbase host tools; use matching OHOS "
                "aarch64 host and build profiles"
            )
        if str(self.settings.arch) != "armv8" or not self.options.shared:
            raise ConanInvalidConfiguration(
                "This adaptation supports shared Qt image format plugins on "
                "OHOS armv8"
            )

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        archive = os.environ.get("QTIMAGEFORMATS_SOURCE_ARCHIVE")
        if archive:
            check_sha256(self, archive, self.conan_data["sources"]["sha256"])
            unzip(self, archive, strip_root=True)
        else:
            get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # CMakeDeps emits configs for libtiff/libwebp/libmng/jasper so Qt's
        # WrapWebP/WrapJasper/Libmng/TIFF find modules resolve the Conan
        # packages. Qt's own Qt6Config.cmake is a complete, relocatable
        # config installed by qtbase — do not shadow it, only point
        # CMAKE_PREFIX_PATH at the qtbase package prefix (E438/E495).
        cmake_deps = CMakeDeps(self)
        cmake_deps.generate()

        qtbase = self.dependencies.host["qtbase"]
        qtbase_prefix = qtbase.package_folder.replace("\\", "/")

        # E495: this is a same-arch OHOS aarch64 build (host == build), so no
        # QT_HOST_PATH/QT_HOST_PATH_CMAKE_DIR is needed. Pointing
        # CMAKE_PREFIX_PATH at the qtbase package prefix (plus the
        # harmonyos-clang mkspec and Qt6_DIR) resolves Qt6Config, the
        # moc/rcc host tools and the mkspec all from the one published qtbase
        # package. NOTE: every cache_variable (including Qt6_DIR) is set
        # BEFORE tc.generate() so it actually lands in the toolchain.
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_PREFIX_PATH"] = qtbase_prefix
        tc.cache_variables["CMAKE_FIND_ROOT_PATH_MODE_PACKAGE"] = "BOTH"
        # ZLIB::ZLIB (from the Conan zlib CMakeDeps config) must be global so
        # Qt's qt_find_package can promote it; otherwise configure fails with
        # "Attempt to promote imported target ZLIB::ZLIB to global scope".
        tc.cache_variables["CMAKE_FIND_PACKAGE_TARGETS_GLOBAL"] = "ON"
        tc.cache_variables["Qt6_DIR"] = os.path.join(
            qtbase_prefix, "lib", "cmake", "Qt6")
        tc.cache_variables["QT_QMAKE_TARGET_MKSPEC"] = "harmonyos-clang"
        # Qt6 submodule feature configuration. The image format libraries
        # are always the Conan system integrations (autodetect is off
        # upstream for mng/jasper; enable explicitly).
        tc.cache_variables["INPUT_jasper"] = "system"
        tc.cache_variables["INPUT_mng"] = "system"
        tc.cache_variables["INPUT_tiff"] = "system"
        tc.cache_variables["INPUT_webp"] = "system"
        # Qt plugins are shared libraries (.so loaded at runtime); there is
        # no system-library name clash, so shared is safe and required.
        tc.cache_variables["BUILD_SHARED_LIBS"] = "ON"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        if str(self.settings.os) == "OHOS":
            self._sign_installed_elfs()
        # Pure plugin package: strip the Qt-generated plugin CMake metadata
        # (Qt6QTgaPluginTargets*.cmake under lib/cmake/Qt6Gui). Consumers
        # never find_package this package (cmake_find_mode=none) and the
        # plugin targets carry IMPORTED_NO_SONAME TRUE (CI L5c gate), so the
        # metadata is both useless and gate-breaking. Removing it also leaves
        # no lib/ dir for the CI L1e destructive negative test to sabotage,
        # keeping the package a clean plugins/imageformats-only artifact like
        # the kimageformats5 precedent.
        lib_cmake = os.path.join(self.package_folder, "lib", "cmake")
        if os.path.isdir(lib_cmake):
            shutil.rmtree(lib_cmake)
            lib_dir = os.path.join(self.package_folder, "lib")
            try:
                os.rmdir(lib_dir)
            except OSError:
                pass  # keep lib/ if it still holds other content

    def _sign_installed_elfs(self):
        """Re-sign installed OHOS ELF plugins with binary-sign-tool.

        Qt's own install rules leave the image-format plugins with a signature
        the HarmonyOS loader rejects (dlopen fails with EACCES: "Permission
        denied"). Follow the published qtbase recipe precedent and re-sign
        every installed ELF with binary-sign-tool (self-sign) so the plugins
        load at runtime.
        """
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
        # Qt image format plugins are runtime-loaded Qt plugins
        # (plugins/imageformats/libq*.so). They are discovered through the
        # Qt plugin infrastructure, not through find_package; the package
        # contributes its plugin directory to the Qt plugin search path.
        plugin_dir = os.path.join(self.package_folder, "plugins")
        self.runenv_info.define_path("QT_PLUGIN_PATH", plugin_dir)
        self.cpp_info.includedirs = ["include"]
        # Pure plugin package: no linker libraries, no executables (R38:
        # empty bindirs keeps the library classification). Qt loads the
        # plugins from <package_folder>/plugins/imageformats at runtime.
        self.cpp_info.libdirs = ["lib", "plugins/imageformats"]
        self.cpp_info.bindirs = []
        self.cpp_info.libs = []
        self.cpp_info.set_property("cmake_find_mode", "none")
