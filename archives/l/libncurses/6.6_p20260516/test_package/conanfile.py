#!/usr/bin/env python3
"""Consumer tests for the static narrow-character libncurses package."""

import os
import re
import shlex
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualBuildEnv


class LibNcursesTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    _config_script = "ncurses6-config"
    _pkgconfig_files = (
        "form.pc",
        "menu.pc",
        "ncurses++.pc",
        "ncurses.pc",
        "panel.pc",
    )
    _package_archives = (
        "libform.a",
        "libmenu.a",
        "libncurses++.a",
        "libncurses.a",
        "libpanel.a",
    )
    _monitored_archives = _package_archives + ("libtinfo.a", "libncursesw.a")

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        # The metadata consumers link straight from this recipe, so the build
        # environment (notably the SDK library path the linker itself needs)
        # must be available as a Conan env file for that step.
        VirtualBuildEnv(self).generate()
        toolchain = CMakeToolchain(self)
        toolchain.variables["LIBNCURSES_PACKAGE_ROOT"] = str(
            self.dependencies["libncurses"].package_folder
        )
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        self._build_consumer_with_log(cmake)

    def _build_consumer_with_log(self, cmake):
        """Build the consumers with their output bound to a log file.

        Letting the recipe process output streams be inherited by the child
        makes the first compiler invocation on this platform fail without a
        single diagnostic line; binding the build output to a file keeps the
        build reproducible and keeps the compiler output available for
        diagnosis instead of losing it.
        """
        log_path = os.path.join(self.build_folder, "cmake-build.log")
        try:
            with open(log_path, "w", encoding="utf-8") as stream:
                cmake.build(build_tool_args=["-j1"], stdout=stream, stderr=stream)
        except ConanException as error:
            self.output.error("consumer build failed; last lines of cmake-build.log:")
            self.output.error("\n".join(self._log_tail(log_path)))
            raise ConanException(
                f"consumer build failed, full log: {log_path}"
            ) from error
        with open(log_path, encoding="utf-8", errors="replace") as stream:
            content = stream.read().splitlines()
        self.output.info(f"--- cmake-build.log ({len(content)} lines) ---")
        for start in range(0, len(content), 500):
            self.output.info("\n".join(content[start : start + 500]))

    @staticmethod
    def _read_log(path):
        if not os.path.isfile(path):
            return f"<missing log file: {path}>"
        with open(path, encoding="utf-8", errors="replace") as stream:
            return stream.read()

    @staticmethod
    def _log_tail(path, lines=80):
        if not os.path.isfile(path):
            return [f"<missing log file: {path}>"]
        with open(path, encoding="utf-8", errors="replace") as stream:
            content = stream.read().splitlines()
        return content[-lines:]

    def test(self):
        if not can_run(self):
            return

        runtime_dir = os.path.join(self.build_folder, "runtime")
        os.makedirs(runtime_dir, exist_ok=True)
        input_path = os.path.join(runtime_dir, "input.txt")
        with open(input_path, "w", encoding="ascii"):
            pass

        bindir = self.cpp.build.bindirs[0]
        binaries = (
            "test_curses_module",
            "test_ncurses_components",
            "test_ohos_platform",
            "test_find_curses_module",
        )
        for name in binaries:
            binary = os.path.join(bindir, name)
            output_path = os.path.join(runtime_dir, f"{name}.out")
            self.run(f'"{binary}" "{output_path}" "{input_path}"', env="conanrun")

        metadata = self._test_metadata_interfaces(runtime_dir)
        self._test_ohos_static_contract(runtime_dir, metadata)

    @staticmethod
    def _capture(command, environment=None):
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            env=environment,
        )
        if result.returncode != 0:
            raise ConanException(
                f"metadata command failed ({result.returncode}): "
                f"{' '.join(command)}\n{result.stdout}{result.stderr}"
            )
        return result.stdout.strip()

    @staticmethod
    def _require_path_flag(flags, option, expected):
        expected = os.path.realpath(expected)
        for token in shlex.split(flags):
            if token.startswith(option):
                actual = os.path.realpath(token[len(option) :])
                if actual == expected:
                    return
        raise ConanException(f"metadata flags do not contain {option}{expected}: {flags}")

    def _compile_metadata_consumer(
        self,
        label,
        cflags,
        libs,
        runtime_dir,
        package_root,
        required_archives,
        source_name="test_metadata.c",
        language="c",
        definitions=(),
    ):
        compiler_names = ("clang++", "c++") if language == "c++" else ("clang", "cc")
        compiler = next(
            (path for path in map(shutil.which, compiler_names) if path), None
        )
        if compiler is None:
            raise ConanException(
                f"no target {language} compiler is available for metadata tests"
            )

        source = os.path.join(self.source_folder, "src", source_name)
        binary = os.path.join(runtime_dir, f"test_metadata_{label}")
        command = [compiler]
        command.extend(shlex.split(cflags))
        command.extend(f"-D{definition}" for definition in definitions)
        command.extend([source, "-o", binary, "-Wl,-t"])
        command.extend(shlex.split(libs))

        # The link goes through ConanFile.run with the generated build env so the
        # compiler keeps the environment the profile provides (the SDK linker
        # itself needs the SDK library directory on LD_LIBRARY_PATH, see E120
        # and E266); a bare subprocess would inherit only this process
        # environment. The output is bound to a file so the link trace stays
        # readable and a failure cannot be silent.
        trace_path = os.path.join(runtime_dir, f"link-{label}.log")
        quoted = " ".join(shlex.quote(part) for part in command)
        try:
            self.run(f"{quoted} > {shlex.quote(trace_path)} 2>&1", env="conanbuild")
        except ConanException as error:
            trace = self._read_log(trace_path)
            raise ConanException(
                f"{label} metadata consumer failed to link:\n{trace}"
            ) from error
        trace = self._read_log(trace_path)

        package_library_dir = os.path.realpath(os.path.join(package_root, "lib"))
        selected = {}
        foreign = []
        for line in trace.splitlines():
            for token in line.split():
                for archive_name in self._monitored_archives:
                    marker = token.find(archive_name)
                    if marker < 0:
                        continue
                    archive = os.path.realpath(token[: marker + len(archive_name)])
                    if os.path.dirname(archive) != package_library_dir:
                        foreign.append(archive)
                    else:
                        selected.setdefault(archive_name, []).append(archive)

        if foreign:
            raise ConanException(
                f"{label} metadata selected archives outside the package: "
                f"{', '.join(sorted(set(foreign)))}\n{trace}"
            )
        missing = sorted(set(required_archives) - set(selected))
        if missing:
            raise ConanException(
                f"{label} metadata did not select packaged archives: "
                f"{', '.join(missing)}\n{trace}"
            )
        if re.search(
            r"lib(?:ncurses[^/ ]*|form|menu|panel|tinfo[^/ ]*)\.so", trace.replace("\\", "/")
        ):
            raise ConanException(f"{label} metadata linked a shared curses library:\n{trace}")
        self.output.info(f"METADATA_{label.upper()}_LINKS=" + ",".join(sorted(selected)))

        environment = os.environ.copy()
        terminfo = os.path.join(package_root, "share", "terminfo")
        environment.update(
            {"TERM": "xterm", "TERMINFO": terminfo, "TERMINFO_DIRS": terminfo}
        )
        self._capture([binary], environment)
        self.output.info(f"METADATA_{label.upper()}=3/3")
        return binary

    @staticmethod
    def _usable_shell():
        """Return the first shell that this process is actually allowed to run.

        The environment PATH can resolve ``bash`` to a copy that the test-phase
        SELinux domain may not execute, so every candidate is probed before it is
        handed to the metadata consumers.
        """
        candidates = (
            os.environ.get("CONFIG_SHELL"),
            "/data/service/hnp/bin/bash",
            "/bin/sh",
            "/system/bin/sh",
            shutil.which("bash"),
            shutil.which("sh"),
        )
        for candidate in candidates:
            if not candidate or not os.path.isfile(candidate):
                continue
            try:
                probe = subprocess.run(
                    [candidate, "-c", "exit 0"],
                    check=False,
                    capture_output=True,
                    text=True,
                )
            except OSError:
                # The candidate exists but this process may not execute it
                # (SELinux domain restriction); try the next one.
                continue
            if probe.returncode == 0:
                return candidate
        raise ConanException(
            "no executable target shell is available for the ncurses6-config consumer"
        )

    def _test_metadata_interfaces(self, runtime_dir):
        package_root = os.path.realpath(str(self.dependencies["libncurses"].package_folder))
        include_dir = os.path.join(package_root, "include")
        library_dir = os.path.join(package_root, "lib")
        terminfo_dir = os.path.join(package_root, "share", "terminfo")

        config = os.path.join(package_root, "bin", self._config_script)
        shell = self._usable_shell()
        config_command = [shell, config]
        if os.path.realpath(self._capture(config_command + ["--prefix"])) != package_root:
            raise ConanException(f"{self._config_script} returned a non-package prefix")
        for option, expected in (
            ("--includedir", include_dir),
            ("--libdir", library_dir),
            ("--terminfo", terminfo_dir),
        ):
            actual = os.path.realpath(self._capture(config_command + [option]))
            if actual != os.path.realpath(expected):
                raise ConanException(
                    f"{self._config_script} {option} escaped the package"
                )
        config_cflags = self._capture(config_command + ["--cflags"])
        config_libs = self._capture(config_command + ["--libs"])
        self._require_path_flag(config_cflags, "-I", include_dir)
        self._require_path_flag(config_libs, "-L", library_dir)
        config_binary = self._compile_metadata_consumer(
            "config",
            config_cflags,
            config_libs,
            runtime_dir,
            package_root,
            ("libncurses.a",),
        )

        pkg_config = shutil.which("pkg-config")
        if pkg_config is None:
            raise ConanException("pkg-config is required to validate installed .pc files")
        pc_environment = os.environ.copy()
        pc_environment["PKG_CONFIG_PATH"] = ""
        pc_environment["PKG_CONFIG_LIBDIR"] = os.path.join(
            package_root, "lib", "pkgconfig"
        )
        pc_environment.pop("PKG_CONFIG_SYSROOT_DIR", None)
        modules = (
            (
                "form",
                "form",
                ("libform.a", "libncurses.a"),
                "test_metadata.c",
                "c",
                ("NCURSES_METADATA_FORM=1",),
            ),
            (
                "menu",
                "menu",
                ("libmenu.a", "libncurses.a"),
                "test_metadata.c",
                "c",
                ("NCURSES_METADATA_MENU=1",),
            ),
            (
                "ncursesxx",
                "ncurses++",
                ("libncurses++.a", "libncurses.a"),
                "test_metadata_cpp.cpp",
                "c++",
                (),
            ),
            (
                "ncurses",
                "ncurses",
                ("libncurses.a",),
                "test_metadata.c",
                "c",
                (),
            ),
            (
                "panel",
                "panel",
                ("libpanel.a", "libncurses.a"),
                "test_metadata.c",
                "c",
                ("NCURSES_METADATA_PANEL=1",),
            ),
        )
        for label, module, required_archives, source_name, language, definitions in modules:
            pc_prefix = self._capture(
                [pkg_config, "--variable=prefix", module], pc_environment
            )
            if os.path.realpath(pc_prefix) != package_root:
                raise ConanException(f"pkg-config {module} returned a non-package prefix")
            pc_cflags = self._capture([pkg_config, "--cflags", module], pc_environment)
            pc_libs = self._capture(
                [pkg_config, "--static", "--libs", module], pc_environment
            )
            self._require_path_flag(pc_cflags, "-I", include_dir)
            self._require_path_flag(pc_libs, "-L", library_dir)
            self._compile_metadata_consumer(
                f"pkgconfig_{label}",
                pc_cflags,
                pc_libs,
                runtime_dir,
                package_root,
                required_archives,
                source_name=source_name,
                language=language,
                definitions=definitions,
            )
        return config_binary

    def _test_ohos_static_contract(self, runtime_dir, config_binary):
        """HarmonyOS platform contract for the narrow static ncurses package.

        The platform shell links a shared wide curses library, so this package
        must ship static archives only and consumers must not pick up any
        shared curses library from the build host or from the target system.
        """
        package_root = os.path.realpath(str(self.dependencies["libncurses"].package_folder))
        library_dir = Path(package_root) / "lib"

        shared = sorted(
            str(path)
            for pattern in ("*.so", "*.so.*")
            for path in Path(package_root).rglob(pattern)
        )
        if shared:
            raise ConanException(
                "static-only package ships shared objects: " + ", ".join(shared)
            )
        self.output.info("OHOS_STATIC_ONLY=1/1")

        missing = sorted(
            name for name in self._package_archives if not (library_dir / name).is_file()
        )
        if missing:
            raise ConanException(
                "packaged static archives are incomplete: " + ", ".join(missing)
            )
        self.output.info(
            f"OHOS_STATIC_ARCHIVES={len(self._package_archives)}/{len(self._package_archives)}"
        )

        readelf = shutil.which("readelf")
        if readelf is None:
            raise ConanException("readelf is required for the HarmonyOS ELF contract")
        header = self._capture([readelf, "-h", config_binary])
        machine = re.search(r"Machine:\s*(.+)", header)
        if machine is None or "AArch64" not in machine.group(1):
            raise ConanException(
                f"consumer binary is not an AArch64 target binary:\n{header}"
            )
        dynamic = self._capture([readelf, "-d", config_binary])
        shared_curses = re.findall(
            r"\(NEEDED\)\s+Shared library:\s+\[(lib(?:ncurses|tinfo|form|menu|panel)[^\]]*)\]",
            dynamic,
        )
        if shared_curses:
            raise ConanException(
                "consumer binary dynamically needs curses libraries: "
                + ", ".join(sorted(set(shared_curses)))
            )
        self.output.info("OHOS_STATIC_LINKAGE=2/2")
