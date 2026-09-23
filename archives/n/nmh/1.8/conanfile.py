#!/usr/bin/env python3
"""Conan recipe - nmh 1.8 (Autotools mail user agent, ~40 CLI tools).

nmh is a classic Unix command-line mail user agent.  The package
builds and installs the whole command family (inc, scan, comp, repl,
refile, show, mhparam, ...) into bin/ together with libexec helpers
and etc configuration templates.

OHOS notes:
- sandboxed bash/clang cannot getcwd() inside the HMDFS-backed conan
  cache, so the source tree is copied to a real-fs work root under
  /data/storage/el2/base before configure/make run (same strategy as
  the ncurses/6.6 recipe).
- OHOS has no termcap/ncurses in the system; ncurses/6.6 provides
  libncursesw.a.  configure only probes -ltermcap/-ltinfo/-lcurses/
  -lncurses, so a private libncurses.a alias of the real archive is
  placed in a dedicated -L directory.
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
from conan.tools.gnu import AutotoolsToolchain


class NmhConan(ConanFile):
    name = "nmh"
    version = "1.8"
    description = "Classic Unix command-line mail user agent"
    license = "BSD-3-Clause"
    homepage = "https://www.nmh.io/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    _ohos_data_root = "/data/storage/el2/base"
    _ohos_bash = "/data/service/hnp/bin/bash"
    _triplet = "aarch64-unknown-linux-ohos"

    def export_sources(self):
        export_conandata_patches(self)
        shutil.copytree(
            os.path.join(self.recipe_folder, "ndbmcompat"),
            os.path.join(self.export_sources_folder, "ndbmcompat"),
        )

    def requirements(self):
        # Termlib is mandatory for nmh's configure (setupterm probe).
        self.requires("ncurses/6.6")
        # OHOS has no ndbm; gdbm backs the classic dbm API that
        # slocal(1) needs (see ndbmcompat/ndbm.h).
        self.requires("gdbm/1.24")

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"nmh supports Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        # Keep sources pristine in the conan cache; building happens on a
        # real-filesystem copy under /data (see _ohos_paths).
        self.folders.source = "src"
        self.folders.generators = "build-generators"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)
        # ndbmcompat/ndbm.h travels with the recipe sources and is copied
        # into the tree so configure/slocal can include it.
        shutil.copytree(
            os.path.join(self.export_sources_folder, "ndbmcompat"),
            os.path.join(self.source_folder, "ndbmcompat"),
        )

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()
        VirtualBuildEnv(self).generate()

    # ------------------------------------------------------------------
    # OHOS real-fs build helpers
    # ------------------------------------------------------------------

    def _ohos_paths(self):
        build_key = hashlib.sha256(
            os.path.abspath(self.build_folder).encode("utf-8")
        ).hexdigest()[:12]
        root = os.path.join(
            self._ohos_data_root,
            f".conan-build-nmh-{self.version}-{build_key}",
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
            f".conan-build-nmh-{self.version}-",
        )
        if not root.startswith(expected_prefix):
            raise ConanException(f"refusing to reset unexpected build root: {root}")
        if os.path.lexists(root):
            if os.path.islink(root):
                os.unlink(root)
            else:
                shutil.rmtree(root)
        os.makedirs(root)

    @contextmanager
    def _ohos_environment(self, work, tmpdir, ncurses_root, gdbm_root, tlib):
        environment = Environment()
        environment.define("TMPDIR", tmpdir)
        environment.define("TMP", tmpdir)
        environment.define("TEMP", tmpdir)
        environment.define("PWD", work)
        environment.define("CONFIG_SHELL", self._ohos_bash)
        environment.define(
            "CPPFLAGS",
            "-D_GNU_SOURCE "
            f"-I{os.path.join(work, 'ndbmcompat')} "
            f"-I{os.path.join(ncurses_root, 'include')} "
            f"-I{os.path.join(gdbm_root, 'include')}",
        )
        environment.define(
            "LDFLAGS",
            f"-L{tlib} "
            f"-L{os.path.join(ncurses_root, 'lib')} "
            f"-L{os.path.join(gdbm_root, 'lib')}",
        )
        environment.define("TERMINFO", os.path.join(ncurses_root, "share", "terminfo"))
        environment.define("TERMINFO_DIRS", os.path.join(ncurses_root, "share", "terminfo"))
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

    def _build_ohos(self):
        root, work, stage, tmpdir = self._ohos_paths()
        self._reset_ohos_root(root)
        shutil.copytree(self.source_folder, work, symlinks=True)
        os.makedirs(stage)
        os.makedirs(tmpdir)

        ncurses = self.dependencies["ncurses"]
        ncurses_root = ncurses.package_folder
        gdbm = self.dependencies["gdbm"]
        gdbm_root = gdbm.package_folder

        tlib = os.path.join(root, "termlib")
        os.makedirs(tlib)
        alias = os.path.join(tlib, "libncurses.a")
        if not os.path.exists(alias):
            shutil.copy2(
                os.path.join(ncurses_root, "lib", "libncursesw.a"), alias
            )

        configure = os.path.join(work, "configure")
        configure_args = " ".join(
            shlex.quote(value)
            for value in (
                f"--build={self._triplet}",
                f"--host={self._triplet}",
                "--prefix=/",
                "--without-cyrus-sasl",
            )
        )
        with self._ohos_environment(work, tmpdir, ncurses_root, gdbm_root, tlib):
            self.output.info("NMH_CONFIGURING_ON_OHOS_REAL_FS")
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
            self.output.info("NMH_MAKE_START")
            self.run(
                "make -j1 SHELL=/bin/sh",
                cwd=work,
                env=None,
            )
            self.output.info("NMH_INSTALL_START")
            self.run(
                "make -j1 SHELL=/bin/sh "
                f"DESTDIR={shlex.quote(stage)} install",
                cwd=work,
                env=None,
            )

    def build(self):
        if self.settings.os == "OHOS":
            self._build_ohos()
            return
        raise ConanException("nmh recipe currently targets OHOS only")

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

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libexecdirs = ["libexec"]
        self.cpp_info.set_property("cmake_file_name", "nmh")
        self.cpp_info.set_property("cmake_target_name", "nmh::nmh")
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "libexec", "nmh")
        )
