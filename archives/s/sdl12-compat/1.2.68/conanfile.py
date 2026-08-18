#!/usr/bin/env python3
"""Conan recipe for sdl12-compat 1.2.68 on HarmonyOS PC."""

import os
import shlex
import shutil
import stat
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    check_sha256,
    copy,
    export_conandata_patches,
    get,
    unzip,
)


class Sdl12CompatConan(ConanFile):
    name = "sdl12-compat"
    version = "1.2.68"
    description = "SDL 1.2 compatibility layer implemented on top of SDL2"
    license = "Zlib"
    homepage = "https://github.com/libsdl-org/sdl12-compat"
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"
    default_options = {"sdl2/*:shared": False}

    _sdl2_revision = "9a6fd1dbbc0ac1eef2a42639df48e3b4"
    _sdl2_package_id = "4b977264131a1c74e82bd6bb51b63cc9aadc4cfa"
    _sdl2_package_revision = "96027f33d6086703ce6fe4e4502533b3"
    _upstream_tests = (
        ("testver", ()),
        ("testplatform", ()),
        ("testerror", ()),
        ("testiconv", ()),
        ("testfile", ()),
        ("testkeys", ()),
        ("testloadso", ("--hello", "libc.so")),
        ("torturethread", ()),
        ("testvidinfo", ()),
        ("testblitspeed", ("--seconds", "1")),
        ("testsem", ("2",)),
        ("testthread", ()),
        ("testtimer", ("10",)),
        ("testjoystick", ()),
    )
    _sdl2_runtime = "libSDL2-2.0.so.0"

    def export_sources(self):
        export_conandata_patches(self)
        copy(
            self,
            "SDL2-LICENSE.txt",
            src=os.path.join(self.recipe_folder, "licenses"),
            dst=os.path.join(self.export_sources_folder, "licenses"),
        )

    def requirements(self):
        # The published package provides the required SDL2 headers and a PIC
        # static archive. A private shared runtime is reconstructed from that
        # archive because sdl12-compat intentionally resolves SDL2 with dlopen.
        self.requires(
            f"sdl2/2.30.10#{self._sdl2_revision}",
            transitive_headers=False,
            transitive_libs=False,
            run=False,
        )

    def validate(self):
        if str(self.settings.os) != "OHOS":
            raise ConanInvalidConfiguration(
                "sdl12-compat/1.2.68 is a HarmonyOS PC adaptation"
            )
        if str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "sdl12-compat/1.2.68 supports HarmonyOS PC aarch64 only"
            )
        if str(self.settings.compiler) != "clang":
            raise ConanInvalidConfiguration(
                "sdl12-compat/1.2.68 requires the HarmonyOS clang toolchain"
            )
        if self.settings_build.os != "OHOS" or str(self.settings_build.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "sdl12-compat/1.2.68 requires a native HarmonyOS PC aarch64 build context"
            )
        dependency = self.dependencies["sdl2"]
        if str(dependency.options.get_safe("shared")) != "False":
            raise ConanInvalidConfiguration(
                "sdl12-compat requires the pinned PIC static sdl2/2.30.10 package"
            )
        if dependency.ref.revision != self._sdl2_revision:
            raise ConanInvalidConfiguration(
                "sdl12-compat requires the audited sdl2/2.30.10 recipe revision"
            )
        if dependency.pref.package_id != self._sdl2_package_id:
            raise ConanInvalidConfiguration(
                "sdl12-compat requires the audited sdl2/2.30.10 package ID"
            )
        if dependency.pref.revision != self._sdl2_package_revision:
            raise ConanInvalidConfiguration(
                "sdl12-compat requires the audited sdl2/2.30.10 package revision"
            )

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        source = self.conan_data["sources"]
        urls = source["url"]
        if isinstance(urls, str):
            urls = [urls]
        local_url = next((url for url in urls if url.startswith("file://")), None)
        if local_url:
            # W3 keeps literal %2D in the cache filename, while Conan's file
            # URL handler decodes it before opening the archive.
            archive = local_url[len("file://"):]
            if not os.path.isfile(archive):
                decoded = archive.replace("%2D", "-").replace("%2d", "-")
                if os.path.isfile(decoded):
                    archive = decoded
            check_sha256(self, archive, source["sha256"])
            unzip(self, archive, destination=self.source_folder, strip_root=True)
            return
        get(self, **source, strip_root=True)

    def generate(self):
        CMakeDeps(self).generate()
        toolchain = CMakeToolchain(self)
        sdl2_include = os.path.join(
            self.dependencies["sdl2"].package_folder, "include", "SDL2"
        )
        toolchain.cache_variables.update(
            {
                "SDL12TESTS": True,
                "SDL12DEVEL": True,
                "STATICDEVEL": False,
                "SDL2_INCLUDE_DIR": sdl2_include,
                "CMAKE_SKIP_RPATH": True,
            }
        )
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        self._build_sdl2_runtime()
        cmake = CMake(self)
        cmake.configure()
        build_environment = Environment()
        build_environment.define("CMAKE_BUILD_PARALLEL_LEVEL", "1")
        with build_environment.vars(self).apply():
            cmake.build()
        compatibility_soname = os.path.join(self.build_folder, "libSDL-1.2.so.0")
        if not os.path.lexists(compatibility_soname):
            os.symlink("libSDL-1.2.so", compatibility_soname)
        if can_run(self):
            environment = Environment()
            environment.prepend_path("LD_LIBRARY_PATH", self.build_folder)
            environment.define("SDL_VIDEODRIVER", "dummy")
            environment.define("SDL_AUDIODRIVER", "dummy")
            with environment.vars(self).apply():
                for test, arguments in self._upstream_tests:
                    command = [os.path.join(self.build_folder, test), *arguments]
                    self.run(
                        " ".join(shlex.quote(argument) for argument in command),
                        cwd=self.build_folder,
                    )

    def package(self):
        CMake(self).install()
        library_directory = os.path.join(self.package_folder, "lib")
        copy(
            self,
            self._sdl2_runtime,
            src=self.build_folder,
            dst=library_directory,
        )
        compatibility_soname = os.path.join(library_directory, "libSDL-1.2.so.0")
        if not os.path.lexists(compatibility_soname):
            os.symlink("libSDL-1.2.so", compatibility_soname)
        license_directory = os.path.join(self.package_folder, "licenses")
        copy(
            self,
            "LICENSE.txt",
            src=self.source_folder,
            dst=license_directory,
        )
        copy(
            self,
            "SDL2-LICENSE.txt",
            src=os.path.join(self.export_sources_folder, "licenses"),
            dst=license_directory,
        )
        self._sign_installed_elfs()
        self._validate_shared_object(
            os.path.join(library_directory, "libSDL-1.2.so"),
            "libSDL-1.2.so.0",
        )
        self._validate_shared_object(
            os.path.join(library_directory, self._sdl2_runtime),
            self._sdl2_runtime,
        )

    def package_info(self):
        self.cpp_info.libs = ["SDL-1.2"]
        self.cpp_info.includedirs = [os.path.join("include", "SDL")]
        self.cpp_info.set_property("cmake_file_name", "SDL")
        self.cpp_info.set_property("cmake_target_name", "SDL::SDL")

    def _build_sdl2_runtime(self):
        dependency = self.dependencies["sdl2"]
        archive = os.path.join(dependency.package_folder, "lib", "libSDL2.a")
        if not os.path.isfile(archive):
            raise ConanInvalidConfiguration(
                f"Published sdl2/2.30.10 package is missing {archive}"
            )
        compiler = self._c_compiler()
        output = os.path.join(self.build_folder, self._sdl2_runtime)
        os.makedirs(self.build_folder, exist_ok=True)
        command = [
            compiler,
            "-shared",
            "-Wl,-z,defs",
            f"-Wl,-soname,{self._sdl2_runtime}",
            "-Wl,--whole-archive",
            archive,
            "-Wl,--no-whole-archive",
            "-lm",
            "-ldl",
            "-lpthread",
            "-o",
            output,
        ]
        self.run(" ".join(shlex.quote(argument) for argument in command))
        self._validate_shared_object(output, self._sdl2_runtime)

    def _validate_shared_object(self, path, expected_soname):
        readelf = self._resolve_tool("READELF", "llvm-readelf")
        header = self._run_tool([readelf, "-h", path])
        dynamic = self._run_tool([readelf, "-d", path])
        if self._elf_type(path) != 3 or "AArch64" not in header:
            raise ConanInvalidConfiguration(
                f"{path} is not an AArch64 ELF shared object"
            )
        if f"Library soname: [{expected_soname}]" not in dynamic:
            raise ConanInvalidConfiguration(
                f"{path} does not have expected SONAME {expected_soname}"
            )
        for line in dynamic.splitlines():
            if "(NEEDED)" in line and "Shared library: [libc.so]" not in line:
                raise ConanInvalidConfiguration(
                    f"{path} has an unexpected runtime dependency: {line.strip()}"
                )
            if "(RPATH)" in line or "(RUNPATH)" in line:
                raise ConanInvalidConfiguration(
                    f"{path} contains a forbidden RPATH/RUNPATH: {line.strip()}"
                )

    def _c_compiler(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        candidate = executables.get("c") or os.environ.get("CC") or "clang"
        resolved = shutil.which(candidate)
        if not resolved and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            resolved = os.path.abspath(candidate)
        if not resolved:
            raise ConanInvalidConfiguration(
                "HarmonyOS C compiler was not found through tools.build:compiler_executables"
            )
        return os.path.abspath(resolved)

    def _sign_installed_elfs(self):
        binaries = []
        for root, _, filenames in os.walk(self.package_folder):
            for filename in filenames:
                candidate = os.path.join(root, filename)
                if not os.path.islink(candidate) and self._elf_type(candidate) in (2, 3):
                    binaries.append(candidate)
        if not binaries:
            raise ConanInvalidConfiguration("Package contains no ELF files to sign")
        objcopy = self._resolve_tool("OBJCOPY", "llvm-objcopy")
        objdump = self._resolve_tool("OBJDUMP", "llvm-objdump")
        signer = self._resolve_tool("BINARY_SIGN_TOOL", "binary-sign-tool")
        for binary in sorted(binaries):
            original_mode = stat.S_IMODE(os.stat(binary).st_mode)
            with tempfile.TemporaryDirectory(
                prefix=".conan-sign-", dir=os.path.dirname(binary)
            ) as temporary_directory:
                unsigned = os.path.join(temporary_directory, "unsigned")
                signed = os.path.join(temporary_directory, "signed")
                shutil.copy2(binary, unsigned)
                if self._has_codesign_section(objdump, unsigned):
                    self._run_tool([objcopy, "--remove-section", ".codesign", unsigned])
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
                    ]
                )
                if self._elf_type(signed) not in (2, 3):
                    raise ConanInvalidConfiguration(
                        f"Signing did not produce an ELF file for {binary}"
                    )
                if not self._has_codesign_section(objdump, signed):
                    raise ConanInvalidConfiguration(
                        f"Signing did not add a .codesign section to {binary}"
                    )
                signature_info = self._run_tool(
                    [signer, "display-sign", "-inFile", signed]
                )
                if "code signature is self-sign" not in signature_info:
                    raise ConanInvalidConfiguration(
                        f"Signing metadata is not readable for {binary}"
                    )
                os.replace(signed, binary)
                os.chmod(binary, original_mode)

    @staticmethod
    def _run_tool(command):
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=60)
        except (OSError, subprocess.SubprocessError) as error:
            raise ConanInvalidConfiguration(
                f"Unable to run {' '.join(command)}: {error}"
            ) from error
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip()
            raise ConanInvalidConfiguration(
                f"Command {' '.join(command)} failed: {detail or result.returncode}"
            )
        return result.stdout

    @classmethod
    def _has_codesign_section(cls, objdump, path):
        return any(
            ".codesign" in line.split()
            for line in cls._run_tool([objdump, "-h", path]).splitlines()
        )

    @staticmethod
    def _elf_type(path):
        try:
            with open(path, "rb") as binary:
                header = binary.read(18)
        except OSError as error:
            raise ConanInvalidConfiguration(f"Unable to inspect {path}: {error}") from error
        if len(header) < 18 or header[:4] != b"\x7fELF":
            return None
        byte_order = {1: "little", 2: "big"}.get(header[5])
        if byte_order is None:
            raise ConanInvalidConfiguration(f"Unsupported ELF byte order in {path}")
        return int.from_bytes(header[16:18], byte_order)

    @staticmethod
    def _resolve_tool(environment_variable, executable):
        candidate = os.environ.get(environment_variable) or executable
        resolved = shutil.which(candidate)
        if not resolved and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            resolved = os.path.abspath(candidate)
        if not resolved:
            raise ConanInvalidConfiguration(
                f"Required tool {executable} was not found; set {environment_variable}"
            )
        return os.path.abspath(resolved)
