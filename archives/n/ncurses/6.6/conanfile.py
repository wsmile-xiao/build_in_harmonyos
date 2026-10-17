#!/usr/bin/env python3
"""Conan recipe - ncurses 6.6 (Autotools, static wide-character build)."""

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


class NcursesConan(ConanFile):
    name = "ncurses"
    version = "6.6"
    description = "Terminal handling library with wide-character support"
    license = "X11"
    homepage = "https://invisible-island.net/ncurses/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    _ohos_data_root = "/data/storage/el2/base"
    _ohos_bash = "/data/service/hnp/bin/bash"
    _pkgconfig_files = (
        "formw.pc",
        "menuw.pc",
        "ncurses++w.pc",
        "ncursesw.pc",
        "panelw.pc",
    )

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"ncurses supports Linux and OHOS, not {self.settings.os}"
            )
        if self.options.shared:
            raise ConanInvalidConfiguration(
                "ncurses is packaged statically to avoid shadowing system libncursesw.so.6"
            )

    def layout(self):
        # ncurses supports VPATH builds, but in-source construction avoids
        # embedding HMDFS absolute paths in generated dependency rules.
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
            f".conan-build-ncurses-{self.version}-{build_key}",
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
            f".conan-build-ncurses-{self.version}-",
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
        if missing:
            raise ConanException(
                "upstream test programs missing after build: " + ", ".join(missing)
            )
        self.output.info("UPSTREAM_TEST_PROGRAMS=86/86")

    def package(self):
        if self.settings.os == "OHOS":
            _root, _work, stage, _tmpdir = self._ohos_paths()
            if not os.path.isdir(stage):
                raise ConanException(f"OHOS staging directory is missing: {stage}")
            shutil.copytree(
                stage,
                self.package_folder,
                symlinks=False,
                dirs_exist_ok=True,
            )
        else:
            autotools = Autotools(self)
            autotools.install(args=["-j1", "SHELL=/bin/sh"])
            self._copy_pkgconfig_files(Path(self.build_folder) / "misc")

        self._relocate_metadata()
        self._validate_package()

    def _copy_pkgconfig_files(self, source_dir):
        destination_dir = Path(self.package_folder) / "lib" / "pkgconfig"
        destination_dir.mkdir(parents=True, exist_ok=True)
        for name in self._pkgconfig_files:
            source = source_dir / name
            if not source.is_file():
                raise ConanException(f"generated pkg-config file is missing: {source}")
            shutil.copy2(source, destination_dir / name)

    @staticmethod
    def _write_lf(path, lines):
        with path.open("w", encoding="utf-8", newline="\n") as stream:
            stream.write("\n".join(lines) + "\n")

    def _relocate_metadata(self):
        config = Path(self.package_folder) / "bin" / "ncursesw6-config"
        if not config.is_file():
            raise ConanException(f"ncurses config script is missing: {config}")

        assignments = {
            "prefix=": 'prefix="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"',
            "exec_prefix=": 'exec_prefix="$prefix"',
            "bindir=": 'bindir="$prefix/bin"',
            "includedir=": 'includedir="$prefix/include"',
            "includesubdir=": 'includesubdir="$includedir"',
            "libdir=": 'libdir="$prefix/lib"',
            "datarootdir=": 'datarootdir="$prefix/share"',
            "datadir=": 'datadir="$prefix/share"',
            "mandir=": 'mandir="$prefix/share/man"',
            "RPATH_LIST=": 'RPATH_LIST=""',
        }
        replaced = set()
        location_case = None
        location_cases = {"--terminfo)", "--terminfo-dirs)", "--termpath)"}
        relocated = []
        for line in config.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            for key, value in assignments.items():
                if stripped.startswith(key):
                    indentation = line[: len(line) - len(line.lstrip())]
                    line = indentation + value
                    replaced.add(key)
                    break

            stripped = line.strip()
            if stripped in location_cases:
                location_case = stripped
            elif location_case and stripped.startswith("echo "):
                line = '\t\techo "${prefix}/share/terminfo"'
                location_case = None
            relocated.append(line)

        missing = sorted(set(assignments) - replaced)
        if missing or location_case is not None:
            raise ConanException(
                "cannot relocate ncurses config metadata: "
                + ", ".join(missing or [location_case])
            )
        self._write_lf(config, relocated)
        config.chmod(0o755)

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
            if path.name not in {"bin", "include", "lib", "share"}
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

        required = [
            Path(self.package_folder) / "include" / "curses.h",
            Path(self.package_folder) / "lib" / "libncursesw.a",
            Path(self.package_folder) / "share" / "terminfo",
        ]
        missing = [str(path) for path in required if not path.exists()]
        if missing:
            raise ConanException(
                "required ncurses package artifacts are missing: "
                + ", ".join(missing)
            )

        metadata = [Path(self.package_folder) / "bin" / "ncursesw6-config"]
        metadata.extend(
            Path(self.package_folder) / "lib" / "pkgconfig" / name
            for name in self._pkgconfig_files
        )
        forbidden = (
            "//include",
            "//lib",
            "//share/terminfo",
            os.path.abspath(self.package_folder),
        )
        for path in metadata:
            content = path.read_text(encoding="utf-8")
            leaks = [value for value in forbidden if value in content]
            if leaks:
                raise ConanException(
                    f"non-relocatable paths remain in {path}: {', '.join(leaks)}"
                )

    def package_info(self):
        # Static link order is consumers first, core provider last.
        self.cpp_info.libs = ["formw", "menuw", "panelw", "ncursesw"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
        self.cpp_info.set_property("cmake_file_name", "ncurses")
        self.cpp_info.set_property("cmake_target_name", "ncurses::ncurses")
        self.cpp_info.set_property("pkg_config_name", "ncursesw")

        terminfo = os.path.join(self.package_folder, "share", "terminfo")
        self.runenv_info.define_path("TERMINFO", terminfo)
        self.runenv_info.define_path("TERMINFO_DIRS", terminfo)
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
