#!/usr/bin/env python3
"""Conan recipe — ncurses 6.4 (Autotools, static wide-character build).

Enforces R4/R26: ncurses must be built statically.  Shared ncurses libraries
can shadow the platform ``libncursesw.so.6`` and crash the system zsh.
"""

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
    version = "6.4"
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

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"ncurses supports Linux and OHOS, not {self.settings.os}"
            )
        if self.options.shared:
            raise ConanInvalidConfiguration(
                "ncurses is packaged statically to avoid shadowing "
                "the system libncursesw.so.6"
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
        autotools.make(target="check", args=["-j1", "SHELL=/bin/sh"])

    def _configure_args(self):
        # R4/R26: static-only build.  --without-shared is the ncurses-native
        # switch (equivalent to --disable-shared) and prevents any .so from
        # being produced, which would shadow the system libncursesw.so.6.
        args = [
            "--disable-shared",
            "--enable-static",
            "--without-shared",
            "--without-debug",
            "--without-ada",
            "--without-manpages",
            "--without-tests",
            "--without-cxx-binding",
            "--enable-widec",
            "--enable-overwrite",
        ]
        if self.settings.os == "OHOS":
            args.append("--prefix=/")
        else:
            args.append("--prefix=/")
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
            raise ConanException(
                f"refusing to reset unexpected build root: {root}"
            )
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

    def package(self):
        if self.settings.os == "OHOS":
            _root, _work, stage, _tmpdir = self._ohos_paths()
            if not os.path.isdir(stage):
                raise ConanException(
                    f"OHOS staging directory is missing: {stage}"
                )
            shutil.copytree(
                stage,
                self.package_folder,
                symlinks=False,
                dirs_exist_ok=True,
            )
        else:
            autotools = Autotools(self)
            autotools.install(args=["-j1", "SHELL=/bin/sh"])

        self._validate_package()

    def _validate_package(self):
        # R4/R26: verify no shared libraries leak into the package.
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
            Path(self.package_folder) / "lib" / "libpanelw.a",
            Path(self.package_folder) / "lib" / "libmenuw.a",
            Path(self.package_folder) / "lib" / "libformw.a",
            Path(self.package_folder) / "share" / "terminfo",
        ]
        missing = [str(path) for path in required if not path.exists()]
        if missing:
            raise ConanException(
                "required ncurses package artifacts are missing: "
                + ", ".join(missing)
            )

    def package_info(self):
        # Static link order: consumers first, core provider last.
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
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
