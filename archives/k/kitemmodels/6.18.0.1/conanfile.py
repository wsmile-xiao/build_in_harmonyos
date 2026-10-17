#!/usr/bin/env python3
"""Conan recipe for kitemmodels 6.18.0.1 on HarmonyOS PC.

kitemmodels is a KDE Frameworks 6 library providing Qt item-model helpers
(libKF6ItemModels.so) and, when Qt6Qml is available, the QML module
org.kde.kitemmodels.

Adaptation history:
  - 6.18.0   : core library only. Qt6Qml was optional and not required, so the
               QML plugin was skipped in the minimal Akonadi KF baseline.
  - 6.18.0.1 : enables the QML module. Adds qtdeclarative/6.11.1 (Qt6Qml) as a
               hard requirement so upstream src/qml is configured, built and
               installed (lib/qml/org/kde/kitemmodels/{qmldir,*.so}). Required
               by kirigami-gallery, whose MainPage.qml does
               `import org.kde.kitemmodels`.

OHOS-specific adaptations:
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS is not
    in the KDE platform allow-list)
  - BUILD_TESTING=ON and ctest execution for the upstream autotests
  - ECM_MODULE_PATH set manually because the CMakeDeps-generated ECMConfig.cmake
    does not propagate the variable the project's CMakeLists.txt relies on
  - qtbase and qtdeclarative both ship complete, relocatable Qt6*Config.cmake
    files and set cmake_find_mode=none, so CMakeDeps generates nothing for them.
    Their lib/cmake dirs are therefore PREPENDed to CMAKE_PREFIX_PATH through a
    hand-written conan_cmakedeps_paths.cmake.
  - The Qt host tools (moc, rcc, qmltyperegistrar, qmlcachegen) live in the
    split qtbase/qtdeclarative packages; qmltyperegistrar/qmlcachegen have a
    RUNPATH of only $ORIGIN/../lib (qtdeclarative) and still NEEDED
    libQt6Core.so.6 (qtbase). The dependency lib dirs are therefore prepended to
    LD_LIBRARY_PATH while running configure/build/install, otherwise the tools
    fail to relocate their symbols (kdeclarative 6.26.0 precedent).
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    get,
    apply_conandata_patches,
    export_conandata_patches,
    save,
)
from conan.tools.env import Environment


class KitemmodelsConan(ConanFile):
    name = "kitemmodels"
    version = "6.18.0.1"
    description = "KDE Frameworks 6 - KDE ItemModels (core library + QML module org.kde.kitemmodels)"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/kitemmodels"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Qt6Core (+ Qt6Test/Qt6Widgets used by the upstream autotests)
        self.requires("qtbase/6.11.1")
        # Qt6Qml/Qt6Quick: required to build the QML module org.kde.kitemmodels.
        self.requires("qtdeclarative/6.11.1")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"

        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join([
                os.path.join(ecm_share, "modules"),
                os.path.join(ecm_share, "find-modules"),
                os.path.join(ecm_share, "kde-modules"),
            ])

        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            self._configure_ohos_shared_library_rules(tc)

        qt_prefixes = []
        for name in ("qtbase", "qtdeclarative"):
            dep = self.dependencies.get(name)
            if dep and dep.package_folder:
                qt_prefixes.append(dep.package_folder)
        if qt_prefixes:
            tc.variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = ";".join(qt_prefixes)

        if qt_prefixes:
            lines = []
            lines.append("set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)")
            for pkg in qt_prefixes:
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{pkg}/lib/cmake")')
                lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{pkg}/lib")')
                lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{pkg}/include")')
            if ecm:
                ecm_cmake = os.path.join(ecm.package_folder, "share", "ECM", "cmake")
                lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')
            lines.append(
                f'list(PREPEND CMAKE_MODULE_PATH '
                f'"${{CMAKE_CURRENT_LIST_DIR}}")'
            )
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH '
                f'"${{CMAKE_CURRENT_LIST_DIR}}")'
            )
            runtime_lib_dirs = ";".join(f"{p}/lib" for p in qt_prefixes)
            lines.append(f'set(CONAN_RUNTIME_LIB_DIRS "{runtime_lib_dirs}")')
            paths_file = os.path.join(
                self.generators_folder, "conan_cmakedeps_paths.cmake"
            )
            with open(paths_file, "w") as f:
                f.write("\n".join(lines) + "\n")

        tc.generate()

    def _configure_ohos_shared_library_rules(self, toolchain):
        """OHOS CMake does not emit a SONAME for shared libraries by default.
        Without a SONAME the QML plugin records a build-tree relative path
        (../../bin/libKF6ItemModels.so) in DT_NEEDED, which the OHOS loader
        treats as a cwd-relative path and fails to resolve. Restore the soname
        flags (kirigami 6.18.0 precedent)."""
        rules = os.path.join(self.generators_folder, "ohos-shared-library-rules.cmake")
        save(
            self,
            rules,
            "\n".join((
                'set(CMAKE_SHARED_LIBRARY_SONAME_C_FLAG "-Wl,-soname,")',
                'set(CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG "-Wl,-soname,")',
                'set(CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG "-Wl,-rpath,")',
                'set(CMAKE_SHARED_LIBRARY_RUNTIME_CXX_FLAG "-Wl,-rpath,")',
                'set(CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG_SEP ":")',
                'set(CMAKE_SHARED_LIBRARY_RUNTIME_CXX_FLAG_SEP ":")',
            )) + "\n",
        )
        toolchain.cache_variables["CMAKE_USER_MAKE_RULES_OVERRIDE_C"] = rules
        toolchain.cache_variables["CMAKE_USER_MAKE_RULES_OVERRIDE_CXX"] = rules

    def _dependency_runtime_env(self, include_build=False):
        """Runtime env for the split Qt packages: the Qt host tools and the
        freshly built QML plugin need every dependency lib dir on
        LD_LIBRARY_PATH (kdeclarative 6.26.0 precedent)."""
        env = Environment()
        deps = list(self.dependencies.values())
        if include_build:
            deps += list(self.dependencies.build.values())
        for dep in deps:
            if dep and dep.package_folder:
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
                env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "bin"))
                env.prepend_path("PATH", os.path.join(dep.package_folder, "bin"))
                env.prepend_path("PATH", os.path.join(dep.package_folder, "libexec"))
                env.prepend_path("QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins"))
                env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "lib", "plugins")
                )
                for rel in ("qml", "lib/qml", "share/qml"):
                    env.prepend_path("QML2_IMPORT_PATH", os.path.join(dep.package_folder, rel))
                    env.prepend_path("QML_IMPORT_PATH", os.path.join(dep.package_folder, rel))
        return env

    def build(self):
        if self.settings.os == "OHOS":
            apply_conandata_patches(self)
        cmake = CMake(self)
        with self._dependency_runtime_env(include_build=True).vars(self).apply():
            cmake.configure()
            cmake.build()
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        test_env = self._dependency_runtime_env(include_build=False)
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
        # The freshly built QML module (org.kde.kitemmodels) is only in the
        # build tree here; its import root has to be discoverable by the
        # upstream QtQml autotests.
        for rel in ("bin", "lib", "src/qml", "lib/qml", "qml"):
            candidate = os.path.join(self.build_folder, rel)
            if os.path.isdir(candidate):
                test_env.prepend_path("QML2_IMPORT_PATH", candidate)
                test_env.prepend_path("QML_IMPORT_PATH", candidate)
        for rel in ("bin", "lib", os.path.join("src", "lib"), os.path.join("src", "core")):
            test_env.prepend_path("LD_LIBRARY_PATH", os.path.join(self.build_folder, rel))
        with test_env.vars(self).apply():
            self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error'.format(
                    self.build_folder
                )
            )

    def package(self):
        cmake = CMake(self)
        with self._dependency_runtime_env(include_build=True).vars(self).apply():
            cmake.install()
        self._sign_ohos_elf_tree(self.package_folder)

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
        """CMake rewrites the RUNPATH of installed shared libraries, which
        invalidates the OHOS build-time .codesign section. The OHOS loader
        then refuses to load the library ("Permission denied"). Re-sign every
        packaged ELF (kirigami 6.18.0 / kdeclarative 6.26.0 precedent)."""
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
                self.run(
                    f"{self._quote(objcopy)} --remove-section .codesign {self._quote(path)}",
                    ignore_errors=True,
                )
                self.run(
                    f"{self._quote(signer)} sign -inFile {self._quote(path)} "
                    f"-outFile {self._quote(path)} -selfSign 1"
                )
                signed += 1
        self.output.info(f"Signed {signed} OHOS package ELF file(s)")

    def package_info(self):
        # The project installs its own KF6ItemModelsConfig.cmake with proper
        # dependency tracking. Use cmake_find_mode=none so CMakeDeps doesn't
        # shadow it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF6ItemModels"]
        # QML module org.kde.kitemmodels: consumers need the import root on
        # their QML import path (kirigami-gallery / akonadi consumers).
        self.runenv_info.prepend_path(
            "QML2_IMPORT_PATH", os.path.join(self.package_folder, "lib", "qml")
        )
        self.runenv_info.prepend_path(
            "QML_IMPORT_PATH", os.path.join(self.package_folder, "lib", "qml")
        )
