#!/usr/bin/env python3
"""Conan recipe for tmate 2.4.0 — terminal multiplexer (tmux fork) with SSH sharing.

Autotools (configure + make).  GitHub tag 2.4.0 tarball does not ship generated
autotools files; 0001-0010 conandata patches add configure.ac probe alignment
(msgpack-c / ncursesw, matching ohpcd pkg-config names) plus pre-generated
configure / Makefile.in / aclocal.m4 / etc aux scripts with HarmonyOS-aware
config.guess.

Dependencies (all published on ohpcd, consumable per dependency analysis):
  - libevent/2.1.13   (pkg-config `libevent`)
  - ncurses/6.6       (pkg-config `ncursesw`, --enable-widec static build)
  - msgpack-c/7.0.0   (pkg-config `msgpack-c`, satisfies upstream msgpack >= 1.1.0)
  - libssh/0.11.4     (pkg-config `libssh`, satisfies upstream libssh >= 0.8.4;
                       transitive openssl/1.1.1w + zlib/1.3.1)
libutempter is OPTIONAL upstream (guarded by HAVE_UTEMPTER) and is not published
on ohpcd; it is kept disabled (no utmp records) — not a build blocker.
"""

import hashlib
import os
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
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps


class TmateConan(ConanFile):
    name = "tmate"
    version = "2.4.0"
    description = "Instant terminal sharing (tmux fork with SSH)"
    license = "ISC"
    homepage = "https://tmate.io/"
    url = "https://github.com/tmate-io/tmate"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    _ohos_data_root = "/data/storage/el2/base"
    _ohos_bash = "/data/service/hnp/bin/bash"

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"tmate supports Linux and OHOS, not {self.settings.os}"
            )
        if self.options.shared:
            raise ConanInvalidConfiguration(
                "tmate is packaged statically (R26: system libs static)"
            )

    def layout(self):
        self.folders.source = "src"
        self.folders.build = "build"
        self.folders.generators = "build-generators"

    def requirements(self):
        self.requires("libevent/2.1.13")
        self.requires("ncurses/6.6")
        self.requires("msgpack-c/7.0.0")
        self.requires("libssh/0.11.4")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(self._configure_args())
        tc.generate()
        PkgConfigDeps(self).generate()

    def _configure_args(self):
        args = [
            "--disable-silent-rules",
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
        autotools.make(args=["-j1", "SHELL=/bin/sh"])

    def _ohos_paths(self):
        build_key = hashlib.sha256(
            os.path.abspath(self.build_folder).encode("utf-8")
        ).hexdigest()[:12]
        root = os.path.join(
            self._ohos_data_root,
            f".conan-build-tmate-{self.version}-{build_key}",
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
            f".conan-build-tmate-{self.version}-",
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
            shlex_quote(value) for value in self._configure_args()
        )
        with self._ohos_environment(work, tmpdir):
            self._verify_ohos_tools()
            self.run(
                " ".join(
                    [
                        shlex_quote(self._ohos_bash),
                        shlex_quote(configure),
                        configure_args,
                    ]
                ),
                cwd=work,
                env=None,
            )
            self.run("make -j1 SHELL=/bin/sh", cwd=work, env=None)
            self.run(
                f"make -j1 SHELL=/bin/sh DESTDIR={shlex_quote(stage)} install",
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
        tools = ["sed", "rm", "expr", "make", "gawk", "clang", "clang++", "pkg-config"]
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

        self._validate_package()

    def _validate_package(self):
        binary = Path(self.package_folder) / "bin" / "tmate"
        if not binary.is_file():
            raise ConanException(f"tmate binary is missing: {binary}")
        unexpected = sorted(
            path.name
            for path in Path(self.package_folder).iterdir()
            if path.name not in {"bin", "share", "etc"}
        )
        if unexpected:
            raise ConanException(
                "unexpected package root entries: " + ", ".join(unexpected)
            )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]


def shlex_quote(value: str) -> str:
    """Minimal POSIX single-quote wrapper (avoids importing shlex at runtime)."""
    return "'" + value.replace("'", "'\\''") + "'"
