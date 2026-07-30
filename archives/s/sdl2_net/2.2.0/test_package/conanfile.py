#!/usr/bin/env python3
"""Conan test package for SDL2_net 2.2.0."""

import os
import re
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class Sdl2NetTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    _executables = (
        "test_upstream_cmake_consumer",
        "test_init_version_byteorder",
        "test_packet_boundaries",
        "test_resolve_errors",
        "test_udp_loopback",
        "test_tcp_loopback",
        "test_socket_set",
    )

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        sdl2_net = self.dependencies["sdl2_net"]
        sdl2 = self.dependencies["sdl2"]
        net_shared = bool(sdl2_net.options.get_safe("shared", True))
        if bool(sdl2.options.get_safe("shared", True)):
            raise ConanInvalidConfiguration(
                "sdl2_net must use the published static SDL2 package"
            )

        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        sdl2_config_dir = os.path.join(
            sdl2.package_folder,
            "lib",
            "cmake",
            "SDL2",
        )
        if not os.path.isfile(os.path.join(sdl2_config_dir, "sdl2-config.cmake")):
            raise ConanInvalidConfiguration(
                "The published SDL2 package does not contain its native CMake config"
            )
        tc.variables["SDL2_DIR"] = sdl2_config_dir.replace("\\", "/")
        tc.variables["CMAKE_SKIP_RPATH"] = True
        tc.variables["SDL2_NET_TEST_SHARED"] = net_shared
        tc.variables["EXPECTED_SDL2_NET_ROOT"] = str(
            sdl2_net.package_folder
        ).replace("\\", "/")
        tc.variables["EXPECTED_SDL2_ROOT"] = str(sdl2.package_folder).replace(
            "\\", "/"
        )
        tc.generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _resolve_ohos_tool(self, tool, llvm=False):
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = compiler_executables.get("c", "")
        compiler_path = shutil.which(compiler) or compiler
        compiler_dir = os.path.dirname(compiler_path)
        compiler_name = os.path.basename(compiler_path)
        version_suffix = (
            compiler_name[len("clang") :]
            if compiler_name.startswith("clang")
            else ""
        )

        candidates = [compiler_executables.get(tool)]
        names = []
        if llvm:
            if version_suffix:
                names.append(f"llvm-{tool}{version_suffix}")
            names.append(f"llvm-{tool}")
        else:
            names.append(tool)
        for name in names:
            if compiler_dir:
                candidates.append(os.path.join(compiler_dir, name))
            candidates.append(os.path.join("/data/service/hnp/bin", name))
            candidates.append(name)

        for candidate in candidates:
            if not candidate:
                continue
            resolved = shutil.which(candidate) or candidate
            if os.path.isfile(resolved):
                return os.path.abspath(resolved)
        raise ConanInvalidConfiguration(
            f"Required OHOS test tool was not found: {tool}"
        )

    @staticmethod
    def _run_tool(arguments, timeout):
        completed = subprocess.run(
            arguments,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        if completed.returncode != 0:
            raise ConanException(
                f"OHOS ELF tool failed ({completed.returncode}): "
                + " ".join(arguments)
                + "\n"
                + completed.stdout
                + completed.stderr
            )
        return completed.stdout

    @staticmethod
    def _codesign_count(section_text):
        return sum(
            1
            for line in section_text.splitlines()
            if re.search(r"\]\s+\.codesign\s", line)
        )

    def _sign_ohos_elf(self, path, recreate=True):
        if not os.path.isfile(path):
            raise ConanException(f"ELF signing input is missing: {path}")

        objcopy = self._resolve_ohos_tool("objcopy", llvm=True)
        readelf = self._resolve_ohos_tool("readelf", llvm=True)
        signer = self._resolve_ohos_tool("binary-sign-tool")
        original_mode = os.stat(path).st_mode & 0o777
        suffix = f".sdl2-net-sign-{os.getpid()}"
        backup = path + suffix + ".backup"

        temporary_paths = (backup,)
        if any(os.path.lexists(item) for item in temporary_paths):
            raise ConanException(f"ELF signing temporary path already exists: {path}")
        if recreate:
            os.replace(path, backup)
        else:
            shutil.copy2(path, backup)
        try:
            if recreate:
                shutil.copy2(backup, path)
            sections = self._run_tool([readelf, "-SW", path], timeout=30)
            existing_count = self._codesign_count(sections)
            if existing_count > 1:
                raise ConanException(
                    f"Input ELF has multiple .codesign sections: {path}"
                )
            if existing_count == 1:
                self._run_tool(
                    [objcopy, "--remove-section", ".codesign", path],
                    timeout=30,
                )
                unsigned_sections = self._run_tool([readelf, "-SW", path], timeout=30)
                if self._codesign_count(unsigned_sections):
                    raise ConanException(
                        f"Unsigned ELF still contains .codesign: {path}"
                    )

            sign_command = [
                signer,
                "sign",
                "-inFile",
                path,
                "-outFile",
                path,
                "-selfSign",
                "1",
            ]
            self.run(shlex.join(sign_command), quiet=True)
            if not os.path.isfile(path):
                raise ConanException(f"OHOS ELF signer produced no output: {path}")
            signed_sections = self._run_tool([readelf, "-SW", path], timeout=30)
            signed_sizes = re.findall(
                r"\]\s+\.codesign\s+\S+\s+\S+\s+\S+\s+"
                r"([0-9a-fA-F]+)\s+",
                signed_sections,
            )
            if (
                self._codesign_count(signed_sections) != 1
                or len(signed_sizes) != 1
                or int(signed_sizes[0], 16) <= 0
            ):
                raise ConanException(
                    f"Signed ELF has an invalid .codesign section: {path}"
                )

            os.chmod(path, original_mode | 0o055)
        except Exception:
            if os.path.lexists(path):
                os.remove(path)
            os.replace(backup, path)
            raise
        finally:
            for temporary in temporary_paths:
                if os.path.lexists(temporary):
                    os.remove(temporary)

    def test(self):
        if not can_run(self):
            self.output.warning(
                "Cross build: seven SDL2_net consumers linked but target execution "
                "is NOT_RUN"
            )
            return
        suffix = ".exe" if self.settings.os == "Windows" else ""
        executables = []
        for name in self._executables:
            executable = os.path.join(self.cpp.build.bindir, name + suffix)
            executables.append(executable)
        staged_paths = []
        run_executables = executables
        staged_library = ""
        if str(self.settings.os) == "OHOS":
            dependency = self.dependencies["sdl2_net"]
            sdl2_dependency = self.dependencies["sdl2"]
            shared = bool(dependency.options.get_safe("shared", True))
            sdl2_shared = bool(sdl2_dependency.options.get_safe("shared", True))
            if sdl2_shared:
                raise ConanInvalidConfiguration(
                    "SDL2_net must use the published static SDL2 package"
                )
            runtime_root = os.environ.get("SDL2_NET_TEST_EXEC_ROOT", "")
            if runtime_root and not os.path.isabs(runtime_root):
                raise ConanException(
                    "SDL2_NET_TEST_EXEC_ROOT must be an absolute target path"
                )
            if runtime_root and (
                not os.path.isdir(runtime_root)
                or os.path.islink(runtime_root)
                or os.listdir(runtime_root)
            ):
                raise ConanException("SDL2_net test execution root is invalid")
            shared_library = ""
            if shared:
                shared_library = os.path.join(
                    dependency.package_folder, "lib", "libSDL2_net.so"
                )
                self._sign_ohos_elf(shared_library)
            if not runtime_root:
                for executable in executables:
                    self._sign_ohos_elf(executable)
            if runtime_root:
                run_executables = []
                if shared:
                    staged_library = os.path.join(runtime_root, "libSDL2_net.so")
                    shutil.copy(shared_library, staged_library)
                    self._sign_ohos_elf(staged_library, recreate=False)
                    staged_paths.append(staged_library)
                for executable in executables:
                    staged = os.path.join(runtime_root, os.path.basename(executable))
                    shutil.copy(executable, staged)
                    self._sign_ohos_elf(staged, recreate=False)
                    staged_paths.append(staged)
                    run_executables.append(staged)
        try:
            for name, executable in zip(
                self._executables, run_executables, strict=True
            ):
                command = shlex.quote(executable)
                if staged_library:
                    quoted_runtime = shlex.quote(os.path.dirname(staged_library))
                    command = (
                        f"LD_LIBRARY_PATH={quoted_runtime}"
                        "${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH} "
                        + command
                    )
                self.run(command, env="conanrun")
                self.output.info(f"SDL2_NET_TEST_PASS name={name}")
        finally:
            for staged in staged_paths:
                if os.path.lexists(staged):
                    os.remove(staged)
