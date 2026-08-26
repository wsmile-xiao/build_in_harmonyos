#!/usr/bin/env python3
"""Conan recipe - dialog 1.3-20240307 (Autotools, static ncurses TUI library).

dialog is a TUI (Text User Interface) library and command-line tool built on
top of ncurses.  This recipe produces a static library (libdialog.a) and the
dialog executable, both statically linked against ncurses.
"""

import hashlib
import os
import shlex
import shutil
from contextlib import contextmanager

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain


class DialogConan(ConanFile):
    name = "dialog"
    version = "1.3-20240307"
    description = "Display dialog boxes from shell scripts (ncurses-based TUI)"
    license = "LGPL-2.1-only"
    homepage = "https://invisible-island.net/dialog/"
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
                f"dialog supports Linux and OHOS, not {self.settings.os}"
            )
        if self.options.shared:
            raise ConanInvalidConfiguration(
                "dialog is packaged statically to avoid shadowing system libraries"
            )

    def requirements(self):
        self.requires("ncurses/6.6")

    def layout(self):
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

    def _configure_args(self):
        args = [
            "--disable-shared",
            "--enable-static",
            "--with-ncurses",
        ]
        if self.settings.os == "OHOS":
            args.append("--prefix=/")
        return args

    def build(self):
        if self.settings.os == "OHOS":
            self._build_ohos()
            return

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def _ohos_paths(self):
        build_key = hashlib.sha256(
            os.path.abspath(self.build_folder).encode("utf-8")
        ).hexdigest()[:12]
        root = os.path.join(
            self._ohos_data_root,
            f".conan-build-dialog-{self.version}-{build_key}",
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
            f".conan-build-dialog-{self.version}-",
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

        # Create symlink libncurses.a -> libncursesw.a so that dialog's
        # configure (which looks for -lncurses) can find the wide-char lib.
        ncurses_pkg = self.dependencies["ncurses"].package_folder
        local_libs = os.path.join(root, "libs")
        os.makedirs(local_libs)
        src_lib = os.path.join(ncurses_pkg, "lib", "libncursesw.a")
        dst_lib = os.path.join(local_libs, "libncurses.a")
        if os.path.islink(dst_lib) or os.path.exists(dst_lib):
            os.remove(dst_lib)
        os.symlink(src_lib, dst_lib)

        configure = os.path.join(work, "configure")
        configure_args = " ".join(
            shlex.quote(v) for v in self._configure_args()
        )
        with self._ohos_environment(work, tmpdir, ncurses_pkg, local_libs):
            self._verify_ohos_tools()
            self.run(
                " ".join([
                    shlex.quote(self._ohos_bash),
                    shlex.quote(configure),
                    configure_args,
                    f"--with-curses-dir={shlex.quote(ncurses_pkg)}",
                ]),
                cwd=work,
                env=None,
            )
            self.run("make -j1", cwd=work, env=None)
            self.run("make -j1 check", cwd=work, env=None)
            self.run(
                f"make -j1 DESTDIR={shlex.quote(stage)} install-full",
                cwd=work,
                env=None,
            )

            # headers-sh fails on HMDFS (temp file issues); copy manually
            inc_dir = os.path.join(stage, "include")
            os.makedirs(inc_dir, exist_ok=True)
            for hdr in ("dialog.h", "dlg_colors.h", "dlg_keys.h"):
                src = os.path.join(work, hdr)
                if os.path.isfile(src):
                    shutil.copy2(src, os.path.join(inc_dir, hdr))
            # dlg_config.h is generated in the build dir
            cfg_hdr = os.path.join(work, "dlg_config.h")
            if os.path.isfile(cfg_hdr):
                shutil.copy2(cfg_hdr, os.path.join(inc_dir, "dlg_config.h"))

    @contextmanager
    def _ohos_environment(self, work, tmpdir, ncurses_pkg, local_libs):
        environment = Environment()
        environment.define("TMPDIR", tmpdir)
        environment.define("TMP", tmpdir)
        environment.define("TEMP", tmpdir)
        environment.define("PWD", work)
        environment.define("CONFIG_SHELL", self._ohos_bash)
        environment.define("SHELL", self._ohos_bash)
        environment.define("PATH",
            "/data/service/hnp/bin:"
            "/storage/Users/currentUser/usr/local/bin:"
            "/system/bin:/bin:/usr/bin",
        )
        environment.define("CPPFLAGS", f"-I{ncurses_pkg}/include")
        environment.define("LDFLAGS", f"-L{local_libs} -L{ncurses_pkg}/lib")
        environment.define("PKG_CONFIG_PATH",
            f"{ncurses_pkg}/lib/pkgconfig")
        environment.compose_env(AutotoolsToolchain(self).environment())
        environment.compose_env(VirtualBuildEnv(self).environment())

        with environment.vars(self).apply():
            yield

    def _verify_ohos_tools(self):
        tools = ["sed", "rm", "expr", "make", "clang", "clang++"]
        missing = [t for t in tools if shutil.which(t) is None]
        if not os.path.isfile(self._ohos_bash):
            missing.append(self._ohos_bash)
        if missing:
            raise ConanException(
                "required OHOS build tools missing: " + ", ".join(missing)
            )
        self.output.info(f"OHOS_BUILD_TOOLS={len(tools)+1}/{len(tools)+1}")

    def package(self):
        if self.settings.os == "OHOS":
            _root, _work, stage, _tmpdir = self._ohos_paths()
            if not os.path.isdir(stage):
                raise ConanException(f"OHOS staging dir missing: {stage}")
            shutil.copytree(
                stage, self.package_folder,
                symlinks=False, dirs_exist_ok=True,
            )
        else:
            autotools = Autotools(self)
            autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["dialog"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "dialog")
        self.cpp_info.set_property("cmake_target_name", "dialog::dialog")
        self.cpp_info.set_property("pkg_config_name", "dialog")
