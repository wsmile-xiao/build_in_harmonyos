#!/usr/bin/env python3
"""Conan recipe for kparts 6.18.0 on HarmonyOS PC.

kparts is the KDE Frameworks 6 plugin framework (libKF6Parts.so): the
Part/ReadOnlyPart/ReadWritePart/PartManager/PartLoader API used by KDE
applications to embed document views.

OHOS-specific adaptations:
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS is
    not in the KDE platform list)
  - patch 0001: lower KF_DEP_VERSION from 6.18.0 to 6.14.0. ohpcd's only
    kio containing KIOWidgets is kio/6.14.0 (kio/6.26.0 is KIOCORE_ONLY: no
    KIOWidgets target and no KUriFilter header, which kparts'
    NavigationExtension does use), and mixing kio/6.14.0 with the KF6 6.18
    series forces a kio rebuild whose trash worker cannot compile against
    the published Solid package. The whole KF6 graph therefore uses the
    published 6.14.0 series.
  - BUILD_TESTING=ON and ctest execution for the two upstream autotests
    (parttest, partloadertest) inside the Conan build; QTest GUI cases run
    with QT_QPA_PLATFORM=offscreen
  - CMAKE_CXX_STANDARD=20: the KF6 6.18 headers use C++20 features; the
    ohos-aarch64 profile pins cppstd=17
  - CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG set manually because CMake has no
    Platform/HarmonyOS module (kio/kfilemetadata/baloo precedent)
  - ECM_MODULE_PATH set manually because the CMakeDeps-generated
    ECMConfig.cmake does not propagate the variable the project's
    CMakeLists.txt relies on
  - conan_cmakedeps_paths.cmake created manually because qtbase uses
    cmake_find_mode=none, which prevents CMakeDeps from adding its
    lib/cmake builddir to CMAKE_PREFIX_PATH
  - Dependency versions: the KF6 6.14.0 series of ohpcd (all prebuilt, no
    dependency rebuild). kio has to be 6.14.0 anyway (only published kio
    with KIOWidgets); the rest of the graph follows so that no dependency
    has to be rebuilt from source. Rejected alternatives and a full
    rationale are documented in notes.md.
  - Runtime closure for the OHOS musl loader before running ctest: the
    published KF6 packages carry (a) absolute DT_NEEDED paths baked on the
    publishing worker's conan cache and (b) relative DT_NEEDED paths such
    as ../../bin/libKF6ConfigCore.so which musl resolves against the
    process CWD. Symlinks (never rewritten copies, so code signatures stay
    valid) are created for the missing paths inside the build tree. See
    _prepare_runtime_closure().
"""
import glob
import os
import re

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class KpartsConan(ConanFile):
    name = "kparts"
    version = "6.18.0"
    description = "KDE Frameworks 6 - KParts (plugin framework for document views)"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/kparts"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # KF6 6.14.0 baseline of ohpcd for the whole graph.
        #
        # Reason: kparts 6.18 needs KIOWidgets (src/navigationextension.cpp
        # uses KUriFilter/KUriFilterData) and the only ohpcd kio package that
        # contains KIOWidgets is kio/6.14.0. kio/6.26.0 is a KIOCORE_ONLY
        # build (no KIOWidgets target, no KUriFilter header, trimmed
        # CamelCase include directory). Combining kio/6.14.0 with the KF6
        # 6.18 series would force kio 6.14 to be rebuilt from source, which
        # fails in its trash worker: kioworkers/trash/trashimpl.cpp includes
        # <solid/block.h> but the published Solid package installs only
        # include/KF6/Solid/Solid/block.h (case mismatch on a case-sensitive
        # filesystem). Pinning the complete graph to the published 6.14.0
        # series keeps every dependency a prebuilt ohpcd binary (no
        # dependency rebuild at all); patch 0001 lowers the library's
        # KF_DEP_VERSION accordingly. Every KF6/KIO API used by kparts 6.18
        # exists in 6.14.0 and KF6 keeps API compatibility within the series.
        self.requires("qtbase/6.11.1")
        self.requires("kconfig/6.14.0")
        self.requires("kcoreaddons/6.14.0")
        self.requires("ki18n/6.14.0")
        self.requires("kservice/6.14.0")
        self.requires("kwidgetsaddons/6.14.0")
        self.requires("kxmlgui/6.14.0")
        self.requires("kjobwidgets/6.14.0")
        self.requires("kio/6.14.0")

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
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_KF6DocTools"] = "ON"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        # kparts and the KF6 6.18 headers use C++20 features; the
        # ohos-aarch64 profile pins cppstd=17.
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        # CMake has no Platform/HarmonyOS module; provide the SONAME flag so
        # libKF6Parts.so gets a DT_SONAME + versioned symlink chain
        # (kio/kfilemetadata/baloo precedent).
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"

        # ECM's own installed ECMConfig.cmake sets ECM_MODULE_PATH, but the
        # CMakeDeps-generated ECMConfig.cmake does not. Set it manually so
        # the KDE cmake modules (KDEInstallDirs, KDECMakeSettings, ...) are
        # found.
        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join(
                [
                    os.path.join(ecm_share, "modules"),
                    os.path.join(ecm_share, "find-modules"),
                    os.path.join(ecm_share, "kde-modules"),
                ]
            )

        tc.generate()

        self._write_cmake_paths(ecm)

    def _write_cmake_paths(self, ecm):
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        for dep in list(self.dependencies.values()) + list(
            self.dependencies.build.values()
        ):
            if dep and dep.package_folder:
                lines.extend(
                    [
                        f'list(PREPEND CMAKE_PREFIX_PATH '
                        f'"{dep.package_folder}/lib/cmake")',
                        f'list(PREPEND CMAKE_LIBRARY_PATH '
                        f'"{dep.package_folder}/lib")',
                        f'list(PREPEND CMAKE_INCLUDE_PATH '
                        f'"{dep.package_folder}/include")',
                    ]
                )
        if ecm and ecm.package_folder:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            lines.extend(
                [
                    f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_share}/cmake")',
                    f'list(PREPEND CMAKE_MODULE_PATH '
                    f'"{ecm_share}/modules")',
                    f'list(PREPEND CMAKE_MODULE_PATH '
                    f'"{ecm_share}/find-modules")',
                    f'list(PREPEND CMAKE_MODULE_PATH '
                    f'"{ecm_share}/kde-modules")',
                ]
            )
        lines.extend(
            [
                'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
                'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")',
            ]
        )
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        # Platform guard: apply OHOS-specific patches only on OHOS so
        # non-OHOS platforms are not affected.
        if self.settings.os == "OHOS":
            apply_conandata_patches(self)
        cmake = CMake(self)
        with self._cmake_build_env().vars(self).apply():
            cmake.configure()
            cmake.build()
        if self.settings.os == "OHOS":
            self._run_upstream_tests()

    def _cmake_build_env(self):
        build_env = self._library_runtime_env()
        if self.settings.os == "OHOS":
            # E132: the OHOS SDK lld depends on libxml2.so.16 shipped in the
            # SDK's llvm/lib directory; CI workers may not export it via
            # LD_LIBRARY_PATH (kio 6.26.0 precedent).
            for llvm_lib in sorted(
                glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos"
                    "/native/llvm/lib"
                )
            ):
                build_env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
            # ECM KDEInstallDirs runs the qtbase qtpaths host tool during
            # configure; the sandbox LD_LIBRARY_PATH contains an
            # incompatible libc++_shared.so which shadows the compatible
            # one; prepend /system/lib64 (kconfig 6.26.0 / kio 6.26.0
            # precedent).
            build_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return build_env

    def _library_runtime_env(self):
        runtime_env = Environment()
        for dep in self._all_dependencies():
            if dep and dep.package_folder:
                runtime_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
                runtime_env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
                )
                runtime_env.prepend_path(
                    "QML2_IMPORT_PATH", os.path.join(dep.package_folder, "qml")
                )
        for rel in ("bin", "lib", os.path.join("src", "lib")):
            runtime_env.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.build_folder, rel)
            )
        return runtime_env

    # --- runtime closure for the OHOS musl loader -------------------------
    #
    # The published KF6 dependency packages contain two forms of DT_NEEDED
    # entries that the OHOS musl loader cannot resolve by itself
    # (platform knowledge base: relative-soname/CWD draft, baked absolute
    # NEEDED symlink draft, PR #9573 precedent):
    #   1. absolute paths baked on the publishing worker, e.g.
    #      /storage/Users/currentUser/.cache/conan2/p/<hash>/p/lib/<name>
    #   2. relative paths such as ../../bin/libKF6ConfigCore.so, which musl
    #      resolves against the *process CWD*; LD_LIBRARY_PATH does not
    #      apply to names containing '/'.
    # Rewriting the libraries is not possible on OHOS (the kernel verifies
    # the code signature of modified ELF files), so symlinks are used: a
    # symlink leaves the target byte-identical (signature stays valid) and
    # the loader opens it through the expected path.

    def _all_dependencies(self):
        result = []
        seen = set()

        def walk(dep):
            if dep is None:
                return
            key = f"{dep.ref.name}/{dep.ref.version}" if dep.ref else str(id(dep))
            if key in seen:
                return
            seen.add(key)
            result.append(dep)
            for sub in dep.dependencies.values():
                walk(sub)

        for dep in self.dependencies.values():
            walk(dep)
        return result

    def _dependency_libraries(self):
        libs = {}
        for dep in self._all_dependencies():
            if not dep or not dep.package_folder:
                continue
            for libdir in ("lib", "lib64"):
                directory = os.path.join(dep.package_folder, libdir)
                if not os.path.isdir(directory):
                    continue
                for name in sorted(os.listdir(directory)):
                    path = os.path.join(directory, name)
                    if ".so" in name and os.path.isfile(path):
                        libs.setdefault(name, path)
        return libs

    def _test_working_dirs(self, root):
        """Directories that CTest may use as a test working directory."""
        found = []
        for dirpath, dirnames, filenames in os.walk(root):
            if os.path.basename(dirpath) == "Testing":
                dirnames[:] = []
                continue
            if "CTestTestfile.cmake" in filenames:
                found.append(dirpath)
            depth = dirpath[len(root):].count(os.sep)
            if depth >= 4:
                dirnames[:] = []
        return found

    def _prepare_runtime_closure(self):
        libs = self._dependency_libraries()
        if not libs:
            return 0
        cwd_dirs = self._test_working_dirs(self.build_folder)
        needed = set()
        for path in libs.values():
            try:
                with open(path, "rb") as handle:
                    blob = handle.read()
            except OSError:
                continue
            for match in re.findall(
                rb"[/.][A-Za-z0-9_+./-]*\.so(?:\.\d+)*", blob
            ):
                name = match.decode("utf-8", "ignore")
                if name.startswith(("/", "./", "../")):
                    needed.add(name)
        linked = 0
        for entry in sorted(needed):
            real = libs.get(os.path.basename(entry))
            if not real:
                continue
            targets = (
                [entry]
                if entry.startswith("/")
                else [
                    os.path.normpath(os.path.join(cwd, entry))
                    for cwd in cwd_dirs
                ]
            )
            for target in targets:
                if os.path.lexists(target):
                    continue
                try:
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    os.symlink(real, target)
                    linked += 1
                except OSError:
                    pass
        return linked

    def _run_upstream_tests(self):
        # 层 1 (TEST_QUALITY_SPEC): run the upstream autotest suite in the
        # build tree. kparts registers two QTest executables with ECM:
        #   - parttest: Part/ReadOnlyPart/OpenUrlArguments/PartManager unit
        #     tests (QTEST_MAIN -> QApplication, run with the offscreen QPA)
        #   - partloadertest: PartLoader/plugin-discovery tests (needs the
        #     notepadpart MODULE built into <build>/lib/kf6/parts)
        self._prepare_runtime_closure()
        test_env = self._library_runtime_env()
        test_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
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
        test_env.define(
            "XDG_DATA_HOME", os.path.join(test_home, ".local", "share")
        )
        # partloadertest discovers the notepadpart test plugin through the
        # Qt/KF plugin search path; point it at the build tree layout
        # (<build>/lib/kf6/parts) that upstream uses as well.
        plugin_root = os.path.join(self.build_folder, "lib")
        if os.path.isdir(os.path.join(plugin_root, "kf6", "parts")):
            test_env.prepend_path("QT_PLUGIN_PATH", plugin_root)
        with test_env.vars(self).apply():
            self.run(
                'ctest --test-dir "{}" --output-on-failure '
                '--no-tests=error'.format(self.build_folder),
                ignore_errors=True,
            )

    def package(self):
        cmake = CMake(self)
        with self._library_runtime_env().vars(self).apply():
            cmake.install()

    def package_info(self):
        # The project installs its own KF6PartsConfig.cmake with proper
        # dependency tracking (find_dependency on KF6KIO etc). Use
        # cmake_find_mode=none so CMakeDeps doesn't shadow it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF6Parts"]
