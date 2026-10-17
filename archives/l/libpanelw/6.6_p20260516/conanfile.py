#!/usr/bin/env python3
"""Conan recipe - libpanelw 6.6_p20260516 (ncurses panel split package, static wide build)."""

import hashlib
import os
import shlex
import shutil
from contextlib import contextmanager
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain


class LibpanelwConan(ConanFile):
    name = "libpanelw"
    version = "6.6_p20260516"
    description = "Panel overlap window management library (wide character) from the ncurses 6.6 snapshot 20260516"
    license = "X11"
    homepage = "https://invisible-island.net/ncurses/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    requires = "ncurses/6.6"

    _ohos_data_root = "/data/storage/el2/base"
    _ohos_bash = "/data/service/hnp/bin/bash"
    _pkgconfig_files = ("panelw.pc",)
    _package_libraries = ("libpanelw.a",)

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libpanelw supports Linux and OHOS, not {self.settings.os}"
            )
        if self.options.shared:
            raise ConanInvalidConfiguration(
                "libpanelw is packaged statically to avoid shadowing the system"
                " libpanelw shared library and the platform libncursesw.so.6"
            )

    def layout(self):
        # The ncurses build tree supports VPATH builds, but in-source construction
        # avoids embedding HMDFS absolute paths in generated dependency rules.
        self.folders.source = "src"
        self.folders.build = "src"
        self.folders.generators = "build-generators"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(self._configure_args())
        tc.generate()

    def build(self):
        if self.settings.os == "OHOS":
            self._build_ohos()
            return

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1", "SHELL=/bin/sh"])
        self._verify_upstream_programs(Path(self.build_folder))
        autotools.make(target="check", args=["-j1", "SHELL=/bin/sh"])

    def _configure_args(self):
        args = [
            "--disable-shared",
            "--enable-static",
            "--without-shared",
            "--with-normal",
            "--without-debug",
            "--with-trace",
            "--without-ada",
            "--without-manpages",
            "--enable-widec",
            "--enable-overwrite",
            "--enable-pc-files",
        ]
        if self.settings.os == "OHOS":
            args.extend(
                ["--prefix=/", "--with-pkg-config-libdir=/lib/pkgconfig"]
            )
        return args

    def _ohos_paths(self):
        build_key = hashlib.sha256(
            os.path.abspath(self.build_folder).encode("utf-8")
        ).hexdigest()[:12]
        root = os.path.join(
            self._ohos_data_root,
            f".conan-build-libpanelw-{self.version}-{build_key}",
        )
        return (
            root,
            os.path.join(root, "src"),
            os.path.join(root, "stage"),
            os.path.join(root, "tmp"),
        )

    def _reset_ohos_root(self, root):
        expected_prefix = os.path.join(
            self._ohos_data_root,
            f".conan-build-libpanelw-{self.version}-",
        )
        if not root.startswith(expected_prefix):
            raise ConanException(f"refusing to reset unexpected build root: {root}")
        if os.path.lexists(root):
            if os.path.islink(root):
                os.unlink(root)
            else:
                shutil.rmtree(root)
        os.makedirs(root)

    def _build_ohos(self):
        root, work, stage, tmpdir = self._ohos_paths()
        self._reset_ohos_root(root)
        shutil.copytree(self.source_folder, work, symlinks=True)
        os.makedirs(stage)
        os.makedirs(tmpdir)

        configure = os.path.join(work, "configure")
        configure_args = " ".join(
            shlex.quote(value) for value in self._configure_args()
        )
        with self._ohos_environment(work, tmpdir):
            self._verify_ohos_tools()
            self.run(
                " ".join(
                    [
                        shlex.quote(self._ohos_bash),
                        shlex.quote(configure),
                        configure_args,
                    ]
                ),
                cwd=work,
                env=None,
            )
            self.run("make -j1 SHELL=/bin/sh", cwd=work, env=None)
            self._verify_upstream_programs(Path(work))
            self.run("make -j1 SHELL=/bin/sh check", cwd=work, env=None)
            self.run(
                f"make -j1 SHELL=/bin/sh DESTDIR={shlex.quote(stage)} install",
                cwd=work,
                env=None,
            )

    @contextmanager
    def _ohos_environment(self, work, tmpdir):
        environment = Environment()
        environment.define("TMPDIR", tmpdir)
        environment.define("TMP", tmpdir)
        environment.define("TEMP", tmpdir)
        environment.define("PWD", work)
        environment.define("CONFIG_SHELL", self._ohos_bash)
        environment.define("ac_cv_func_setfsuid", "no")
        environment.define(
            "PATH",
            "/data/service/hnp/bin:"
            "/storage/Users/currentUser/usr/local/bin:"
            "/system/bin:/bin:/usr/bin",
        )
        environment.compose_env(AutotoolsToolchain(self).environment())
        environment.compose_env(VirtualBuildEnv(self).environment())

        with environment.vars(self).apply():
            yield

    def _verify_ohos_tools(self):
        tools = ["sed", "rm", "expr", "make", "gawk", "clang", "clang++"]
        missing = [tool for tool in tools if shutil.which(tool) is None]
        if not os.path.isfile(self._ohos_bash):
            missing.append(self._ohos_bash)
        if missing:
            raise ConanException(
                "required OHOS build tools are missing: " + ", ".join(missing)
            )
        self.output.info(f"OHOS_BUILD_TOOLS={len(tools) + 1}/{len(tools) + 1}")

    def _verify_upstream_programs(self, build_root):
        programs_file = build_root / "test" / "programs"
        names = []
        for line in programs_file.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                names.append(stripped.split()[0])

        if len(names) != 86 or len(set(names)) != 86:
            raise ConanException(
                f"upstream test inventory changed: {len(names)}/86 program entries"
            )

        missing = [
            name
            for name in names
            if not (build_root / "test" / name).is_file()
        ]
        missing.append(
            ""
            if (build_root / "test" / "demo_panels").is_file()
            else "demo_panels"
        )
        missing = [name for name in missing if name]
        if missing:
            raise ConanException(
                "upstream test programs missing after build: " + ", ".join(missing)
            )
        self.output.info("UPSTREAM_TEST_PROGRAMS=86/86")

    def package(self):
        if self.settings.os == "OHOS":
            _root, _work, stage, _tmpdir = self._ohos_paths()
        else:
            stage = os.path.join(self.build_folder, "stage")
            shutil.rmtree(stage, ignore_errors=True)
            os.makedirs(stage)
            autotools = Autotools(self)
            autotools.install(
                args=["-j1", f"DESTDIR={shlex.quote(stage)}", "SHELL=/bin/sh"]
            )
        if not os.path.isdir(stage):
            raise ConanException(f"staging directory is missing: {stage}")

        self._copy_panel_artifacts(Path(stage))
        self._relocate_metadata()
        self._validate_package()

    def _copy_panel_artifacts(self, stage):
        stage_root = Path(stage)
        package_root = Path(self.package_folder)
        copies = [
            (stage_root / "include" / "panel.h", package_root / "include" / "panel.h"),
            (stage_root / "lib" / "libpanelw.a", package_root / "lib" / "libpanelw.a"),
            (
                stage_root / "lib" / "pkgconfig" / "panelw.pc",
                package_root / "lib" / "pkgconfig" / "panelw.pc",
            ),
        ]
        for source, destination in copies:
            if not source.is_file():
                raise ConanException(f"staged panel artifact is missing: {source}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)

    @staticmethod
    def _write_lf(path, lines):
        with path.open("w", encoding="utf-8", newline="\n") as stream:
            stream.write("\n".join(lines) + "\n")

    def _relocate_metadata(self):
        pc_dir = Path(self.package_folder) / "lib" / "pkgconfig"
        for name in self._pkgconfig_files:
            pc_file = pc_dir / name
            lines = pc_file.read_text(encoding="utf-8").splitlines()
            original = {}
            for line in lines:
                key, separator, value = line.partition("=")
                if separator and key in {"prefix", "exec_prefix", "libdir", "includedir"}:
                    original[key] = value
            if set(original) != {"prefix", "exec_prefix", "libdir", "includedir"}:
                raise ConanException(f"unexpected pkg-config metadata in {pc_file}")

            output = []
            for line in lines:
                key, separator, _value = line.partition("=")
                if separator and key == "prefix":
                    line = "prefix=${pcfiledir}/../.."
                elif separator and key == "exec_prefix":
                    line = "exec_prefix=${prefix}"
                elif separator and key == "libdir":
                    line = "libdir=${prefix}/lib"
                elif separator and key == "includedir":
                    line = "includedir=${prefix}/include"
                elif line.startswith(("Libs:", "Libs.private:", "Cflags:")):
                    field, _separator, flags = line.partition(":")
                    tokens = []
                    for token in shlex.split(flags):
                        if token.startswith("-L/"):
                            token = "-L${libdir}"
                        elif token.startswith("-I/"):
                            token = "-I${includedir}"
                        tokens.append(token)
                    line = f"{field}: {' '.join(tokens)}"
                else:
                    line = line.replace(
                        f"-I{original['includedir']}", "-I${includedir}"
                    ).replace(f"-L{original['libdir']}", "-L${libdir}")
                output.append(line)
            self._write_lf(pc_file, output)

    def _validate_package(self):
        package_root = Path(self.package_folder)
        unexpected = sorted(
            path.name
            for path in package_root.iterdir()
            if path.name not in {"include", "lib"}
        )
        if unexpected:
            raise ConanException(
                "unexpected package root entries: " + ", ".join(unexpected)
            )

        shared = []
        for pattern in ("*.so", "*.so.*"):
            shared.extend(Path(self.package_folder).rglob(pattern))
        if shared:
            raise ConanException(
                "static-only package contains shared libraries: "
                + ", ".join(str(path) for path in shared)
            )

        foreign = [
            str(path)
            for path in Path(self.package_folder).rglob("*.a")
            if path.name not in self._package_libraries
        ]
        if foreign:
            raise ConanException(
                "panel-only package must not bundle ncurses core artifacts: "
                + ", ".join(foreign)
            )

        required = [
            Path(self.package_folder) / "include" / "panel.h",
            Path(self.package_folder) / "lib" / "libpanelw.a",
            Path(self.package_folder) / "lib" / "pkgconfig" / "panelw.pc",
        ]
        missing = [str(path) for path in required if not path.exists()]
        if missing:
            raise ConanException(
                "required libpanelw package artifacts are missing: "
                + ", ".join(missing)
            )

        forbidden = (
            "//include",
            "//lib",
            os.path.abspath(self.package_folder),
        )
        for name in self._pkgconfig_files:
            path = Path(self.package_folder) / "lib" / "pkgconfig" / name
            content = path.read_text(encoding="utf-8")
            leaks = [value for value in forbidden if value in content]
            if leaks:
                raise ConanException(
                    f"non-relocatable paths remain in {path}: {', '.join(leaks)}"
                )

    def package_info(self):
        self.cpp_info.libs = ["panelw"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "libpanelw")
        self.cpp_info.set_property("cmake_target_name", "libpanelw::libpanelw")
        self.cpp_info.set_property("pkg_config_name", "panelw")
        # The panel core is provided by the ncurses package; consumers of this
        # split package always link the packaged libpanelw.a against ncursesw.
        self.cpp_info.requires = ["ncurses::ncurses"]
