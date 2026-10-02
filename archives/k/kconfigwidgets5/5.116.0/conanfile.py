#!/usr/bin/env python3
"""Conan recipe for kconfigwidgets5 5.116.0 (KDE Frameworks 5 / Qt5) on
HarmonyOS PC.

kconfigwidgets5 is the KDE Frameworks configuration-dialogs library (builds
libKF5ConfigWidgets). It provides KConfigDialog (a KPageDialog subclass),
KConfigDialogManager, KStandardAction, KColorScheme, KCodecAction,
KRecentFilesAction, KCModule and friends.

OHOS-specific adaptations (KF5 chain, knotifications5/kconfig5/kcoreaddons5/
ki18n5 5.116.0 precedents):
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS not
    in KDE platform list).
  - CMAKE_SYSTEM_NAME=Linux: the OHOS CMake platform has no
    Platform/HarmonyOS module, so `UNIX` is not set and KDEInstallDirs /
    KDECMakeSettings `if(UNIX)` install-path selection would misbehave;
    forcing the Linux platform is POSIX-compatible (knotifications5 /
    kcoreaddons5 5.116.0 precedents).
  - WITH_KAUTH=OFF: KF5Auth is not published to ohpcd and KAuth support is
    optional upstream (guarded by the WITH_KAUTH option and the
    KCONFIGWIDGETS_WITH_KAUTH define; only kcmodule.cpp consults it for the
    deprecated KAuth handshake). The core widgets stay fully functional.
  - BUILD_DESIGNERPLUGIN=OFF (Qt5UiPlugin not published).
  - USE_DBUS / Qt5DBus: the packaged qt5-qtbase/5.15.2.2 DOES ship the real
    Qt5DBus library + cmake config, so the upstream
    `if (NOT ANDROID) find_package(Qt5 REQUIRED DBus)` resolves and only
    KPasteTextAction (PRIVATE) links it — kept ON to match the kconfig5
    5.116.0 precedent (KCONFIG_USE_DBUS=ON).
  - ki18n_install(po) disabled via patch 0001: it needs the full
    LinguistTools/po toolchain not shipped by the packaged OHOS Qt5
    (kconfig5 ecm_install_po_files_as_qm precedent).
  - qt5-qtbase/5.15.2.2 pinned with override=True to unify the qt5-qtbase
    line declared as 5.15.2 by kcoreaddons5 (binary-compatible recipe-fix
    release, knotifications5 precedent).
  - ECM_MODULE_PATH set manually because the CMakeDeps-generated
    ECMConfig.cmake does not propagate the variable the project relies on.
  - conan_cmakedeps_paths.cmake created manually to prepend the KF5
    dependencies' lib/cmake dirs (the KF5 packages ship their own installed
    Config.cmake files via builddirs) ahead of the CMakeDeps component
    configs.
  - CMAKE_SHARED_LIBRARY_SONAME flags injected: the OHOS (Generic) CMake
    platform defines no soname rule, so without them libKF5ConfigWidgets.so
    would ship without DT_SONAME (E537/CI L5 gate, kconfig5 precedent).
  - CMAKE_AUTOMOC/AUTORCC_EXECUTABLE pointed at the qt5-qtbase bin/moc and
    bin/rcc (CMakeDeps does not export Qt5::moc/rcc, ki18n5 precedent).
  - /system/lib64 prepended to LD_LIBRARY_PATH for configure/build/test
    runs (sandbox libc++_shared.so shadowing, kconfig5 precedent).
  - Installed ELFs re-signed with binary-sign-tool in package(): the OHOS
    loader rejects the placeholder .codesign emitted by the OHOS lld for
    locally built libraries (dlopen fails with "Permission denied");
    knotifications5 / qt-5.15.19 package precedent.
"""
import glob
import os
import shutil
import stat
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    load,
    save,
)


class Kconfigwidgets5Conan(ConanFile):
    name = "kconfigwidgets5"
    version = "5.116.0"
    description = "KDE Frameworks 5 - Widgets for configuration dialogs (libKF5ConfigWidgets)"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/kconfigwidgets"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Pin the qt5-qtbase line to 5.15.2.2 (overrides the qt5-qtbase/5.15.2
        # declared by kcoreaddons5; 5.15.2.2 is its recipe-fix release and is
        # binary-compatible for the Qt5Core consumers) — knotifications5
        # validated pattern.
        self.requires("qt5-qtbase/5.15.2.2", override=True)
        self.requires("kconfig5/5.116.0")
        self.requires("kcoreaddons5/5.116.0")
        self.requires("kguiaddons5/5.116.0")
        self.requires("ki18n5/5.116.0")
        self.requires("kwidgetsaddons5/5.116.0")
        self.requires("kcodecs5/5.116.0")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        # Regenerate a clean aggregated Qt5Config (qt5-qtbase only ships
        # per-module configs; find_package(Qt5 COMPONENTS ...) needs one).
        deps.set_property("qt5-qtbase", "cmake_file_name", "Qt5")
        deps.generate()

        tc = CMakeToolchain(self)
        shared = bool(self.options.shared)
        tc.variables["BUILD_SHARED_LIBS"] = shared
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["QT_MAJOR_VERSION"] = "5"
        tc.variables["KDE_INSTALL_USE_QT_SYS_PATHS"] = "OFF"
        tc.variables["BUILD_QCH"] = "OFF"
        # KAuth is optional upstream; KF5Auth is not published to ohpcd.
        tc.variables["WITH_KAUTH"] = "OFF"
        # Qt Designer plugin needs Qt5UiPlugin (not published).
        tc.variables["BUILD_DESIGNERPLUGIN"] = "OFF"
        # See class docstring: force the Linux platform so KDEInstallDirs'
        # if(UNIX) install-path selection works (knotifications5 precedent).
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        # SONAME emission on OHOS (E537 / CI L5 gate, kconfig5 precedent).
        tc.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "TRUE"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"

        # ECM's CMakeDeps-generated ECMConfig.cmake does not propagate
        # ECM_MODULE_PATH; set it manually so KDE cmake modules
        # (KDEInstallDirs, KDECMakeSettings, ...) are found.
        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_DIR"] = os.path.join(ecm_share, "cmake")
            tc.variables["ECM_MODULE_PATH"] = ";".join([
                os.path.join(ecm_share, "modules"),
                os.path.join(ecm_share, "find-modules"),
                os.path.join(ecm_share, "kde-modules"),
            ])

        qt5 = self.dependencies["qt5-qtbase"]
        moc_path = os.path.join(qt5.package_folder, "bin", "moc")
        rcc_path = os.path.join(qt5.package_folder, "bin", "rcc")
        if not os.path.isfile(moc_path):
            raise RuntimeError(
                "qt5-qtbase/5.15.2.2 does not provide bin/moc"
            )
        if not os.path.isfile(rcc_path):
            raise RuntimeError(
                "qt5-qtbase/5.15.2.2 does not provide bin/rcc"
            )
        tc.variables["CMAKE_AUTOMOC_EXECUTABLE"] = moc_path
        tc.variables["CMAKE_AUTORCC_EXECUTABLE"] = rcc_path
        tc.generate()

        # conan_cmakedeps_paths.cmake created manually: qt5-qtbase uses
        # cmake_find_mode=none so CMakeDeps does not add its lib/cmake dir to
        # CMAKE_PREFIX_PATH; the KF5 deps ship their own installed
        # Config.cmake files via builddirs which must win over the CMakeDeps
        # component configs (knotifications5 precedent).
        extra_paths = []
        if ecm:
            ecm_cmake = os.path.join(ecm.package_folder, "share", "ECM", "cmake")
            extra_paths.append(
                ('list(PREPEND CMAKE_MODULE_PATH "%s")\n'
                 'list(PREPEND CMAKE_PREFIX_PATH "%s")') % (ecm_cmake, ecm_cmake)
            )
        extra_paths.append(
            'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")\n'
            'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")'
        )
        for dep_name in ("kconfig5", "kcoreaddons5", "kguiaddons5",
                         "ki18n5", "kwidgetsaddons5", "kcodecs5"):
            dep = self.dependencies.get(dep_name)
            if dep and dep.package_folder:
                extra_paths.append(
                    'list(PREPEND CMAKE_PREFIX_PATH "%s/lib/cmake")'
                    % dep.package_folder.replace("\\", "/")
                )
        qt_pkg = qt5.package_folder.replace("\\", "/")
        extra_paths.append(
            ('list(PREPEND CMAKE_PREFIX_PATH "%s/lib/cmake")\n'
             'list(PREPEND CMAKE_LIBRARY_PATH "%s/lib")\n'
             'list(PREPEND CMAKE_INCLUDE_PATH "%s/include")') % (qt_pkg, qt_pkg, qt_pkg)
        )
        extra_paths.append('set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)')
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w", encoding="utf-8") as f:
            f.write("\n".join(extra_paths) + "\n")

    @staticmethod
    def _prepare_qt_mkspec_compat(qt_package_folder):
        # The qt5-qtbase conan package stores its full mkspec tree under
        # <pkg>/mkspecs. Downstream Qt builds compile against the build-side
        # mkspec path <pkg>/../b/mkspecs/linux-clang whose qplatformdefs.h
        # does `#include "../common/posix/qplatformdefs.h"`. On a clean CI
        # worker the b/mkspecs dir may be missing; mirror the mkspecs tree so
        # the relative include always resolves (kconfig5/attica5 pattern).
        src_mkspecs = os.path.join(qt_package_folder, "mkspecs")
        dst_mkspecs = os.path.join(
            os.path.dirname(qt_package_folder), "b", "mkspecs"
        )
        if os.path.isdir(src_mkspecs):
            for rel in ("linux-clang", "common"):
                src = os.path.join(src_mkspecs, rel)
                dst = os.path.join(dst_mkspecs, rel)
                if os.path.isdir(src) and not os.path.islink(dst) and not os.path.isdir(dst):
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copytree(src, dst)

    def _cmake_build_env(self):
        # Sandbox libc++_shared.so shadowing fix (kconfig5 precedent): the
        # SDK's aarch64-linux-ohos libc++.so is a linker script that shadows
        # the real system libc++_shared.so; prepend /system/lib64 and the SDK
        # llvm/lib dirs. Dependency libs (Qt5, KF5) are also prepended so
        # build-time tools shipped by the dependency packages
        # (kconfig_compiler_kf5 from kconfig5) can execute under make.
        env = Environment()
        if str(self.settings.os) == "OHOS":
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
            for llvm_lib in sorted(glob.glob(
                "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"
            )):
                env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
        for rel in ("bin", "lib"):
            env.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.build_folder, rel)
            )
        return env

    def build(self):
        if self.settings.os == "OHOS":
            apply_conandata_patches(self)
        qt5 = self.dependencies["qt5-qtbase"]
        self._prepare_qt_mkspec_compat(qt5.package_folder)
        cmake = CMake(self)
        with self._cmake_build_env().vars(self).apply():
            cmake.configure()
            cmake.build()
        self._run_upstream_tests()

    def _library_runtime_env(self):
        runtime_env = self._cmake_build_env()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                runtime_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
                runtime_env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
                )
                runtime_env.prepend_path(
                    "QT_QPA_PLATFORM_PLUGIN_PATH",
                    os.path.join(dep.package_folder, "plugins", "platforms"),
                )
        for rel in ("bin", "lib"):
            runtime_env.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.build_folder, rel)
            )
        # /system/lib64 back to the very front (prepend LAST = first in the
        # final path): the real system libc++.so must not be shadowed by the
        # SDK's linker-script libc++.so (needed by /system/lib64 consumers
        # like libhilog with the __h namespace symbols).
        if str(self.settings.os) == "OHOS":
            runtime_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return runtime_env

    def _run_upstream_tests(self):
        if not can_run(self):
            self.output.info(
                "Skipping upstream CTest during cross-compilation; target execution is required on OHOS"
            )
            return
        test_env = self._library_runtime_env()
        test_env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        test_env.define("CTEST_PARALLEL_LEVEL", "1")
        test_env.define("QT_QPA_PLATFORM", "offscreen")
        test_home = os.path.join(self.build_folder, "test-home")
        xdg_runtime = os.path.join(self.build_folder, "xdg-runtime")
        os.makedirs(test_home, exist_ok=True)
        os.makedirs(xdg_runtime, exist_ok=True)
        os.chmod(xdg_runtime, 0o700)
        test_env.define("HOME", test_home)
        test_env.define("XDG_RUNTIME_DIR", xdg_runtime)
        test_env.define("XDG_CACHE_HOME", os.path.join(test_home, ".cache"))
        test_env.define("XDG_CONFIG_HOME", os.path.join(test_home, ".config"))
        test_env.define("XDG_DATA_HOME", os.path.join(test_home, ".local", "share"))
        # Locally built / re-extracted KF5 ELFs carry a placeholder .codesign
        # the sandbox loader rejects; re-sign every shared library in the
        # build tree and the dependency caches before running ctest
        # (knotifications5 precedent, extended to the dependency packages).
        self._resign_runtime_elfs()
        self._prepare_ctest_runtime_links()
        # Test exclusions (OHOS platform limitations, kconfig5 precedent):
        # - kstandardactiontest::changingShortcut waits for the
        #   KStandardShortcutWatcher config-change notification which never
        #   fires on the OHOS sandbox (no inotify), QTRY_COMPARE times out
        #   with the shortcut list unchanged (5/6 slots pass, only this one
        #   fails).
        excluded = "|".join(["kstandardactiontest"])
        with test_env.vars(self).apply():
            self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error -E "({})"'.format(
                    self.build_folder, excluded
                )
            )

    def _resign_runtime_elfs(self):
        """Re-sign the KF5 shared libraries the tests load at runtime.

        The OHOS loader rejects ELFs whose .codesign section holds the
        placeholder signature the OHOS lld emits (dlopen fails with
        "Permission denied"). Libraries freshly built into this package's
        build tree and the locally chain-filled dependency packages
        (kguiaddons5/kcodecs5/kwidgetsaddons5, plus any re-extracted package
        binaries) all need a real signature from binary-sign-tool before
        they can be loaded by the test executables.
        """
        lib_dirs = set()
        for rel in ("bin", "lib"):
            lib_dirs.add(os.path.join(self.build_folder, rel))
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lib_dirs.add(os.path.join(dep.package_folder, "lib"))
        signer = self._resolve_tool("BINARY_SIGN_TOOL", "binary-sign-tool")
        objcopy = self._resolve_tool("OBJCOPY", "llvm-objcopy")
        for lib_dir in sorted(lib_dirs):
            if not os.path.isdir(lib_dir):
                continue
            for name in sorted(os.listdir(lib_dir)):
                path = os.path.join(lib_dir, name)
                if not os.path.isfile(path) or os.path.islink(path):
                    continue
                if not (name.startswith("lib") and ".so" in name):
                    continue
                if self._elf_type(path) not in (2, 3):
                    continue
                original_mode = stat.S_IMODE(os.stat(path).st_mode)
                with tempfile.TemporaryDirectory(
                    prefix=".conan-sign-", dir=lib_dir
                ) as temp_dir:
                    unsigned = os.path.join(temp_dir, "unsigned")
                    signed = os.path.join(temp_dir, "signed")
                    shutil.copy2(path, unsigned)
                    try:
                        self._run_tool(
                            [objcopy, "--remove-section", ".codesign", unsigned],
                            f"remove the old code signature from {path}",
                        )
                    except ConanInvalidConfiguration:
                        pass  # no .codesign section, sign directly
                    self._run_tool(
                        [signer, "sign", "-inFile", unsigned,
                         "-outFile", signed, "-selfSign", "1"],
                        f"sign {path}",
                    )
                    if not os.path.isfile(signed) or self._elf_type(signed) not in (2, 3):
                        raise ConanInvalidConfiguration(
                            f"Signing did not produce a runnable ELF file for {path}"
                        )
                    os.replace(signed, path)
                    os.chmod(path, original_mode)

    def _prepare_ctest_runtime_links(self):
        # The built KF5 libs and the dependency libs are symlinked next to
        # the build tree so the relative DT_NEEDED entries of the test
        # executables resolve (kconfig5 pattern).
        compatibility_bin = os.path.normpath(
            os.path.join(self.build_folder, os.pardir, "bin")
        )
        os.makedirs(compatibility_bin, exist_ok=True)
        lib_sources = glob.glob(os.path.join(self.build_folder, "bin", "lib*.so*"))
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lib_sources.extend(
                    glob.glob(os.path.join(dep.package_folder, "lib", "lib*.so*"))
                )
        for src in lib_sources:
            dst = os.path.join(compatibility_bin, os.path.basename(src))
            if os.path.exists(src) and not os.path.exists(dst):
                try:
                    os.symlink(src, dst)
                except OSError:
                    shutil.copy2(src, dst)

    def package(self):
        cmake = CMake(self)
        with self._cmake_build_env().vars(self).apply():
            cmake.install()
        if str(self.settings.os) == "OHOS":
            # The OHOS loader rejects the placeholder .codesign that the OHOS
            # lld emits for locally built shared libraries (dlopen fails with
            # "Permission denied" even though the section exists); re-sign
            # every installed ELF with binary-sign-tool so consumers and the
            # test_package can load libKF5ConfigWidgets.so
            # (knotifications5 / qt-5.15.19 package precedent).
            self._sign_installed_elfs()
        self._make_pkgconfig_relocatable()

    # ------------------------------------------------------------------
    # ELF self-signing (knotifications5 / qt-5.15.19 recipe precedent)
    # ------------------------------------------------------------------
    def _sign_installed_elfs(self):
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

    def _make_pkgconfig_relocatable(self):
        package_root = os.path.abspath(self.package_folder)
        pc_dir = os.path.join(self.package_folder, "lib", "pkgconfig")
        for pc_file in glob.glob(os.path.join(pc_dir, "*.pc")):
            content = load(self, pc_file)
            content = content.replace(
                f"prefix={package_root}", "prefix=${pcfiledir}/../..", 1
            )
            content = content.replace(
                f"libdir={package_root}/lib", "libdir=${prefix}/lib", 1
            )
            content = content.replace(
                f"includedir={package_root}/include", "includedir=${prefix}/include", 1
            )
            content = content.replace(f"-L{package_root}/lib", "-L${libdir}")
            content = content.replace(f"-I{package_root}/include", "-I${includedir}")
            save(self, pc_file, content)

    def package_info(self):
        # The project installs its own KF5ConfigWidgetsConfig.cmake with
        # proper dependency tracking (find_dependency on KF5Config etc). Use
        # cmake_find_mode=none so CMakeDeps doesn't shadow it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF5ConfigWidgets"]
        # preparetips5 is installed to bin/ by upstream (R38 tool surface).
        self.cpp_info.bindirs = ["bin"]
