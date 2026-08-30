#!/usr/bin/env python3
"""Conan recipe for SDL2 2.32.10 with native multimedia providers."""

import json
import os
import re
import shlex
import shutil
import stat
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run, cross_building
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class SDL2Conan(ConanFile):
    name = "sdl2"
    version = "2.32.10"
    description = "Cross-platform low-level audio, input, and graphics library"
    license = "Zlib", "Apache-2.0"
    homepage = "https://www.libsdl.org/"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    _ctest_names = (
        "testautomation",
        "testatomic",
        "testerror",
        "testthread",
        "testlocale",
        "testplatform",
        "testpower",
        "testfilesystem",
        "testtimer",
        "testver",
        "testqsort",
        "testaudioinfo",
        "testsurround",
        "testkeys",
        "testbounds",
        "testdisplayinfo",
    )

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(
            self,
            **self.conan_data["sources"],
            strip_root=True,
            excludes=(
                "SDL2-2.32.10/android-project-ant/src",
                "SDL2-2.32.10/android-project-ant/AndroidManifest.xml",
            ),
        )
        for relative in (
            "android-project-ant/src",
            "android-project-ant/AndroidManifest.xml",
        ):
            path = os.path.join(self.source_folder, relative)
            if os.path.lexists(path):
                raise ConanInvalidConfiguration(
                    f"excluded legacy link survived source extraction: {relative}"
                )
        for relative in (
            "src/audio/ohaudio",
            "src/video/nativewindow",
        ):
            path = Path(self.source_folder, relative)
            if os.path.lexists(path):
                raise ConanInvalidConfiguration(
                    f"native backend source directory unexpectedly exists: {relative}"
                )
            path.mkdir(parents=True)
        apply_conandata_patches(self)

    def generate(self):
        toolchain = CMakeToolchain(self)
        shared = bool(self.options.shared)
        toolchain.variables["SDL_SHARED"] = shared
        # Upstream's CTest executables link SDL2::SDL2-static even when the
        # package-under-test is shared. Keep that target build-local and trim
        # it from the installed shared package below.
        toolchain.variables["SDL_STATIC"] = True
        toolchain.variables["SDL_STATIC_PIC"] = bool(
            self.options.get_safe("fPIC", True)
        )
        toolchain.variables["SDL_TEST"] = True
        toolchain.variables["SDL_TESTS"] = True

        if str(self.settings.os) == "OHOS":
            # HarmonyOS is not a built-in CMake platform in the current worker.
            # This selects SDL's Unix capability probes without changing target OS.
            toolchain.variables["UNIX"] = True
            toolchain.variables["SDL_OHAUDIO"] = True
            toolchain.variables["SDL_NATIVEWINDOW"] = True
            toolchain.variables["SDL_OPENGL"] = False
            toolchain.variables["SDL_OPENGLES"] = True
            toolchain.variables["SDL_VULKAN"] = False
            toolchain.variables["SDL_DUMMYAUDIO"] = True
            toolchain.variables["SDL_DUMMYVIDEO"] = True
            toolchain.variables["SDL_OFFSCREEN"] = True
            toolchain.variables["SDL_HIDAPI"] = False
            for option in (
                "SDL_ALSA",
                "SDL_ARTS",
                "SDL_DIRECTFB",
                "SDL_ESD",
                "SDL_FUSIONSOUND",
                "SDL_JACK",
                "SDL_KMSDRM",
                "SDL_LIBUDEV",
                "SDL_NAS",
                "SDL_PIPEWIRE",
                "SDL_PULSEAUDIO",
                "SDL_RPI",
                "SDL_SNDIO",
                "SDL_VIVANTE",
                "SDL_WAYLAND",
                "SDL_X11",
            ):
                toolchain.variables[option] = False
            toolchain.variables["SDL_UNVERSIONED_SHARED"] = shared
            for language in ("C", "CXX"):
                toolchain.variables[
                    f"CMAKE_SHARED_LIBRARY_SONAME_{language}_FLAG"
                ] = "-Wl,-soname,"
                toolchain.variables[
                    f"CMAKE_SHARED_LIBRARY_RUNTIME_{language}_FLAG"
                ] = "-Wl,-rpath,"
                toolchain.variables[
                    f"CMAKE_SHARED_LIBRARY_RUNTIME_{language}_FLAG_SEP"
                ] = ":"
                toolchain.variables[
                    f"CMAKE_SHARED_LIBRARY_RPATH_LINK_{language}_FLAG"
                ] = "-Wl,-rpath-link,"
            toolchain.variables["CMAKE_BUILD_RPATH_USE_ORIGIN"] = True
        else:
            toolchain.variables["SDL_OHAUDIO"] = False
            toolchain.variables["SDL_NATIVEWINDOW"] = False

        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(cli_args=["--parallel", "1"])

        if not can_run(self):
            self.output.info(
                "SDL2 upstream target suite: 0/16 CTest containers and "
                "0/300 enabled automation cases NOT_RUN (target execution required)"
            )
            return

        if str(self.settings.os) == "OHOS":
            self._sign_upstream_runtime_closure()
        self._run_upstream_tests()

    def package(self):
        CMake(self).install()
        if self.options.shared:
            self._remove_shared_package_static_core()
        self._relocate_metadata()
        require_codesign = False
        if str(self.settings.os) == "OHOS" and self.options.shared:
            require_codesign = self._sign_shared_package_for_runtime(
                Path(self.package_folder, "lib", "libSDL2.so")
            )
        self._validate_package_layout(require_codesign=require_codesign)
        copy(
            self,
            "LICENSE.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "SDL2")

        core = self.cpp_info.components["SDL2"]
        core.libs = ["SDL2"]
        core.includedirs = ["include", "include/SDL2"]
        core.set_property("pkg_config_name", "sdl2")
        if self.options.shared:
            core.set_property("cmake_target_name", "SDL2::SDL2")
        else:
            core.set_property("cmake_target_name", "SDL2::SDL2-static")
            core.set_property("cmake_target_aliases", ["SDL2::SDL2"])

        if not self.options.shared:
            if str(self.settings.os) == "Linux":
                core.system_libs = ["dl", "m", "pthread", "rt"]
            elif str(self.settings.os) == "OHOS":
                core.system_libs = [
                    "ohaudio",
                    "native_window",
                    "EGL",
                    "GLESv2",
                    "m",
                    "pthread",
                ]

        main = self.cpp_info.components["SDL2main"]
        main.libs = ["SDL2main"]
        main.includedirs = ["include", "include/SDL2"]
        main.requires = ["SDL2"]
        main.set_property("cmake_target_name", "SDL2::SDL2main")

        test = self.cpp_info.components["SDL2test"]
        test.libs = ["SDL2_test"]
        test.includedirs = ["include", "include/SDL2"]
        test.requires = ["SDL2"]
        test.set_property("cmake_target_name", "SDL2::SDL2test")

    def _run_upstream_tests(self):
        ctest = self._resolve_tool("ctest", llvm=False)
        environment = Environment()
        if self.options.shared:
            environment.prepend_path("LD_LIBRARY_PATH", self.build_folder)
        command = (
            f"{shlex.quote(ctest)} --test-dir {shlex.quote(self.build_folder)} "
            "-V --output-on-failure --no-tests=error"
        )
        with environment.vars(self).apply():
            self.run(command)

    def _sign_upstream_runtime_closure(self):
        inventory = self._ctest_inventory()
        tests = inventory.get("tests")
        if not isinstance(tests, list):
            raise ConanInvalidConfiguration("CTest inventory has no tests array")
        names = [test.get("name") for test in tests]
        if names != list(self._ctest_names):
            raise ConanInvalidConfiguration(
                f"unexpected SDL2 CTest inventory: {names!r}"
            )
        commands = []
        build_root = Path(self.build_folder).resolve()
        for test in tests:
            command = test.get("command")
            if not isinstance(command, list) or not command:
                raise ConanInvalidConfiguration(
                    f"CTest entry has no executable command: {test.get('name')}"
                )
            executable = Path(command[0]).resolve()
            try:
                executable.relative_to(build_root)
            except ValueError as exc:
                raise ConanInvalidConfiguration(
                    f"CTest executable escapes the build folder: {executable}"
                ) from exc
            commands.append(executable)
        if len(set(commands)) != len(self._ctest_names):
            raise ConanInvalidConfiguration("CTest executable paths are not unique")
        for executable in commands:
            self._sign_elf(executable)
        if self.options.shared:
            self._sign_elf(build_root / "libSDL2.so")

    def _ctest_inventory(self):
        ctest = self._resolve_tool("ctest", llvm=False)
        result = subprocess.run(
            [ctest, "--show-only=json-v1"],
            cwd=self.build_folder,
            check=True,
            capture_output=True,
            text=True,
        )
        inventory_path = Path(self.build_folder, "sdl2-ctest-inventory.json")
        inventory_path.write_text(result.stdout, encoding="utf-8")
        return json.loads(result.stdout)

    def _remove_shared_package_static_core(self):
        archive = Path(self.package_folder, "lib", "libSDL2.a")
        if not archive.is_file() or archive.is_symlink():
            raise ConanException(
                "shared test build did not install the expected static core"
            )
        archive.unlink()

        cmake_dir = Path(self.package_folder, "lib", "cmake", "SDL2")
        static_targets = sorted(cmake_dir.glob("SDL2staticTargets*.cmake"))
        if len(static_targets) < 2:
            raise ConanException(
                "shared package has no complete SDL2 static-target metadata set"
            )
        for target_file in static_targets:
            target_file.unlink()

    def _relocate_metadata(self):
        pc_path = Path(self.package_folder, "lib", "pkgconfig", "sdl2.pc")
        if not pc_path.is_file():
            raise ConanException("installed sdl2.pc is missing")
        content = pc_path.read_text(encoding="utf-8")
        content = self._replace_unique_metadata_line(
            content,
            r"^prefix=.*$",
            "prefix=${pcfiledir}/../..",
            "prefix",
        )
        if str(self.settings.os) == "OHOS":
            provider_flags = (
                "-lohaudio -lnative_window -lEGL -lGLESv2 -lm -lpthread"
            )
            if self.options.shared:
                field_pattern = r"^Libs\.private:.*$"
                field_value = f"Libs.private: {provider_flags}"
                field_name = "Libs.private"
            else:
                field_pattern = r"^Libs:.*$"
                field_value = f"Libs: -L${{libdir}} -lSDL2 {provider_flags}"
                field_name = "Libs"
            content = self._replace_unique_metadata_line(
                content,
                field_pattern,
                field_value,
                field_name,
            )
        pc_path.write_text(content, encoding="utf-8")

        config_path = Path(self.package_folder, "bin", "sdl2-config")
        if not config_path.is_file():
            raise ConanException("installed sdl2-config is missing")
        config_content = config_path.read_text(encoding="utf-8")
        if "bindir=`cd -P" not in config_content or "prefix=`cd -P" not in config_content:
            raise ConanException("sdl2-config is not relocatable")
        config_content, count = re.subn(
            r"^(\s*echo )-I\$\{prefix\}/include/SDL2(\s+-D_REENTRANT\s*)$",
            r"\1-I${prefix}/include -I${prefix}/include/SDL2\2",
            config_content,
            count=1,
            flags=re.MULTILINE,
        )
        if count != 1:
            raise ConanException("sdl2-config has no unique --cflags output")
        if str(self.settings.os) == "OHOS":
            config_content, count = re.subn(
                r"^\s*sdl_static_libs=.*$",
                '      sdl_static_libs=$(echo " -lSDL2 -lohaudio -lnative_window '
                '-lEGL -lGLESv2 -lm -lpthread" | sed -E '
                '"s#-lSDL2[ $]#$libdir/libSDL2.a #g")',
                config_content,
                count=1,
                flags=re.MULTILINE,
            )
            if count != 1:
                raise ConanException(
                    "sdl2-config has no unique static provider output"
                )
        config_path.write_text(config_content, encoding="utf-8")

        if not self.options.shared:
            static_targets = Path(
                self.package_folder,
                "lib",
                "cmake",
                "SDL2",
                "SDL2staticTargets.cmake",
            )
            if not static_targets.is_file():
                raise ConanException("SDL2 static CMake target metadata is missing")
            target_content = static_targets.read_text(encoding="utf-8")
            if str(self.settings.os) == "OHOS":
                providers = (
                    r"\$<LINK_ONLY:ohaudio>;\$<LINK_ONLY:native_window>;"
                    r"\$<LINK_ONLY:EGL>;\$<LINK_ONLY:GLESv2>;"
                    r"\$<LINK_ONLY:m>;\$<LINK_ONLY:pthread>"
                )
                target_content, count = re.subn(
                    r'^(\s*INTERFACE_LINK_LIBRARIES )"[^"]*"$',
                    lambda match: f'{match.group(1)}"{providers}"',
                    target_content,
                    count=1,
                    flags=re.MULTILINE,
                )
                if count != 1:
                    raise ConanException(
                        "SDL2 static CMake target has no unique link interface"
                    )
                static_targets.write_text(target_content, encoding="utf-8")

        self._validate_relocatable_metadata()

    @staticmethod
    def _replace_unique_metadata_line(content, pattern, replacement, field_name):
        updated, count = re.subn(
            pattern,
            replacement,
            content,
            flags=re.MULTILINE,
        )
        if count != 1:
            raise ConanException(
                f"sdl2.pc has no unique {field_name} field"
            )
        return updated

    def _validate_relocatable_metadata(self):
        metadata = [
            Path(self.package_folder, "lib", "pkgconfig", "sdl2.pc"),
            Path(self.package_folder, "bin", "sdl2-config"),
        ]
        metadata.extend(
            sorted(Path(self.package_folder, "lib", "cmake", "SDL2").glob("*.cmake"))
        )
        forbidden_roots = []
        for folder in (self.source_folder, self.build_folder, self.package_folder):
            if folder:
                forbidden_roots.extend(
                    (str(folder).lower(), str(folder).replace("\\", "/").lower())
                )

        for path in metadata:
            if not path.is_file():
                raise ConanException(f"required SDL2 metadata is missing: {path}")
            text = path.read_text(encoding="utf-8")
            lowered = text.lower()
            residue = [root for root in forbidden_roots if root and root in lowered]
            if residue:
                raise ConanException(
                    f"SDL2 metadata retains a build/package path: {path}"
                )
            if re.search(r"(?<![A-Za-z0-9+.-])[A-Za-z]:[\\/]", text):
                raise ConanException(
                    f"SDL2 metadata retains a drive-letter path: {path}"
                )

    def _validate_package_layout(self, require_codesign=False):
        library = Path(self.package_folder, "lib", "libSDL2.so")
        archive = Path(self.package_folder, "lib", "libSDL2.a")
        main_archive = Path(self.package_folder, "lib", "libSDL2main.a")
        test_archive = Path(self.package_folder, "lib", "libSDL2_test.a")
        if str(self.settings.os) == "OHOS":
            self._reject_package_symlinks()
        for component in (main_archive, test_archive):
            if not component.is_file() or component.is_symlink():
                raise ConanException(f"required SDL2 component is missing: {component}")
        if self.options.shared:
            if not library.exists():
                raise ConanException("shared package requires libSDL2.so")
            if archive.exists() or archive.is_symlink():
                raise ConanException("shared package unexpectedly contains libSDL2.a")
            if str(self.settings.os) == "OHOS":
                if not library.is_file() or library.is_symlink():
                    raise ConanException(
                        "OHOS shared package requires one real libSDL2.so"
                    )
                aliases = list(
                    Path(self.package_folder, "lib").glob("libSDL2-*.so*")
                )
                if aliases:
                    raise ConanException(
                        f"OHOS shared package contains version aliases: {aliases}"
                    )
                self._validate_shared_elf(library, require_codesign)
        else:
            if not archive.is_file() or archive.is_symlink():
                raise ConanException("static package requires one real libSDL2.a")
            shared_entries = list(Path(self.package_folder, "lib").glob("libSDL2*.so*"))
            if shared_entries:
                raise ConanException(
                    f"static package unexpectedly contains shared artifacts: {shared_entries}"
                )

    def _reject_package_symlinks(self):
        for current, directories, files in os.walk(self.package_folder):
            for name in list(directories) + list(files):
                path = os.path.join(current, name)
                if os.path.islink(path):
                    raise ConanException(f"SDL2 package contains a symbolic link: {path}")

    def _sign_shared_package_for_runtime(self, library):
        if cross_building(self):
            self.output.info(
                "SDL2 shared package: PACKAGE_CODESIGN=NOT_RUN "
                "(target execution must sign a task-private copy)"
            )
            return False
        self._sign_elf(library)
        return True

    def _validate_shared_elf(self, library, require_codesign):
        readelf = self._resolve_tool("readelf")
        header = subprocess.run(
            [readelf, "-h", str(library)],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        if "AArch64" not in header:
            raise ConanException("libSDL2.so is not an AArch64 ELF")
        dynamic = subprocess.run(
            [readelf, "-dW", str(library)],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        sonames = re.findall(r"\(SONAME\).*?\[([^]]+)\]", dynamic)
        if sonames != [library.name]:
            raise ConanException(f"invalid libSDL2.so SONAME: {sonames!r}")
        needed = re.findall(r"\(NEEDED\).*?\[([^]]+)\]", dynamic)
        if any("/" in item or "\\" in item for item in needed):
            raise ConanException(f"path-bearing libSDL2.so dependency: {needed!r}")
        if re.search(r"\((?:RPATH|RUNPATH)\)", dynamic):
            raise ConanException("libSDL2.so contains a packaged RPATH/RUNPATH")
        if require_codesign:
            self._validate_signed_elf(readelf, library)

    def _sign_elf(self, executable):
        executable = Path(executable)
        if not executable.is_file():
            raise ConanInvalidConfiguration(
                f"required OHOS ELF is missing: {executable}"
            )
        objcopy = self._resolve_tool("objcopy")
        readelf = self._resolve_tool("readelf")
        signer = self._resolve_tool("binary-sign-tool", llvm=False)
        temporary = executable.with_name(f"{executable.name}.signing-{os.getpid()}")
        original_mode = stat.S_IMODE(executable.stat().st_mode)
        try:
            shutil.copy2(executable, temporary)
            sections = subprocess.run(
                [readelf, "-S", str(temporary)],
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            if ".codesign" in sections:
                subprocess.run(
                    [objcopy, "--remove-section", ".codesign", str(temporary)],
                    check=True,
                )
            subprocess.run(
                [
                    signer,
                    "sign",
                    "-inFile",
                    str(temporary),
                    "-outFile",
                    str(temporary),
                    "-selfSign",
                    "1",
                ],
                check=True,
            )
            os.chmod(temporary, original_mode | 0o755)
            self._validate_signed_elf(readelf, temporary)
            os.replace(temporary, executable)
            os.chmod(executable, original_mode | 0o755)
            self._validate_signed_elf(readelf, executable)
        finally:
            if temporary.exists():
                temporary.unlink()

    @staticmethod
    def _validate_signed_elf(readelf, executable):
        sections = subprocess.run(
            [readelf, "-SW", str(executable)],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        matches = re.findall(
            r"^\s*\[\s*\d+\]\s+\.codesign\s+\S+\s+"
            r"[0-9A-Fa-f]+\s+[0-9A-Fa-f]+\s+([0-9A-Fa-f]+)\s+",
            sections,
            flags=re.MULTILINE,
        )
        if len(matches) != 1 or int(matches[0], 16) <= 0:
            raise ConanException(
                f"ELF requires one non-empty .codesign section: {executable}"
            )
        if os.name != "nt" and not (
            stat.S_IMODE(Path(executable).stat().st_mode) & stat.S_IXUSR
        ):
            raise ConanException(f"signed ELF lacks owner execute permission: {executable}")

    def _resolve_tool(self, tool, llvm=True):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        compiler = executables.get("c") or shutil.which("cc")
        compiler_path = shutil.which(compiler) if compiler else None
        compiler_path = compiler_path or compiler
        compiler_dir = os.path.dirname(compiler_path) if compiler_path else ""
        compiler_name = os.path.basename(compiler_path) if compiler_path else ""
        suffix = (
            compiler_name[len("clang") :]
            if compiler_name.startswith("clang")
            else ""
        )
        candidates = [executables.get(tool)]
        if compiler_dir:
            if llvm:
                candidates.extend(
                    [
                        os.path.join(compiler_dir, f"llvm-{tool}{suffix}"),
                        os.path.join(compiler_dir, f"llvm-{tool}"),
                    ]
                )
            candidates.append(os.path.join(compiler_dir, tool))
        if llvm and suffix:
            candidates.append(f"llvm-{tool}{suffix}")
        if llvm:
            candidates.append(f"llvm-{tool}")
        candidates.append(tool)
        for candidate in candidates:
            if candidate:
                resolved = shutil.which(candidate)
                if resolved:
                    return resolved
        raise ConanInvalidConfiguration(f"required tool was not found: {tool}")
