#!/usr/bin/env python3
"""Consumer tests for ncurses CMake config and FindCurses contracts."""

import os
import re
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class NcursesTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"])

    def test(self):
        if not can_run(self):
            return

        runtime_dir = os.path.join(self.build_folder, "runtime")
        os.makedirs(runtime_dir, exist_ok=True)
        input_path = os.path.join(runtime_dir, "input.txt")
        with open(input_path, "w", encoding="ascii"):
            pass

        bindir = self.cpp.build.bindirs[0]
        for name in ("test_curses_module", "test_ncurses_components"):
            binary = os.path.join(bindir, name)
            output_path = os.path.join(runtime_dir, f"{name}.out")
            self.run(
                f'"{binary}" "{output_path}" "{input_path}"',
                env="conanrun",
            )

        self._test_metadata_interfaces(runtime_dir)

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
        raise ConanException(
            f"metadata flags do not contain {option}{expected}: {flags}"
        )

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
        compiler_names = (
            ("clang++", "c++") if language == "c++" else ("clang", "cc")
        )
        compiler = next(
            (path for path in map(shutil.which, compiler_names) if path),
            None,
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
        compiler_environment = os.environ.copy()
        compiler_tmp = os.path.join(runtime_dir, f"tmp-{label}")
        os.makedirs(compiler_tmp, exist_ok=True)
        compiler_environment.update(
            {"TMPDIR": compiler_tmp, "TMP": compiler_tmp, "TEMP": compiler_tmp}
        )
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            env=compiler_environment,
        )
        trace = result.stdout + result.stderr
        normalized_trace = trace.replace("\\", "/")
        if result.returncode != 0:
            raise ConanException(f"{label} metadata consumer failed to link:\n{trace}")

        package_library_dir = os.path.realpath(os.path.join(package_root, "lib"))
        monitored_archives = (
            "libformw.a",
            "libmenuw.a",
            "libncurses++w.a",
            "libncursesw.a",
            "libpanelw.a",
            "libtinfo.a",
            "libtinfow.a",
        )
        selected = {}
        foreign = []
        for line in trace.splitlines():
            for token in line.split():
                for archive_name in monitored_archives:
                    marker = token.find(archive_name)
                    if marker < 0:
                        continue
                    archive = os.path.realpath(
                        token[: marker + len(archive_name)]
                    )
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
            r"lib(?:ncurses[^/ ]*|formw|menuw|panelw|tinfo[^/ ]*)\.so",
            normalized_trace,
        ):
            raise ConanException(
                f"{label} metadata linked a shared curses library:\n{trace}"
            )
        self.output.info(
            f"METADATA_{label.upper()}_LINKS="
            + ",".join(sorted(selected))
        )

        environment = os.environ.copy()
        terminfo = os.path.join(package_root, "share", "terminfo")
        environment.update(
            {"TERM": "xterm", "TERMINFO": terminfo, "TERMINFO_DIRS": terminfo}
        )
        self._capture([binary], environment)
        self.output.info(f"METADATA_{label.upper()}=3/3")

    def _test_metadata_interfaces(self, runtime_dir):
        package_root = os.path.realpath(
            str(self.dependencies["ncurses"].package_folder)
        )
        include_dir = os.path.join(package_root, "include")
        library_dir = os.path.join(package_root, "lib")
        terminfo_dir = os.path.join(package_root, "share", "terminfo")

        config = os.path.join(package_root, "bin", "ncursesw6-config")
        shell = shutil.which("bash") or shutil.which("sh")
        if shell is None:
            raise ConanException("a target shell is required for ncursesw6-config")
        config_command = [shell, config]
        if os.path.realpath(
            self._capture(config_command + ["--prefix"])
        ) != package_root:
            raise ConanException("ncursesw6-config returned a non-package prefix")
        for option, expected in (
            ("--includedir", include_dir),
            ("--libdir", library_dir),
            ("--terminfo", terminfo_dir),
        ):
            actual = os.path.realpath(self._capture(config_command + [option]))
            if actual != os.path.realpath(expected):
                raise ConanException(f"ncursesw6-config {option} escaped the package")
        config_cflags = self._capture(config_command + ["--cflags"])
        config_libs = self._capture(config_command + ["--libs"])
        self._require_path_flag(config_cflags, "-I", include_dir)
        self._require_path_flag(config_libs, "-L", library_dir)
        self._compile_metadata_consumer(
            "config",
            config_cflags,
            config_libs,
            runtime_dir,
            package_root,
            ("libncursesw.a",),
        )

        pkg_config = shutil.which("pkg-config")
        if pkg_config is None:
            raise ConanException(
                "pkg-config is required to validate installed .pc files"
            )
        pc_environment = os.environ.copy()
        pc_environment["PKG_CONFIG_PATH"] = ""
        pc_environment["PKG_CONFIG_LIBDIR"] = os.path.join(
            package_root, "lib", "pkgconfig"
        )
        pc_environment.pop("PKG_CONFIG_SYSROOT_DIR", None)
        modules = (
            (
                "formw",
                "formw",
                ("libformw.a", "libncursesw.a"),
                "test_metadata.c",
                "c",
                ("NCURSES_METADATA_FORMW=1",),
            ),
            (
                "menuw",
                "menuw",
                ("libmenuw.a", "libncursesw.a"),
                "test_metadata.c",
                "c",
                ("NCURSES_METADATA_MENUW=1",),
            ),
            (
                "ncursesxxw",
                "ncurses++w",
                ("libncurses++w.a", "libncursesw.a"),
                "test_metadata_cpp.cpp",
                "c++",
                (),
            ),
            (
                "ncursesw",
                "ncursesw",
                ("libncursesw.a",),
                "test_metadata.c",
                "c",
                (),
            ),
            (
                "panelw",
                "panelw",
                ("libpanelw.a", "libncursesw.a"),
                "test_metadata.c",
                "c",
                ("NCURSES_METADATA_PANELW=1",),
            ),
        )
        for (
            label,
            module,
            required_archives,
            source_name,
            language,
            definitions,
        ) in modules:
            pc_prefix = self._capture(
                [pkg_config, "--variable=prefix", module], pc_environment
            )
            if os.path.realpath(pc_prefix) != package_root:
                raise ConanException(
                    f"pkg-config {module} returned a non-package prefix"
                )
            pc_cflags = self._capture(
                [pkg_config, "--cflags", module], pc_environment
            )
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
