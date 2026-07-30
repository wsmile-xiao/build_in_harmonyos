#!/usr/bin/env python3
"""Conan recipe - SDL2_net 2.2.0 (CMake)."""

import os
import re
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    save,
)


required_conan_version = ">=2.0"


class Sdl2NetConan(ConanFile):
    name = "sdl2_net"
    version = "2.2.0"
    description = "Portable TCP and UDP networking library for SDL2"
    license = "Zlib"
    homepage = "https://github.com/libsdl-org/SDL_net"
    url = "https://github.com/libsdl-org/SDL_net"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

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
            f"Required OHOS build tool was not found: {tool}"
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

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires(
            "sdl2/2.30.10",
            options={"shared": False},
            transitive_headers=True,
            transitive_libs=True,
        )

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        source = self.conan_data["sources"][str(self.version)]
        get(self, **source, strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        platform_modules = os.path.join(
            self.build_folder, "_cmake_modules"
        ).replace("\\", "/")
        for system_name in ("OHOS", "HarmonyOS"):
            save(
                self,
                os.path.join(
                    platform_modules, "Platform", f"{system_name}.cmake"
                ),
                "include(Platform/Linux)\n",
            )

        CMakeDeps(self).generate()

        tc = CMakeToolchain(self)
        sdl2_config_dir = os.path.join(
            self.dependencies["sdl2"].package_folder,
            "lib",
            "cmake",
            "SDL2",
        )
        if not os.path.isfile(os.path.join(sdl2_config_dir, "sdl2-config.cmake")):
            raise ConanException(
                "The published SDL2 package does not contain its native CMake config"
            )
        tc.variables["SDL2_DIR"] = sdl2_config_dir.replace("\\", "/")
        tc.variables["CMAKE_SKIP_RPATH"] = True
        tc.variables["CMAKE_MODULE_PATH"] = platform_modules
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(
            self.options.get_safe("fPIC", True)
        )
        for language in ("C", "CXX"):
            tc.variables[
                f"CMAKE_SHARED_LIBRARY_SONAME_{language}_FLAG"
            ] = "-Wl,-soname,"
            tc.variables[
                f"CMAKE_SHARED_LIBRARY_RUNTIME_{language}_FLAG"
            ] = "-Wl,-rpath,"
            tc.variables[
                f"CMAKE_SHARED_LIBRARY_RUNTIME_{language}_FLAG_SEP"
            ] = ":"
            tc.variables[
                f"CMAKE_SHARED_LIBRARY_RPATH_LINK_{language}_FLAG"
            ] = "-Wl,-rpath-link,"
        tc.variables["CMAKE_BUILD_WITH_INSTALL_RPATH"] = True
        tc.variables["SDL2NET_INSTALL"] = True
        tc.variables["SDL2NET_SAMPLES"] = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        if str(self.settings.os) == "OHOS" and self.options.shared:
            shared_library = os.path.join(
                self.package_folder, "lib", "libSDL2_net.so"
            )
            if not can_run(self):
                self.output.warning(
                    "Cross build: libSDL2_net.so cannot be signed without "
                    "native OHOS signing tools."
                )
            else:
                self._sign_ohos_elf(shared_library)

    def package_info(self):
        target = (
            "SDL2_net::SDL2_net"
            if self.options.shared
            else "SDL2_net::SDL2_net-static"
        )
        self.cpp_info.set_property("cmake_file_name", "SDL2_net")
        component = self.cpp_info.components["sdl2_net"]
        component.libs = ["SDL2_net"]
        component.includedirs = ["include/SDL2"]
        component.requires = ["sdl2::sdl2"]
        component.set_property("cmake_target_name", target)
        component.set_property("pkg_config_name", "SDL2_net")
        if self.settings.os == "Windows":
            component.system_libs = ["ws2_32", "iphlpapi"]
