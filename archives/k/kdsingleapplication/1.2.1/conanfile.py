#!/usr/bin/env python3
"""Conan recipe for KDSingleApplication 1.2.1 on HarmonyOS PC."""

import os
import platform
import shutil
import shlex
import socket
import stat
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    save,
)


class KDSingleApplicationConan(ConanFile):
    name = "kdsingleapplication"
    version = "1.2.1"
    description = "Qt helper for single-instance applications and local IPC"
    license = "MIT"
    homepage = "https://github.com/KDAB/KDSingleApplication"
    url = "https://github.com/KDAB/KDSingleApplication"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1.2")

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.get_safe("shared"):
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        qt_cmake = os.path.join(
            self.dependencies["qtbase"].package_folder, "lib", "cmake"
        )
        tc.cache_variables["QT_DIR"] = os.path.join(qt_cmake, "Qt6")
        tc.cache_variables["Qt6_DIR"] = os.path.join(qt_cmake, "Qt6")
        tc.cache_variables["Qt6Core_DIR"] = os.path.join(qt_cmake, "Qt6Core")
        tc.cache_variables["Qt6CoreTools_DIR"] = os.path.join(
            qt_cmake, "Qt6CoreTools"
        )
        tc.cache_variables["Qt6Network_DIR"] = os.path.join(
            qt_cmake, "Qt6Network"
        )
        tc.cache_variables["Qt6Widgets_DIR"] = os.path.join(
            qt_cmake, "Qt6Widgets"
        )
        tc.cache_variables["Qt6Test_DIR"] = os.path.join(qt_cmake, "Qt6Test")
        tc.cache_variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "ON"
        tc.cache_variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = (
            "-Wl,-soname,"
        )
        tc.cache_variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = (
            "-Wl,-soname,"
        )
        tc.variables["KDSingleApplication_QT6"] = "ON"
        tc.variables["KDSingleApplication_STATIC"] = (
            "OFF" if self.options.shared else "ON"
        )
        tc.variables["KDSingleApplication_TESTS"] = "ON"
        tc.variables["KDSingleApplication_EXAMPLES"] = "OFF"
        tc.variables["KDSingleApplication_DOCS"] = "OFF"
        tc.variables["KDSingleApplication_INSTALL_QMAKE_PRI"] = "OFF"
        self._configure_cross_emulator(tc)
        tc.generate()

    def _configure_cross_emulator(self, toolchain):
        if platform.system() == "HarmonyOS":
            return
        runner = self.conf.get(
            "user.libminini:qemu_runner", default=None, check_type=str
        )
        if not runner:
            host_moc = self._find_host_moc()
            if host_moc:
                toolchain.variables["KDSingleApplication_MOC_EXECUTABLE"] = (
                    host_moc
                )
            return
        arguments = shlex.split(runner)
        qt_libdir = os.path.join(
            self.dependencies["qtbase"].package_folder, "lib"
        )
        for index, argument in enumerate(arguments):
            if argument.startswith("LD_LIBRARY_PATH="):
                arguments[index] = f"{argument}:{qt_libdir}"
                break
        else:
            arguments.extend(["-E", f"LD_LIBRARY_PATH={qt_libdir}"])
        toolchain.cache_variables["CMAKE_CROSSCOMPILING_EMULATOR"] = ";".join(
            arguments
        )
        moc = os.path.join(
            self.dependencies["qtbase"].package_folder, "libexec", "moc"
        )
        wrapper = os.path.join(self.generators_folder, "ohos-moc-wrapper.sh")
        command = shlex.join(arguments + [moc])
        save(self, wrapper, f'#!/bin/sh\nexec {command} "$@"\n')
        os.chmod(wrapper, 0o755)
        toolchain.variables["KDSingleApplication_MOC_EXECUTABLE"] = wrapper

    @staticmethod
    def _find_host_moc():
        candidates = []
        qt_host_path = os.environ.get("QT_HOST_PATH")
        if qt_host_path:
            candidates.append(os.path.join(qt_host_path, "libexec", "moc"))
        for name in ("moc-qt6", "moc6", "moc"):
            resolved = shutil.which(name)
            if resolved:
                candidates.append(resolved)
        candidates.extend(
            [
                "/usr/lib/qt6/libexec/moc",
                "/usr/lib/x86_64-linux-gnu/qt6/libexec/moc",
            ]
        )
        return next(
            (
                candidate
                for candidate in candidates
                if os.path.isfile(candidate) and os.access(candidate, os.X_OK)
            ),
            None,
        )

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        with self._runtime_env(include_build_tree=False).vars(self).apply():
            cmake.configure()
            cmake.build(build_tool_args=["-j1"])
        if self._can_run_upstream_tests():
            test_env = self._runtime_env(include_build_tree=True)
            test_env.define("TMPDIR", self._socket_capable_temp_dir())
            with test_env.vars(self).apply():
                self.run(
                    'ctest --test-dir "{}" --output-on-failure '
                    "--no-tests=error -j1".format(self.build_folder)
                )

    def _can_run_upstream_tests(self):
        if not can_run(self):
            return False
        if str(self.settings.os) == "OHOS" and platform.system() != "HarmonyOS":
            self.output.info(
                "Skipping execution on a non-HarmonyOS cross-build host"
            )
            return False
        return True

    def package(self):
        CMake(self).install()
        if str(self.settings.os) == "OHOS" and platform.system() == "HarmonyOS":
            self._sign_installed_elfs()

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [
            os.path.join("lib", "cmake"),
            os.path.join("lib", "cmake", "KDSingleApplication-qt6"),
        ]
        self.cpp_info.includedirs = [
            os.path.join("include", "kdsingleapplication-qt6")
        ]
        self.cpp_info.libs = ["kdsingleapplication-qt6"]
        self.cpp_info.requires = ["qtbase::core"]
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib")
        )

    def _runtime_env(self, include_build_tree):
        env = Environment()
        for dependency in self.dependencies.values():
            if dependency.package_folder:
                libdir = os.path.join(dependency.package_folder, "lib")
                if os.path.isdir(libdir):
                    env.prepend_path("LD_LIBRARY_PATH", libdir)
        if include_build_tree:
            env.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.build_folder, "lib")
            )
        env.define("QT_QPA_PLATFORM", "offscreen")
        env.define("QT_LOGGING_RULES", "qt.qpa.*=false")
        return env

    def _socket_capable_temp_dir(self):
        candidates = [
            os.environ.get("TMPDIR"),
            os.environ.get("XDG_RUNTIME_DIR"),
            "/data/storage/el2/base/cache",
        ]
        checked = set()
        for candidate in candidates:
            if not candidate or candidate in checked:
                continue
            checked.add(candidate)
            if self._supports_unix_socket(candidate):
                return candidate
        raise ConanInvalidConfiguration(
            "No writable temporary directory with Unix-domain socket support"
        )

    @staticmethod
    def _supports_unix_socket(directory):
        if not os.path.isdir(directory) or not os.access(directory, os.W_OK):
            return False
        probe_path = os.path.join(directory, "kdsa-conan-socket-probe")
        if len(probe_path.encode()) >= 100:
            return False
        probe = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            if os.path.lexists(probe_path):
                os.unlink(probe_path)
            probe.bind(probe_path)
            return True
        except OSError:
            return False
        finally:
            probe.close()
            if os.path.lexists(probe_path):
                os.unlink(probe_path)

    def _sign_installed_elfs(self):
        binaries = []
        for root, _, filenames in os.walk(self.package_folder):
            for filename in filenames:
                candidate = os.path.join(root, filename)
                if not os.path.islink(candidate) and self._elf_type(candidate) in (2, 3):
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
                if self._elf_type(signed) not in (2, 3):
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
        output = self._run_tool([objdump, "-h", path], f"inspect {path}")
        return any(".codesign" in line.split() for line in output.splitlines())

    @staticmethod
    def _run_tool(command, action):
        try:
            result = subprocess.run(
                command, capture_output=True, text=True, timeout=60
            )
        except (OSError, subprocess.SubprocessError) as error:
            raise ConanInvalidConfiguration(
                f"Unable to {action}: {error}"
            ) from error
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip()
            raise ConanInvalidConfiguration(
                f"Unable to {action}: {detail or 'tool exited unsuccessfully'}"
            )
        return result.stdout

    @staticmethod
    def _resolve_tool(environment_variable, executable):
        candidate = os.environ.get(environment_variable) or executable
        resolved = shutil.which(candidate)
        if not resolved and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            resolved = os.path.abspath(candidate)
        if not resolved:
            raise ConanInvalidConfiguration(
                f"Required tool {executable} was not found; set "
                f"{environment_variable} or add it to PATH"
            )
        return os.path.abspath(resolved)

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
