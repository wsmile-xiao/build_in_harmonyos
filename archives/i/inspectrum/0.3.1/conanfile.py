#!/usr/bin/env python3
"""Conan recipe for inspectrum 0.3.1 on HarmonyOS PC (aarch64).

inspectrum is a Qt5 GUI tool for analysing captured RF signals: it renders a
spectrogram and time-domain traces from raw sample files (cfile/cf32, cs16,
cs8, sigmf-data, ...).  CMake build, GPL-3.0-or-later.

Upstream build surface (src/CMakeLists.txt):

  find_package(Qt5Widgets REQUIRED)
  find_package(Qt5Concurrent REQUIRED)
  find_package(FFTW REQUIRED)     # custom module, float precision (fftw3f)
  find_package(Liquid REQUIRED)   # custom module (libliquid from liquid-dsp)

OHOS-specific adaptations:

  - Qt5Widgets/Qt5Concurrent come from the published qt5-qtbase/5.15.2.2
    package.  That package ships the real Qt5 CMake config files, so its
    package root is put on CMAKE_PREFIX_PATH directly (neovim-qt 0.2.19
    precedent); the stale mkspec path baked into
    Qt5CoreConfigExtrasMkspecDir.cmake is rewritten at generate() time.
  - The custom FindFFTW/FindLiquid modules honour pre-set cache variables,
    so FFTW_INCLUDES/FFTW_LIBRARIES and LIQUID_INCLUDES/LIQUID_LIBRARIES are
    passed as absolute paths into the dependency packages (fftw3f/3.3.10 for
    the single-precision fftw3f that upstream requires; the published
    fftw/3.3.11 only carries the double-precision fftw3).  No source patch
    and no pkg-config lookup are needed.
  - The GUI cannot attach to a display server on OHOS and a GUI process
    never exits headlessly (it enters the Qt event loop), so the packaged
    executable is verified with a bounded startup smoke test under
    QT_QPA_PLATFORM=offscreen (neovim-qt / isoimagewriter precedent): the
    process must survive 15s without crashing and show evidence of a fully
    initialized QApplication in its log.
  - The installed ELF is re-signed with the OHOS signing tool, because the
    RPATH rewrite invalidates the original code signature and an unsigned
    ELF cannot be executed by test_package (isoimagewriter precedent).
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class InspectrumConan(ConanFile):
    name = "inspectrum"
    version = "0.3.1"
    description = ("inspectrum: a tool for analysing captured RF signals "
                   "(Qt5 spectrogram viewer)")
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/miek/inspectrum"
    url = "https://github.com/miek/inspectrum/archive/refs/tags/v0.3.1.tar.gz"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    options = {}
    default_options = {}

    def export_sources(self):
        # 本包无源码补丁（patches/ 为空），保留标准管线以通过 G1。
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"inspectrum only supports Linux and OHOS, got {self.settings.os}"
            )

    def requirements(self):
        # Qt5 Widgets/Concurrent (5.15.2.2 carries the full Qt5Widgets,
        # 5.15.2 was configured -no-widgets — neovim-qt precedent).
        self.requires("qt5-qtbase/5.15.2.2")
        # Single-precision FFTW: upstream's FindFFTW looks for fftw3f.
        self.requires("fftw3f/3.3.10")
        self.requires("liquid-dsp/1.8.2")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        qtbase_pkg = self.dependencies["qt5-qtbase"].package_folder
        fftw3f_pkg = self.dependencies["fftw3f"].package_folder
        liquid_pkg = self.dependencies["liquid-dsp"].package_folder

        tc = CMakeToolchain(self)
        # Upstream find_package(Qt5Widgets) is satisfied by the real Qt5
        # config files shipped inside the qt5-qtbase package.
        tc.cache_variables["CMAKE_PREFIX_PATH"] = qtbase_pkg
        # Pre-set the custom Find module cache variables with absolute paths
        # (find_path/find_library skip the search when the cache is set).
        # liquid-dsp/1.8.2 ships a static libliquid.a; prefer a shared
        # libliquid.so when a future package revision ships one.
        liquid_lib = self._dep_lib(liquid_pkg, "libliquid.so", "libliquid.a")
        tc.cache_variables["FFTW_INCLUDES"] = os.path.join(fftw3f_pkg, "include")
        tc.cache_variables["FFTW_LIBRARIES"] = self._dep_lib(fftw3f_pkg, "libfftw3f.so", "libfftw3f.a")
        tc.cache_variables["LIQUID_INCLUDES"] = os.path.join(liquid_pkg, "include")
        tc.cache_variables["LIQUID_LIBRARIES"] = liquid_lib
        # enable_testing() is declared upstream but no add_test() exists;
        # skip the CTest plumbing.
        tc.cache_variables["BUILD_TESTING"] = "OFF"
        # AUTOMOC needs the host moc from the qtbase package bin/.
        tc.cache_variables["CMAKE_PROGRAM_PATH"] = os.path.join(qtbase_pkg, "bin")
        # Upstream declares cmake_minimum_required(VERSION 3.1); CMake >= 4
        # removed compatibility with < 3.5 — let configure proceed anyway.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()
        self._patch_qtbase_cmake_configs(qtbase_pkg)

    def _patch_qtbase_cmake_configs(self, qtbase_pkg):
        """Fix stale build-machine paths baked into the published Qt config.

        Qt5CoreConfigExtrasMkspecDir.cmake hardcodes
        "${_qt5Core_install_prefix}/../b//mkspecs/linux-clang" from the
        builder's layout; find_package(Qt5Core) validates that file exists
        and fails in a clean environment.  Rewrite it to the in-package path
        (neovim-qt 0.2.19 precedent).
        """
        mkspec_cmake = os.path.join(
            qtbase_pkg, "lib", "cmake", "Qt5Core",
            "Qt5CoreConfigExtrasMkspecDir.cmake")
        if os.path.exists(mkspec_cmake):
            from conan.tools.files import load, save
            content = load(self, mkspec_cmake)
            fixed = content.replace(
                "${_qt5Core_install_prefix}/../b//mkspecs/linux-clang",
                "${_qt5Core_install_prefix}/mkspecs/linux-clang")
            if fixed != content:
                save(self, mkspec_cmake, fixed)
                self.output.info(
                    "patched Qt5CoreConfigExtrasMkspecDir.cmake: "
                    "../b//mkspecs -> mkspecs")

    def build(self):
        # 本包无源码补丁（patches/ 为空），apply_conandata_patches 为 no-op。
        apply_conandata_patches(self)
        cmake = CMake(self)
        with self._runtime_env().vars(self).apply():
            self._cmake_step("configure", cmake.configure)
            self._cmake_step("build", cmake.build)

    def package(self):
        cmake = CMake(self)
        with self._runtime_env().vars(self).apply():
            self._cmake_step("install", cmake.install)
        self._sign_ohos_elf_tree(self.package_folder)

    def _cmake_step(self, label, runner):
        """Run one CMake step with its stdout/stderr bound to a log file.

        ``ConanFile.run()`` hands the recipe process' output streams to the
        child; on this platform clang then fails on every compilation unit
        without emitting a single diagnostic line and make only reports
        "Error 1" (libncurses 6.6_p20260516 precedent).
        """
        log_dir = os.path.join(self.build_folder, "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, f"{label}.log")
        self.output.info(f"CMake step '{label}' log: {log_path}")
        with open(log_path, "w") as log:
            try:
                runner(stdout=log, stderr=log)
            except Exception as error:
                self.output.error(
                    f"CMake step '{label}' failed; tail of {log_path}:"
                )
                try:
                    with open(log_path, "r", errors="replace") as handle:
                        tail = handle.read().splitlines()[-80:]
                except OSError:
                    tail = ["<log unavailable>"]
                self.output.error("\n".join(tail))
                raise ConanException(
                    f"CMake step '{label}' failed, full log: {log_path}"
                ) from error

    def package_info(self):
        # Application package: consumers resolve bin/inspectrum through
        # bindirs, there is no library to export.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []

    # ── OHOS helpers ────────────────────────────────────────────────────
    @staticmethod
    def _dep_lib(pkg_folder, *names):
        """Return the first existing library path inside <pkg>/lib."""
        for name in names:
            candidate = os.path.join(pkg_folder, "lib", name)
            if os.path.isfile(candidate):
                return candidate
        raise ConanException(
            f"none of {names} found in {os.path.join(pkg_folder, 'lib')}")

    def _runtime_env(self):
        """LD_LIBRARY_PATH/PATH for configure, build and install.

        The AUTOMOC-launched host moc links against the Qt5Core shared
        library inside the qtbase package, and the inherited shell
        LD_LIBRARY_PATH carries whitespace-padded entries the OHOS loader
        cannot resolve (isoimagewriter 26.04.0 precedent).
        """
        env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                env.prepend_path("LD_LIBRARY_PATH",
                                 os.path.join(dep.package_folder, "lib"))
                env.prepend_path("LD_LIBRARY_PATH",
                                 os.path.join(dep.package_folder, "bin"))
                env.prepend_path("PATH", os.path.join(dep.package_folder, "bin"))
                env.prepend_path("QT_PLUGIN_PATH",
                                 os.path.join(dep.package_folder, "plugins"))
                env.prepend_path("QT_PLUGIN_PATH",
                                 os.path.join(dep.package_folder, "lib", "plugins"))
        for system_lib in ("/system/lib64", "/system/lib64/platformsdk",
                           "/system/lib64/ndk"):
            env.append_path("LD_LIBRARY_PATH", system_lib)
        env.define("QT_QPA_PLATFORM", "offscreen")
        return env

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _find_ohos_tool(self, name):
        candidates = []
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        for compiler in (compilers.get("c"), compilers.get("cpp")):
            if compiler:
                candidates.append(os.path.join(os.path.dirname(compiler), name))
        found = shutil.which(name)
        if found:
            candidates.append(found)
        candidates.append(os.path.join("/data/service/hnp/bin", name))
        return next((path for path in candidates if path and os.path.isfile(path)), "")

    @staticmethod
    def _quote(value):
        return '"' + str(value).replace('"', '\\"') + '"'

    def _sign_ohos_elf_tree(self, root_folder):
        """Re-sign every ELF in the package: the RPATH rewrite invalidates the
        original OHOS signature and an unsigned ELF cannot be executed."""
        if str(self.settings.os) not in ("OHOS", "HarmonyOS") or not os.path.isdir(root_folder):
            return
        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            raise ConanException("Cannot locate OHOS ELF signing tools")
        signed = 0
        for root, _, files in os.walk(root_folder):
            for name in files:
                path = os.path.join(root, name)
                if os.path.islink(path) or not self._is_elf(path):
                    continue
                self.run(f"{self._quote(objcopy)} --remove-section .codesign {self._quote(path)}", ignore_errors=True)
                self.run(f"{self._quote(signer)} sign -inFile {self._quote(path)} -outFile {self._quote(path)} -selfSign 1")
                signed += 1
        self.output.info(f"Signed {signed} OHOS package ELF file(s)")
