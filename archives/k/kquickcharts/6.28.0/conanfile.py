#!/usr/bin/env python3
"""Conan recipe for kquickcharts 6.28.0 on HarmonyOS PC (arm64).

kquickcharts is the KDE Frameworks 6 Qt Quick Charts library. It ships as a
QML module ``org.kde.quickcharts`` (BarChart / LineChart / PieChart) plus an
extra controls module ``org.kde.quickcharts.controls``.

OHOS-specific adaptations (patterns follow attica/6.28.0 + qtquicktimeline/6.11.1.1):
  - The ohpcd registry publishes ecm up to 6.26.0 only; patch 0001 lowers
    ``find_package(ECM 6.28.0 NO_MODULE)`` to 6.26.0 and KF_DEP_VERSION to
    6.26.0 so the installed KF6QuickChartsConfig.cmake asks for ECM 6.26.0.
  - qtbase/qtdeclarative/qtshadertools use cmake_find_mode=none, so Qt6*_DIR
    cache variables are set explicitly and a conan_cmakedeps_paths.cmake is
    written to prepend qtbase's lib/cmake into CMAKE_PREFIX_PATH.
  - CMakeDeps-generated ECMConfig.cmake does NOT define ECM_MODULE_DIR /
    ECM_MODULE_PATH / ECM_GLOBAL_FIND_VERSION. Without ECM_GLOBAL_FIND_VERSION
    >= 5.240 the ECM QtVersionOption module defaults to Qt5 (KDEInstallDirs5 /
    ECMQmlModule5) and configure aborts with an add_library CMP0002 error.
    All three variables are set manually.
  - qt6_add_shaders runs the qsb host tool, an OHOS arm64 binary that loads
    Qt6Core from qtbase; the build runs with qtbase/qtshadertools libs on
    LD_LIBRARY_PATH (same trick as attica's _library_runtime_env).
  - qt_add_qml_module clears VERSION/SOVERSION on the backing library target,
    so the built .so has no ELF SONAME and plugins/tests record a relative
    DT_NEEDED ("../bin/libQuickCharts.so") that only resolves against the CWD.
    Patch 0001 forces ``-Wl,-soname`` and this recipe creates versioned .so
    symlinks in the build bin dir (for ctest) and in the package lib dir (for
    deployment), so the loader finds libQuickCharts.so.1 via LD_LIBRARY_PATH.
  - Upstream autotests (4 ecm_add_tests C++ tests + 3 QML tests driven by the
    local qmltest binary) run in build(); QML tests need QT_QPA_PLATFORM=offscreen
    QT_QUICK_BACKEND=software and QML2_IMPORT_PATH/QML_IMPORT_PATH pointing at
    the build bin dir plus the dependency qml dirs.
"""
import glob
import os
import re
import shlex
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class KQuickChartsConan(ConanFile):
    name = "kquickcharts"
    version = "6.28.0"
    description = (
        "KDE Frameworks 6 - Qt Quick Charts (QML module org.kde.quickcharts: "
        "BarChart, LineChart, PieChart)"
    )
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/kquickcharts"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        self.requires("qtdeclarative/6.11.1")
        self.requires("qtshadertools/6.11.1")

    def build_requirements(self):
        # ecm/6.26.0 is the highest ECM published on ohpcd; patch 0001 lowers
        # the upstream find_package(ECM 6.28.0) requirement to 6.26.0.
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self, generator="Unix Makefiles")
        qtbase_pkg = self.dependencies["qtbase"].package_folder
        qtdeclarative_pkg = self.dependencies["qtdeclarative"].package_folder
        qtshadertools_pkg = self.dependencies["qtshadertools"].package_folder
        ecm = self.dependencies.build.get("ecm")
        ecm_share = os.path.join(ecm.package_folder, "share", "ECM") if ecm else None

        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["BUILD_EXAMPLES"] = "OFF"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["QT_QMAKE_TARGET_MKSPEC"] = "harmonyos-clang"

        if ecm_share:
            tc.variables["ECM_GLOBAL_FIND_VERSION"] = "6.26.0"
            tc.variables["ECM_MODULE_DIR"] = os.path.join(ecm_share, "modules") + os.sep
            tc.variables["ECM_MODULE_PATH"] = ";".join(
                [
                    os.path.join(ecm_share, "modules"),
                    os.path.join(ecm_share, "find-modules"),
                    os.path.join(ecm_share, "kde-modules"),
                ]
            )

        # qtbase/qtdeclarative/qtshadertools ship their own Qt6*Config.cmake
        # (cmake_find_mode=none), so point CMake straight at them.
        tc.variables["Qt6_DIR"] = os.path.join(qtbase_pkg, "lib", "cmake", "Qt6")
        tc.variables["Qt6Qml_DIR"] = os.path.join(qtdeclarative_pkg, "lib", "cmake", "Qt6Qml")
        tc.variables["Qt6Quick_DIR"] = os.path.join(qtdeclarative_pkg, "lib", "cmake", "Qt6Quick")
        tc.variables["Qt6QuickControls2_DIR"] = os.path.join(
            qtdeclarative_pkg, "lib", "cmake", "Qt6QuickControls2"
        )
        tc.variables["Qt6QuickTest_DIR"] = os.path.join(
            qtdeclarative_pkg, "lib", "cmake", "Qt6QuickTest"
        )
        tc.variables["Qt6ShaderTools_DIR"] = os.path.join(
            qtshadertools_pkg, "lib", "cmake", "Qt6ShaderTools"
        )
        tc.variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = ";".join(
            [qtdeclarative_pkg, qtshadertools_pkg]
        )

        lines = [
            f'list(PREPEND CMAKE_PREFIX_PATH "{qtbase_pkg}/lib/cmake")',
            f'list(PREPEND CMAKE_LIBRARY_PATH "{qtbase_pkg}/lib")',
            f'list(PREPEND CMAKE_INCLUDE_PATH "{qtbase_pkg}/include")',
        ]
        if ecm_share:
            ecm_cmake = os.path.join(ecm_share, "cmake")
            lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')
        lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        lines.append("set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)")
        lines.append(f'set(CONAN_RUNTIME_LIB_DIRS "{qtbase_pkg}/lib")')
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        with self._runtime_env().vars(self).apply():
            cmake.build()
        # qt_add_qml_module drops VERSION/SOVERSION, so CMake installs no
        # versioned symlinks; create them so SONAME resolution works.
        self._create_versioned_symlinks(self._build_bin_dir())
        self._run_upstream_ctest()

    def _runtime_env(self):
        """LD_LIBRARY_PATH for host tools (qsb) and runtime deps."""
        env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
        env.prepend_path("LD_LIBRARY_PATH", self._build_bin_dir())
        return env

    def _build_bin_dir(self):
        for cand in (
            os.path.join(self.build_folder, "bin"),
            os.path.join(self.build_folder, "Release", "bin"),
            os.path.join(self.build_folder, "Debug", "bin"),
        ):
            if os.path.isdir(cand):
                return cand
        return os.path.join(self.build_folder, "bin")

    def _create_versioned_symlinks(self, libdir):
        if not os.path.isdir(libdir):
            return
        for base, soversion in (
            ("libQuickCharts", "1"),
            ("libQuickChartsControls", "1"),
        ):
            real = os.path.join(libdir, base + ".so")
            if not os.path.exists(real):
                continue
            for name in (base + ".so." + soversion, base + ".so.6.28.0"):
                dst = os.path.join(libdir, name)
                if os.path.islink(dst):
                    os.unlink(dst)
                if not os.path.exists(dst):
                    try:
                        os.symlink(base + ".so", dst)
                    except OSError:
                        # HMDFS soft-link limitations: fall back to a copy
                        import shutil
                        shutil.copy2(real, dst)

    def _run_upstream_ctest(self):
        if not can_run(self):
            self.output.warning(
                "kquickcharts upstream tests built but not run: target binaries "
                "cannot execute on this host"
            )
            return
        lib_path = os.pathsep.join(self._run_lib_dirs())
        qml_path = os.pathsep.join(self._run_qml_dirs())
        plugin_path = os.pathsep.join(self._run_plugin_dirs())
        test_home = os.path.join(self.build_folder, "test-home")
        xdg_runtime = os.path.join(self.build_folder, "xdg-runtime")
        os.makedirs(test_home, exist_ok=True)
        os.makedirs(xdg_runtime, exist_ok=True)
        os.chmod(xdg_runtime, 0o700)
        command = (
            "QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software "
            "LD_LIBRARY_PATH={ld} QT_PLUGIN_PATH={pp} "
            "QML2_IMPORT_PATH={qml} QML_IMPORT_PATH={qml} "
            "HOME={home} XDG_RUNTIME_DIR={xdg} "
            "XDG_CACHE_HOME={cache} XDG_CONFIG_HOME={config} XDG_DATA_HOME={data} "
            "CTEST_OUTPUT_ON_FAILURE=1 CTEST_PARALLEL_LEVEL=1 "
            "ctest --test-dir {build} --output-on-failure --no-tests=error"
        ).format(
            ld=shlex.quote(lib_path),
            pp=shlex.quote(plugin_path),
            qml=shlex.quote(qml_path),
            home=shlex.quote(test_home),
            xdg=shlex.quote(xdg_runtime),
            cache=shlex.quote(os.path.join(test_home, ".cache")),
            config=shlex.quote(os.path.join(test_home, ".config")),
            data=shlex.quote(os.path.join(test_home, ".local", "share")),
            build=shlex.quote(self.build_folder),
        )
        self.run(command)

    def _run_lib_dirs(self):
        dirs = []
        for dep in self.dependencies.values():
            package = dep.package_folder
            for libdir in dep.cpp_info.libdirs or ["lib"]:
                dirs.append(os.path.join(package, libdir))
            dirs.append(os.path.join(package, "lib"))
        dirs.append(self._build_bin_dir())
        return self._unique(dirs)

    def _run_qml_dirs(self):
        dirs = []
        for dep in self.dependencies.values():
            dirs.append(os.path.join(dep.package_folder, "qml"))
        dirs.append(self._build_bin_dir())
        dirs.append(os.path.join(self.build_folder, "qml"))
        return self._unique(dirs)

    def _run_plugin_dirs(self):
        dirs = []
        for dep in self.dependencies.values():
            dirs.append(os.path.join(dep.package_folder, "plugins"))
        dirs.append(self._build_bin_dir())
        return self._unique(dirs)

    @staticmethod
    def _unique(paths):
        seen = set()
        result = []
        for path in paths:
            if path not in seen:
                seen.add(path)
                result.append(path)
        return result

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Versioned symlinks for the SONAME (see class docstring).
        self._create_versioned_symlinks(os.path.join(self.package_folder, "lib"))
        self._strip_imported_no_soname()
        if str(self.settings.os) == "OHOS" and self.options.shared:
            self._sign_shared_libs()

    def _strip_imported_no_soname(self):
        """Expose the packaged libs as normal shared targets in generated
        CMake configs (the libs now carry a real ELF SONAME)."""
        for dirpath, _, filenames in os.walk(self.package_folder):
            for filename in filenames:
                if not filename.endswith(".cmake"):
                    continue
                path = os.path.join(dirpath, filename)
                try:
                    with open(path, encoding="utf-8", errors="ignore") as handle:
                        content = handle.read()
                except OSError:
                    continue
                updated = re.sub(
                    r'(IMPORTED_NO_SONAME(?:_[A-Za-z0-9]+)?)([ \t]*)"(TRUE|ON|YES|1)"',
                    lambda m: m.group(1) + m.group(2) + '"FALSE"',
                    content,
                    flags=re.IGNORECASE,
                )
                updated = re.sub(
                    r"(IMPORTED_NO_SONAME(?:_[A-Za-z0-9]+)?)([ \t]*)(TRUE|ON|YES|1)",
                    lambda m: m.group(1) + m.group(2) + "FALSE",
                    updated,
                    flags=re.IGNORECASE,
                )
                if updated != content:
                    with open(path, "w", encoding="utf-8") as handle:
                        handle.write(updated)

    def _sign_shared_libs(self):
        libdir = os.path.join(self.package_folder, "lib")
        shared_objects = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        shared_objects += glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not shared_objects:
            return
        objcopy = os.environ.get("HNP_LLVM_OBJCOPY", "/data/service/hnp/bin/llvm-objcopy")
        signer = os.environ.get("HNP_BINARY_SIGN_TOOL", "/data/service/hnp/bin/binary-sign-tool")
        for tool in (objcopy, signer):
            if not os.path.isfile(tool):
                raise ConanInvalidConfiguration(
                    "Required OHOS signing tool not found: {}".format(tool)
                )
        for shared_object in shared_objects:
            if os.path.islink(shared_object):
                continue
            self._remove_codesign_section(objcopy, shared_object)
            self.run(
                "{} sign -inFile {} -outFile {} -selfSign 1".format(
                    shlex.quote(signer),
                    shlex.quote(shared_object),
                    shlex.quote(shared_object),
                )
            )

    def _remove_codesign_section(self, objcopy, shared_object):
        probe = subprocess.run(
            [objcopy, "--dump-section", ".codesign=/dev/null", shared_object],
            text=True,
            capture_output=True,
            check=False,
        )
        if probe.returncode != 0:
            return
        self.run(
            "{} --remove-section .codesign {}".format(
                shlex.quote(objcopy),
                shlex.quote(shared_object),
            )
        )

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        # QML module org.kde.quickcharts (+ .controls) shipped in lib/qml.
        self.cpp_info.libs = ["QuickCharts", "QuickChartsControls"]
