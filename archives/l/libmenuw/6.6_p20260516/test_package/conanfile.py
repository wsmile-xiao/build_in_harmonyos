#!/usr/bin/env python3
"""Consumer tests for the libmenuw split package and its ncurses core linkage."""

import os
import re
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class LibmenuwTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # The ncurses core is also a direct requirement here: menu.h pulls in
        # curses.h, and on the current CMakeDeps the include directories of a
        # purely transitive ncurses are not emitted, so the consumer compile
        # would lose the curses.h search path.
        self.requires("ncurses/6.6")

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
        binary = os.path.join(bindir, "test_menu_consumer")
        output_path = os.path.join(runtime_dir, "test_menu_consumer.out")
        self.run(
            f'"{binary}" "{output_path}" "{input_path}"',
            env="conanrun",
        )

        with open(output_path, encoding="utf-8") as stream:
            output = stream.read()
        if "MENU_CONSUMER_OK passed=16/16" not in output:
            raise ConanException(
                f"menu consumer assertions incomplete: {output!r}"
            )
        self.output.info("MENU_CONSUMER=16/16")

        self._test_pkgconfig_consumer(runtime_dir)

    def _test_pkgconfig_consumer(self, runtime_dir):
        menu_package = os.path.realpath(
            str(self.dependencies["libmenuw"].package_folder)
        )
        ncurses_package = os.path.realpath(
            str(self.dependencies["ncurses"].package_folder)
        )
        menu_lib = os.path.join(menu_package, "lib")
        ncurses_lib = os.path.join(ncurses_package, "lib")

        pkg_config = shutil.which("pkg-config")
        if pkg_config is None:
            raise ConanException(
                "pkg-config is required to validate installed .pc files"
            )
        pc_environment = os.environ.copy()
        pc_environment["PKG_CONFIG_PATH"] = ""
        pc_environment["PKG_CONFIG_LIBDIR"] = os.pathsep.join(
            [
                os.path.join(menu_package, "lib", "pkgconfig"),
                os.path.join(ncurses_package, "lib", "pkgconfig"),
            ]
        )
        pc_environment.pop("PKG_CONFIG_SYSROOT_DIR", None)

        def capture(arguments):
            result = subprocess.run(
                [pkg_config] + arguments,
                check=False,
                capture_output=True,
                text=True,
                env=pc_environment,
            )
            if result.returncode != 0:
                raise ConanException(
                    f"pkg-config {' '.join(arguments)} failed:"
                    f"{result.stdout}{result.stderr}"
                )
            return result.stdout.strip()

        if os.path.realpath(capture(["--variable=prefix", "menuw"])) != menu_package:
            raise ConanException("pkg-config menuw returned a non-package prefix")
        pc_cflags = capture(["--cflags", "menuw"])
        pc_libs = capture(["--static", "--libs", "menuw"])

        source = os.path.join(self.source_folder, "src", "test_menu_pkgconfig.c")
        binary = os.path.join(runtime_dir, "test_menu_pkgconfig")
        compiler = next(
            (path for path in map(shutil.which, ("clang", "cc")) if path),
            None,
        )
        if compiler is None:
            raise ConanException("no target C compiler is available for the metadata test")
        compiler_tmp = os.path.join(runtime_dir, "tmp-pkgconfig")
        os.makedirs(compiler_tmp, exist_ok=True)
        compiler_environment = os.environ.copy()
        compiler_environment.update(
            {"TMPDIR": compiler_tmp, "TMP": compiler_tmp, "TEMP": compiler_tmp}
        )
        command = (
            [compiler]
            + shlex.split(pc_cflags)
            + [source, "-o", binary, "-Wl,-t"]
            + shlex.split(pc_libs)
        )
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            env=compiler_environment,
        )
        trace = result.stdout + result.stderr
        if result.returncode != 0:
            raise ConanException(f"pkg-config consumer failed to link:\n{trace}")

        normalized_trace = trace.replace("\\", "/")
        menu_archive = os.path.realpath(os.path.join(menu_lib, "libmenuw.a"))
        ncurses_archive = os.path.realpath(
            os.path.join(ncurses_lib, "libncursesw.a")
        )
        # pkg-config emits ${pcfiledir}/../.. based paths and ld -t traces each
        # archive member as "libfoo.a(member.o)"; strip the member suffix and
        # canonicalize every traced archive token before comparing.
        def _archive_path(token):
            if "(" in token and token.endswith(")"):
                token = token[: token.index("(")]
            return os.path.realpath(token)

        traced_archives = {
            _archive_path(token)
            for line in normalized_trace.splitlines()
            for token in line.split()
            if ".a(" in token or token.endswith(".a")
        }
        if menu_archive not in traced_archives:
            raise ConanException(
                f"menuw link did not select {menu_archive}:\n{trace}"
            )
        if ncurses_archive not in traced_archives:
            raise ConanException(
                f"menuw link did not select the ncurses core {ncurses_archive}:\n{trace}"
            )
        if re.search(
            r"lib(?:ncurses[^/ ]*|panelw|formw|menuw|tinfo[^/ ]*)\.so",
            normalized_trace,
        ):
            raise ConanException(
                f"pkg-config consumer linked a shared curses library:\n{trace}"
            )
        self.output.info(
            f"PKGCONFIG_MENUW_LINKS={menu_archive},{ncurses_archive}"
        )

        terminfo = os.path.join(ncurses_package, "share", "terminfo")
        run_environment = os.environ.copy()
        run_environment.update(
            {"TERM": "xterm", "TERMINFO": terminfo, "TERMINFO_DIRS": terminfo}
        )
        result = subprocess.run(
            [binary],
            check=False,
            capture_output=True,
            text=True,
            env=run_environment,
        )
        if result.returncode != 0:
            raise ConanException(
                f"pkg-config menuw consumer failed at runtime: {result.stdout}{result.stderr}"
            )
        self.output.info("PKGCONFIG_MENUW_RUNTIME=ok")
