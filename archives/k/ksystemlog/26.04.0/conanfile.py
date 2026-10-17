#!/usr/bin/env python3
"""Conan recipe for ksystemlog 26.04.0 on HarmonyOS PC (aarch64).

ksystemlog is the KDE system log viewer: a Qt6/KF6 GUI application that
reads kernel/systemd-boot/auth/daemon/X.org/cron/... logs through KIO and
renders them in a KXmlGui main window. Upstream ships one executable:

  - ksystemlog    the GUI log viewer (QApplication main window)

OHOS-specific adaptations (patches/0001 + patches/0002):
  - Qt6 PrintSupport removed from the REQUIRED component list and from
    ksystemlog_lib: the published qtbase/6.11.1 builds qtbase with
    FEATURE_printsupport=OFF and ships no Qt6PrintSupport (algobox 1.1.1 /
    conducteo 5.0.2 precedent). The print-selection action is re-targeted
    to a QPdfWriter (QtGui) "Export Selection to PDF" flow so the log
    printing feature keeps working in PDF form (conducteo precedent);
    QPrintPreviewDialog (PrintSupport) is routed to the same export flow.
  - KF6 DocTools is optional upstream (find_package without REQUIRED) and
    is not part of the published KF6 6.14 closure; the DocBook handbook is
    not a runtime requirement (kfourinline 26.04.0 / audiocd precedent),
    so no kdoctools patch is needed - the KF6DocTools_FOUND branch simply
    stays disabled.
  - Journald and Audit modes stay optional and absent on OHOS: the custom
    cmake/FindJournald.cmake + cmake/FindAudit.cmake probes find neither
    systemd sd-journal nor libaudit on the platform, so HAVE_JOURNALD /
    HAVE_AUDIT stay undefined and modes/journald (the only QtConcurrent
    consumer) is not compiled.
  - Dependencies resolved from the ohpcd registry: qtbase 6.11.1 (Qt6
    Core/Concurrent/Gui/Widgets/Test - Concurrent and Test ARE built) and
    the KF6 6.14.0 framework closure (the version line for which every
    required framework is published: kio/6.14.0 + ktextwidgets/6.14.0 +
    kxmlgui/6.14.0 pin the whole 6.14.0 graph consistently).
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS
    is not in the KDE platform list).
  - KF_SKIP_PO_PROCESSING=ON to skip translation catalog generation (po/
    processing requires a gettext toolchain; catalogs are not needed for
    the smoke-verified deliverable; kfourinline 26.04.0 precedent).
  - conan_cmakedeps_paths.cmake written manually because qtbase (and the
    other KF6 packages) use cmake_find_mode=none, which prevents CMakeDeps
    from adding their lib/cmake dirs to CMAKE_PREFIX_PATH (kfourinline
    precedent).
  - Linker flags -Wl,-z,max-page-size=0x1000: default lld 0x10000
    max-page-size can split .dynsym/.dynstr into separate high-address RW
    LOAD segments which the OHOS musl loader refuses to mmap (audiocd /
    kfourinline precedent).

Upstream test suite (autotests/, 4 registered ctest entries) is exercised
on-device with BUILD_TESTING=ON; results are recorded in notes.md and
reports/test-report.md. The conan test_package performs a runtime smoke of
the installed binary (--version / --help headless-safe offscreen run).
"""
import glob
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class KsystemlogConan(ConanFile):
    name = "ksystemlog"
    version = "26.04.0"
    description = (
        "KDE system log viewer - a Qt6/KF6 GUI application that browses "
        "kernel, boot, auth, daemon, X.org, cron, acpid, apache, postfix, "
        "samba, cups and samba log files"
    )
    license = "GPL-2.0-or-later AND GFDL-1.2-only"
    homepage = "https://invent.kde.org/utilities/ksystemlog"
    url = "https://invent.kde.org/utilities/ksystemlog"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        # KF6 6.14.0 closure: the version line for which every framework
        # ksystemlog needs is published on ohpcd (kio/ktextwidgets/kxmlgui
        # only exist at 6.14.0 below 6.18, so 6.14.0 keeps the graph
        # consistent with no overrides).
        self.requires("kconfig/6.14.0")
        self.requires("kconfigwidgets/6.14.0")
        self.requires("kcoreaddons/6.14.0")
        self.requires("kcrash/6.14.0")
        self.requires("ki18n/6.14.0")
        self.requires("karchive/6.14.0")
        self.requires("kitemviews/6.14.0")
        self.requires("kwidgetsaddons/6.14.0")
        self.requires("kcompletion/6.14.0")
        self.requires("ktextwidgets/6.14.0")
        self.requires("kio/6.14.0")
        self.requires("kxmlgui/6.14.0")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        # po/ catalog processing needs the gettext msgfmt toolchain; skip it
        # (kfourinline 26.04.0 / khealthcertificate 26.04.3 precedent).
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        # OHOS loader workaround (audiocd/kfourinline precedent): default
        # lld 0x10000 max-page-size can split .dynsym/.dynstr into separate
        # high-address RW LOAD segments which the OHOS musl loader refuses
        # to mmap; pin the 4K page layout.
        if self.settings.os == "OHOS":
            tc.variables["CMAKE_EXE_LINKER_FLAGS_INIT"] = (
                "-Wl,-z,max-page-size=0x1000"
            )
            tc.variables["CMAKE_SHARED_LINKER_FLAGS_INIT"] = (
                "-Wl,-z,max-page-size=0x1000"
            )

        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join(
                os.path.join(ecm_share, rel)
                for rel in ("modules", "find-modules", "kde-modules")
            )

        self._write_cmake_paths(ecm)
        tc.generate()

    def _write_cmake_paths(self, ecm):
        # qtbase/KF6 packages use cmake_find_mode=none, so CMakeDeps doesn't
        # put their lib/cmake dirs on CMAKE_PREFIX_PATH. Write
        # conan_cmakedeps_paths.cmake manually (kfourinline precedent).
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        for dep in list(self.dependencies.values()) + list(
            self.dependencies.build.values()
        ):
            if dep and dep.package_folder:
                self._append_dependency_paths(lines, dep.package_folder)
        if ecm and ecm.package_folder:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            lines.extend(
                [
                    f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_share}/cmake")',
                    f'list(PREPEND CMAKE_MODULE_PATH "{ecm_share}/modules")',
                    f'list(PREPEND CMAKE_MODULE_PATH "{ecm_share}/find-modules")',
                    f'list(PREPEND CMAKE_MODULE_PATH "{ecm_share}/kde-modules")',
                ]
            )
        lines.extend(
            [
                'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
                'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")',
            ]
        )
        paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    @staticmethod
    def _append_dependency_paths(lines, package_folder):
        lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{package_folder}/lib/cmake")')
        lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{package_folder}")')
        lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{package_folder}/lib")')
        lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{package_folder}/include")')

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        with self._cmake_build_env().vars(self).apply():
            cmake.configure()
            cmake.build()

    def _cmake_build_env(self):
        # Host tools (moc/uic/rcc/kconfig_compiler) shipped by the conan
        # packages are OHOS binaries: they need the compatible
        # libc++_shared from /system/lib64 plus the dependency lib dirs on
        # LD_LIBRARY_PATH (kfourinline / kconfig 6.26.0 precedent).
        build_env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                build_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
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
            # The sandbox LD_LIBRARY_PATH contains an incompatible
            # libc++_shared.so under /data/storage/el1/bundle/libs/arm64
            # which shadows the compatible one; prepend /system/lib64 so
            # the loader resolves the compatible libc++ first (kconfig
            # 6.26.0 / bluez-qt 6.28.0 / kcrash 6.26.0 precedent).
            build_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return build_env

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # Application package: one executable in bin/, no library
        # deliverable (ksystemlog links Qt6/KF6 at runtime).
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_find_mode", "none")
        # Runtime env for consumers: the app needs the Qt6/KF6 libs.
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib")
        )
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                self.runenv_info.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
                self.runenv_info.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
                )
                self.runenv_info.prepend_path(
                    "QT_PLUGIN_PATH",
                    os.path.join(dep.package_folder, "lib", "plugins"),
                )
