#!/usr/bin/env python3
"""Conan recipe for qtkeychain 0.14.2 on HarmonyOS PC."""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class QtKeychainConan(ConanFile):
    name = "qtkeychain"
    version = "0.14.2"
    description = "Qt API for storing passwords and secrets"
    license = "BSD-3-Clause"
    homepage = "https://github.com/frankosterfeld/qtkeychain"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase-sql-dbus/6.11.1")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()

        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_WITH_QT6"] = "ON"
        tc.variables["BUILD_TEST_APPLICATION"] = "ON"
        tc.variables["BUILD_TRANSLATIONS"] = "OFF"
        tc.variables["LIBSECRET_SUPPORT"] = "OFF"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.variables["CMAKE_BUILD_RPATH"] = "$ORIGIN"
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = "-Wl,--disable-new-dtags"

        self._define_cmake_paths(tc)
        tc.generate()

    def _define_cmake_paths(self, tc):
        prefixes = []
        modules = []

        def add_unique(collection, value):
            normalized = value.replace("\\", "/")
            if normalized not in collection:
                collection.append(normalized)

        qtbase = self.dependencies["qtbase-sql-dbus"]
        add_unique(prefixes, qtbase.package_folder)
        add_unique(prefixes, os.path.join(qtbase.package_folder, "lib", "cmake"))
        add_unique(
            modules,
            os.path.join(qtbase.package_folder, "lib", "cmake", "Qt6", "platforms"),
        )

        ecm = self.dependencies.build.get("ecm")
        if ecm and ecm.package_folder:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            add_unique(prefixes, os.path.join(ecm_share, "cmake"))
            for rel in ("modules", "find-modules", "kde-modules"):
                add_unique(modules, os.path.join(ecm_share, rel))

        tc.variables["CMAKE_PREFIX_PATH"] = ";".join(prefixes)
        tc.variables["CMAKE_MODULE_PATH"] = ";".join(modules)

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        with self._library_runtime_env(include_build=True).vars(self).apply():
            cmake.configure()
            cmake.build()
            self._run_upstream_smoke()

    def _library_runtime_env(self, include_build=False):
        runtime_env = Environment()
        deps = list(self.dependencies.values())
        if include_build:
            deps += list(self.dependencies.build.values())
        for dep in deps:
            if dep and dep.package_folder:
                runtime_env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
                runtime_env.prepend_path("PATH", os.path.join(dep.package_folder, "bin"))
                runtime_env.prepend_path("QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins"))
                runtime_env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "lib", "plugins")
                )
        for rel in ("bin", "lib"):
            runtime_env.prepend_path("LD_LIBRARY_PATH", os.path.join(self.build_folder, rel))
        runtime_env.define("QT_QPA_PLATFORM", "offscreen")
        return runtime_env

    def _run_upstream_smoke(self):
        testclient = os.path.join(self.build_folder, "testclient")
        if not os.path.isfile(testclient):
            candidates = glob.glob(os.path.join(self.build_folder, "**", "testclient"), recursive=True)
            testclient = next((path for path in candidates if os.path.isfile(path)), "")
        if not testclient:
            raise ConanException("qtkeychain upstream testclient was not built")
        self.output.info("Built upstream qtkeychain testclient: {}".format(testclient))

    def package(self):
        cmake = CMake(self)
        with self._library_runtime_env(include_build=True).vars(self).apply():
            cmake.install()
        self._sign_ohos_elf_tree(self.package_folder, "package")

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
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        )
        for compiler in (compilers.get("c"), compilers.get("cpp")):
            if compiler:
                candidates.append(os.path.join(os.path.dirname(compiler), name))
        found = shutil.which(name)
        if found:
            candidates.append(found)
        candidates.append(os.path.join("/data/service/hnp/bin", name))
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return ""

    @staticmethod
    def _quote(value):
        return '"' + str(value).replace('"', '\\"') + '"'

    def _sign_ohos_elf_tree(self, root_folder, label):
        if str(self.settings.os) not in ("OHOS", "HarmonyOS"):
            return
        if not os.path.isdir(root_folder):
            return
        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            raise ConanException(
                "Cannot locate OHOS llvm-objcopy/binary-sign-tool for ELF signing"
            )

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
                try:
                    os.chmod(path, 0o755)
                except OSError as exc:
                    self.output.warning(f"chmod signed ELF skipped for {path}: {exc}")
                signed += 1
        self.output.info(f"Signed {signed} OHOS {label} ELF file(s)")

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["qt6keychain"]
        self.runenv_info.prepend_path("LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))
