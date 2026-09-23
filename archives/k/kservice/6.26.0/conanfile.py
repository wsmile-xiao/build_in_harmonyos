#!/usr/bin/env python3
"""Conan recipe for kservice 6.26.0 on HarmonyOS PC.

kservice is a KDE Frameworks 6 library for desktop service discovery and the
KSycoca service cache (libKF6Service.so and kbuildsycoca6).

OHOS-specific adaptations (carried forward from the 6.18.0 recipe, verified
against the 6.26.0 source):
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS not
    in KDE platform list)
  - KF_SKIP_PO_PROCESSING=ON: skip translation catalog generation for the
    initial KF baseline
  - BUILD_PYTHON_BINDINGS=OFF to avoid Shiboken/PySide requirements
  - CMAKE_DISABLE_FIND_PACKAGE_KF6DocTools=ON to keep optional docs out of
    the baseline package
  - BUILD_TESTING=ON and ctest execution for upstream autotests available in
    the current headless feature set
  - Dependencies: qtbase/6.11.1, kconfig/6.26.0, kcoreaddons/6.26.0,
    ki18n/6.26.0, ecm/6.26.0 (ECM)
  - ECM_MODULE_PATH set manually because CMakeDeps-generated ECMConfig.cmake
    does not propagate the variable the project's CMakeLists.txt relies on
  - conan_cmakedeps_paths.cmake created manually because qtbase uses
    cmake_find_mode=none, which prevents CMakeDeps from adding its lib/cmake
    builddir to CMAKE_PREFIX_PATH
  - ECM 6.26 KDEInstallDirs6 runs the qtbase qtpaths host tool during
    configure; the sandbox LD_LIBRARY_PATH contains an incompatible
    libc++_shared.so which shadows the compatible one, so /system/lib64 is
    prepended (kconfig 6.26.0 / bluez-qt 6.28.0 / kcrash 6.26.0 precedent)
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class KserviceConan(ConanFile):
    name = "kservice"
    version = "6.26.0"
    description = "KDE Frameworks 6 - desktop service discovery"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/kservice"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        self.requires("kconfig/6.26.0")
        self.requires("kcoreaddons/6.26.0")
        self.requires("ki18n/6.26.0")

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
        tc.variables["BUILD_PYTHON_BINDINGS"] = "OFF"
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_KF6DocTools"] = "ON"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"

        # ECM's own installed ECMConfig.cmake sets ECM_MODULE_PATH, but the
        # CMakeDeps-generated ECMConfig.cmake does not. Set it manually so
        # KDE cmake modules (KDEInstallDirs, KDECMakeSettings, etc.) are
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

        qtbase = self.dependencies.get("qtbase")
        if qtbase:
            qt_pkg = qtbase.package_folder
            # qtbase uses cmake_find_mode=none -> CMakeDeps does not generate
            # conan_cmakedeps_paths.cmake. Create it manually so the
            # toolchain adds qtbase's cmake dirs to CMAKE_PREFIX_PATH.
            lines = [
                f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")',
                f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")',
                f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")',
            ]
            if ecm:
                ecm_pkg = ecm.package_folder
                ecm_cmake = os.path.join(ecm_pkg, "share", "ECM", "cmake")
                lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')

            # Add every dependency's lib/cmake dir so find_package(KF6*)
            # and transitive find_dependency() chains all resolve.
            for dep_name in ("kconfig", "kcoreaddons", "ki18n"):
                dep = self.dependencies.get(dep_name)
                if dep and dep.package_folder:
                    lines.append(
                        f'list(PREPEND CMAKE_PREFIX_PATH '
                        f'"{dep.package_folder}/lib/cmake")'
                    )
                    lines.append(
                        f'list(PREPEND CMAKE_LIBRARY_PATH '
                        f'"{dep.package_folder}/lib")'
                    )
                    lines.append(
                        f'list(PREPEND CMAKE_INCLUDE_PATH '
                        f'"{dep.package_folder}/include")'
                    )

            lines.append(
                'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")'
            )
            lines.append(
                'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")'
            )
            lines.append("set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)")
            lines.append(f'set(CONAN_RUNTIME_LIB_DIRS "{qt_pkg}/lib")')
            paths_file = os.path.join(
                self.generators_folder, "conan_cmakedeps_paths.cmake"
            )
            with open(paths_file, "w") as f:
                f.write("\n".join(lines) + "\n")

        tc.generate()

    def build(self):
        # Platform guard: apply OHOS-specific patches only on OHOS so
        # non-OHOS platforms are not affected.
        if self.settings.os == "OHOS":
            apply_conandata_patches(self)
        cmake = CMake(self)
        with self._cmake_build_env().vars(self).apply():
            cmake.configure()
            cmake.build()
        self._run_upstream_tests()

    def _cmake_build_env(self):
        build_env = self._library_runtime_env()
        if self.settings.os == "OHOS":
            # E132: OHOS SDK lld depends on libxml2.so.16 shipped in the
            # SDK's llvm/lib directory; CI workers may not export it via
            # LD_LIBRARY_PATH. Prepend it so CMake's TryCompile can link.
            for llvm_lib in sorted(
                glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"
                )
            ):
                build_env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
            # ECM 6.26 KDEInstallDirs6 runs the qtbase qtpaths host tool
            # during configure (ecm_query_qt -> QT_INSTALL_PREFIX). The
            # sandbox LD_LIBRARY_PATH contains an incompatible
            # libc++_shared.so under /data/storage/el1/bundle/libs/arm64
            # which shadows the compatible one; prepend /system/lib64 (and
            # the qtbase lib dir, already added by _library_runtime_env) so
            # the loader resolves the compatible libc++ first (kconfig
            # 6.26.0 / bluez-qt 6.28.0 / kcrash 6.26.0 precedent).
            build_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return build_env

    def _library_runtime_env(self):
        runtime_env = Environment()
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
                runtime_env.prepend_path(
                    "QML2_IMPORT_PATH", os.path.join(dep.package_folder, "qml")
                )
        for rel in ("bin", "lib", os.path.join("src", "lib")):
            runtime_env.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.build_folder, rel)
            )
        return runtime_env

    def _run_upstream_tests(self):
        test_env = self._library_runtime_env()
        if self.settings.os == "OHOS":
            # The sandbox LD_LIBRARY_PATH contains an incompatible
            # libc++_shared.so (under /data/storage/el1/bundle/libs/arm64)
            # which shadows the compatible one; prepend /system/lib64 so
            # test executables resolve the compatible libc++ first (kconfig
            # 6.26.0 / kcrash 6.26.0 precedent, same fix as
            # _cmake_build_env).
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
        test_env.define("XDG_DATA_HOME", os.path.join(test_home, ".local", "share"))
        test_env.define("XDG_DATA_DIRS", self._prepare_test_mime_database())
        test_env.define("KSERVICE_OHOS_SKIP_UNSUPPORTED_FS_TESTS", "1")
        self._prepare_ctest_runtime_links()
        with test_env.vars(self).apply():
            self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error'.format(
                    self.build_folder
                )
            )

    def _prepare_test_mime_database(self):
        # A minimal test-only MIME database is generated under the build
        # folder and exposed through XDG_DATA_DIRS. It provides both
        # mime/packages/freedesktop.org.xml for QMimeDatabase and per-type
        # mime/<type>.xml entries for KBuildMimeTypeFactory, which is
        # required by upstream service-trader and MIME association autotests
        # on the current runner (6.18.0 recipe precedent).
        mime_root = os.path.join(self.build_folder, "test-mime", "share")
        mime_packages = os.path.join(mime_root, "mime", "packages")
        os.makedirs(mime_packages, exist_ok=True)
        mime_xml = os.path.join(mime_packages, "freedesktop.org.xml")
        with open(mime_xml, "w") as f:
            f.write(
                """<?xml version="1.0" encoding="UTF-8"?>
<mime-info xmlns="http://www.freedesktop.org/standards/shared-mime-info">
  <mime-type type="application/octet-stream">
    <comment>unknown binary data</comment>
    <glob pattern="*.bin"/>
  </mime-type>
  <mime-type type="application/x-executable">
    <sub-class-of type="application/octet-stream"/>
    <glob pattern="*.exe"/>
  </mime-type>
  <mime-type type="text/plain">
    <comment>plain text document</comment>
    <glob pattern="*.txt"/>
  </mime-type>
  <mime-type type="text/html">
    <sub-class-of type="text/plain"/>
    <glob pattern="*.html"/>
    <glob pattern="*.htm"/>
  </mime-type>
  <mime-type type="text/x-csrc">
    <sub-class-of type="text/plain"/>
    <alias type="text/c-src"/>
    <glob pattern="*.c"/>
  </mime-type>
  <mime-type type="text/x-java">
    <sub-class-of type="text/plain"/>
    <glob pattern="*.java"/>
  </mime-type>
  <mime-type type="text/x-python">
    <sub-class-of type="text/plain"/>
    <glob pattern="*.py"/>
  </mime-type>
  <mime-type type="text/javascript">
    <sub-class-of type="text/plain"/>
    <sub-class-of type="application/x-executable"/>
    <glob pattern="*.js"/>
  </mime-type>
  <mime-type type="application/ecmascript">
    <sub-class-of type="text/javascript"/>
  </mime-type>
  <mime-type type="image/jpeg">
    <glob pattern="*.jpg"/>
    <glob pattern="*.jpeg"/>
  </mime-type>
  <mime-type type="image/png">
    <glob pattern="*.png"/>
  </mime-type>
  <mime-type type="application/pdf">
    <alias type="application/x-pdf"/>
    <glob pattern="*.pdf"/>
  </mime-type>
  <mime-type type="application/msword">
    <alias type="application/vnd.ms-word"/>
    <glob pattern="*.doc"/>
  </mime-type>
  <mime-type type="application/zip">
    <sub-class-of type="application/octet-stream"/>
    <glob pattern="*.zip"/>
  </mime-type>
  <mime-type type="application/x-7z-compressed">
    <sub-class-of type="application/octet-stream"/>
    <glob pattern="*.7z"/>
  </mime-type>
  <mime-type type="application/vnd.oasis.opendocument.text">
    <sub-class-of type="application/zip"/>
    <glob pattern="*.odt"/>
  </mime-type>
  <mime-type type="application/x-kns">
    <sub-class-of type="application/zip"/>
    <glob pattern="*.kns"/>
  </mime-type>
  <mime-type type="application/x-shellscript">
    <sub-class-of type="text/plain"/>
    <sub-class-of type="application/x-executable"/>
    <glob pattern="*.sh"/>
  </mime-type>
  <mime-type type="application/x-desktop">
    <sub-class-of type="text/plain"/>
    <glob pattern="*.desktop"/>
  </mime-type>
  <mime-type type="application/x-theme">
    <sub-class-of type="application/x-desktop"/>
    <glob pattern="*.theme"/>
  </mime-type>
  <mime-type type="x-scheme-handler/mailto">
    <comment>mailto URL handler</comment>
  </mime-type>
  <mime-type type="x-scheme-handler/someprotocol">
    <comment>test URL handler</comment>
  </mime-type>
</mime-info>
"""
            )
        mime_types = [
            "application/octet-stream",
            "application/x-executable",
            "text/plain",
            "text/html",
            "text/x-csrc",
            "text/x-java",
            "text/x-python",
            "text/javascript",
            "application/ecmascript",
            "image/jpeg",
            "image/png",
            "application/pdf",
            "application/msword",
            "application/zip",
            "application/x-7z-compressed",
            "application/vnd.oasis.opendocument.text",
            "application/x-kns",
            "application/x-shellscript",
            "application/x-desktop",
            "application/x-theme",
            "x-scheme-handler/mailto",
            "x-scheme-handler/someprotocol",
        ]
        for mime_type in mime_types:
            mime_entry = os.path.join(
                mime_root, "mime", *mime_type.split("/")
            ) + ".xml"
            os.makedirs(os.path.dirname(mime_entry), exist_ok=True)
            with open(mime_entry, "w") as f:
                f.write(
                    '<?xml version="1.0" encoding="UTF-8"?>\n'
                    '<mime-info xmlns='
                    '"http://www.freedesktop.org/standards/shared-mime-info">\n'
                    f'  <mime-type type="{mime_type}"/>\n'
                    '</mime-info>\n'
                )
        return mime_root

    def _prepare_ctest_runtime_links(self):
        # Some upstream tests resolve the freshly built libraries via
        # $ORIGIN-relative loader paths next to the test executables; mirror
        # the built libs and dependency libs there (6.18.0 recipe precedent).
        compatibility_bin = os.path.normpath(
            os.path.join(self.build_folder, os.pardir, "bin")
        )
        os.makedirs(compatibility_bin, exist_ok=True)
        lib_sources = glob.glob(
            os.path.join(self.build_folder, "bin", "lib*.so*")
        )
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lib_sources.extend(
                    glob.glob(
                        os.path.join(dep.package_folder, "lib", "lib*.so*")
                    )
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
        cmake.install()

    def package_info(self):
        # The project installs its own KF6ServiceConfig.cmake with proper
        # dependency tracking. Use cmake_find_mode=none so CMakeDeps doesn't
        # shadow it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF6Service"]
