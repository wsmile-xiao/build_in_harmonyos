#!/usr/bin/env python3
"""Conan recipe for knotifications 6.18.0.1 on HarmonyOS PC."""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, save


class KnotificationsConan(ConanFile):
    name = "knotifications"
    version = "6.18.0.1"
    description = "KDE Frameworks 6 - desktop notification library"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/knotifications"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        self.requires("kconfig/6.18.0")
        self.requires("kcoreaddons/6.18.0")
        self.requires("ki18n/6.18.0")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # Static archives must still be position independent: shared consumers
        # (e.g. kjobwidgets, whose own default is shared=True) link this archive
        # into their shared libraries. Without PIC the link fails with
        # "relocation R_AARCH64_ADD_ABS_LO12_NC ... recompile with -fPIC".
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = "ON"
        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            # Conan's HarmonyOS name has no complete CMake platform module. Use
            # CMake's OHOS platform rules so shared C++ targets receive SONAMEs.
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
            self._configure_ohos_shared_library_rules(tc)
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["BUILD_DESIGNERPLUGIN"] = "OFF"
        tc.variables["BUILD_PYTHON_BINDINGS"] = "OFF"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        tc.variables["USE_DBUS"] = "OFF"
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_Canberra"] = "ON"
        self._define_ecm(tc)
        self._write_cmake_paths()
        tc.generate()

    def _configure_ohos_shared_library_rules(self, toolchain):
        rules = os.path.join(self.generators_folder, "ohos-shared-library-rules.cmake")
        save(
            self,
            rules,
            "\n".join(
                (
                    'set(CMAKE_SHARED_LIBRARY_SONAME_C_FLAG "-Wl,-soname,")',
                    'set(CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG "-Wl,-soname,")',
                    'set(CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG "-Wl,-rpath,")',
                    'set(CMAKE_SHARED_LIBRARY_RUNTIME_CXX_FLAG "-Wl,-rpath,")',
                    'set(CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG_SEP ":")',
                    'set(CMAKE_SHARED_LIBRARY_RUNTIME_CXX_FLAG_SEP ":")',
                )
            )
            + "\n",
        )
        toolchain.cache_variables["CMAKE_USER_MAKE_RULES_OVERRIDE_C"] = rules
        toolchain.cache_variables["CMAKE_USER_MAKE_RULES_OVERRIDE_CXX"] = rules

    def _define_ecm(self, tc):
        ecm = self.dependencies.build.get("ecm")
        if not ecm:
            return
        ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
        tc.variables["ECM_MODULE_PATH"] = ";".join(
            os.path.join(ecm_share, rel)
            for rel in ("modules", "find-modules", "kde-modules")
        )

    def _write_cmake_paths(self):
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        for dep in list(self.dependencies.values()) + list(self.dependencies.build.values()):
            if dep and dep.package_folder:
                lines.extend(
                    [
                        f'list(PREPEND CMAKE_PREFIX_PATH "{dep.package_folder}/lib/cmake")',
                        f'list(PREPEND CMAKE_LIBRARY_PATH "{dep.package_folder}/lib")',
                        f'list(PREPEND CMAKE_INCLUDE_PATH "{dep.package_folder}/include")',
                    ]
                )
        ecm = self.dependencies.build.get("ecm")
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
        with open(os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake"), "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        CMake(self).install()
        self._sign_ohos_package_elfs()

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_ohos_package_elfs(self):
        """OHOS 只加载带有效 .codesign 段的 ELF：复制/重建都会让签名失效，
        因此打包后对所有 ELF 重新自签名（否则消费者运行时加载会报
        "Error loading shared library libKF6Notifications.so.6"）。"""
        if str(self.settings.os) not in ("OHOS", "HarmonyOS"):
            return
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            self.output.warning(
                "binary-sign-tool not found: skip OHOS package ELF signing"
            )
            return
        objcopy = shutil.which("llvm-objcopy")
        signed = 0
        for root, _, files in os.walk(self.package_folder):
            for name in files:
                path = os.path.join(root, name)
                if os.path.islink(path) or not self._is_elf(path):
                    continue
                if objcopy:
                    self.run(
                        f'"{objcopy}" --remove-section .codesign "{path}"',
                        ignore_errors=True,
                    )
                self.run(
                    f'"{signer}" sign -inFile "{path}" -outFile "{path}" -selfSign 1'
                )
                try:
                    os.chmod(path, 0o755)
                except OSError as exc:
                    self.output.warning(f"chmod signed ELF skipped for {path}: {exc}")
                signed += 1
        self.output.info(f"Signed {signed} OHOS package ELF file(s)")

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF6Notifications"]
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib")
        )
