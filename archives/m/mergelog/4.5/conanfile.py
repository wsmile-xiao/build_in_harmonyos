#!/usr/bin/env python3
"""Conan recipe for mergelog 4.5.1.

mergelog is a small, fast C program that merges httpd log files written in
Common Log Format (CLF) from web servers behind round-robin DNS and emits a
single chronologically sorted stream to stdout. `zmergelog` is the sibling
binary that additionally handles gzipped log files via zlib.

The upstream release tarball ships no test suite and only a single source
file; the recipe builds it with the OHOS clang toolchain through the upstream
autotools Makefile (autoconf 2.13 era). Two Debian-packaged upstream bug-fix
patches (SCAN_OFFSET and link order) are applied so the resulting binaries
parse dates correctly and link against modern ld.lld.

Upstream: https://mergelog.sourceforge.net/  (Bertrand Demiddelaer)
Source tarball: Debian pool pristine-tar (PGP-signed .dsc), SHA-256 verified.
"""

import glob as _glob
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    save,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class MergelogConan(ConanFile):
    name = "mergelog"
    version = "4.5"
    description = (
        "Fast tool to merge and sort by date httpd log files in Common Log "
        "Format; ships mergelog (plain) and zmergelog (gzip-aware)."
    )
    license = "GPL-2.0-only"
    homepage = "https://mergelog.sourceforge.net/"
    url = ""  # CI fills this
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "mergelog is adapted for Linux and OHOS only"
            )
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "OHOS builds require armv8/aarch64"
            )

    def requirements(self):
        # mergelog/zmergelog link against zlib (AC_CHECK_LIB(z) in configure.in)
        self.requires("zlib/1.3.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        is_ohos = str(self.settings.os) == "OHOS"
        if is_ohos:
            triplet = self._ohos_triplet()
            tc.configure_args.extend([
                f"--build={triplet}",
                f"--host={triplet}",
            ])
        if is_ohos:
            # The shared OHOS profile pins CC/CXX/CONFIG_SHELL to a node-specific
            # prefix that is absent on some build workers, which would otherwise
            # fail configure's compiler probe and config.status's shell probe.
            # Override with PATH-discovered executables without mutating the
            # shared profile.
            env = tc.environment()
            shell = self._select_shell()
            env.define("CONFIG_SHELL", shell)
            env.define("SHELL", shell)
            for compiler, variable in (("c", "CC"), ("cpp", "CXX")):
                command = self._select_compiler_command(compiler)
                if command:
                    env.define(variable, command)
            for variable, candidates in (
                ("LD", ["ld.lld", "ld"]),
                ("AR", ["llvm-ar", "ar"]),
                ("RANLIB", ["llvm-ranlib", "ranlib"]),
                ("NM", ["llvm-nm", "nm"]),
            ):
                command = self._select_tool_command(candidates)
                if command:
                    env.define(variable, command)
            tc.generate(env=env)
        else:
            tc.generate()

    def build(self):
        apply_conandata_patches(self)
        self._stamp_generated_files_fresh()
        self._prepare_build_environment()
        # The 2.13-era configure cannot emit VPATH-aware Makefiles (no
        # srcdir/build-dir separation in src/Makefile.in), so configure/make
        # must run inside the source tree itself. basic_layout points
        # source_folder at the extracted tree; run everything there.
        os.chdir(self.source_folder)
        if str(self.settings.os) == "OHOS":
            # Run configure/make under the conanautotoolstoolchain env scope so
            # the CONFIG_SHELL/CC/AR overrides from generate() win over the
            # shared profile's node-specific paths (which are absent on some
            # build nodes). Autotools.configure() would instead inherit the
            # conanbuild scope and re-probe a broken shell into config.status.
            self._run_ohos(self._configure_command(), "OHOS configure")
            self._run_ohos("make -j1", "OHOS make all")
        else:
            autotools = Autotools(self)
            autotools.configure()
            autotools.make(args=["-j1"])
        # Upstream ships no test suite (no tests/ dir, Makefile `check` is the
        # empty autotools default `check-am: all-am`); see test_package/MANIFEST.yml
        # for the full evidence. Functional verification runs in test_package.

    def package(self):
        self._prepare_build_environment()
        os.chdir(self.source_folder)
        if str(self.settings.os) == "OHOS":
            # --prefix already points at package_folder, so a plain `make
            # install` lands binaries in <pkg>/bin. Passing DESTDIR=<pkg> on
            # top of that would double-nest to <pkg>/<pkg>/bin and the
            # declared bindirs would miss the binaries.
            self._run_ohos("make install", "OHOS make install")
        else:
            autotools = Autotools(self)
            autotools.install()
        # Drop libtool artifacts that this pure-binary package never produces.
        for _la in _glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(_la)

    def _stamp_generated_files_fresh(self):
        # The tarball ships pre-generated aclocal.m4 / configure / Makefile.in
        # (autoconf 2.13 era). Their Makefile regeneration rules re-invoke
        # automake when a source (.am/.in/.ac) is newer than its generated
        # counterpart, but modern automake then demands auxiliary scripts
        # (`compile`, `depcomp`) that the old tarball doesn't ship. Restamp the
        # generated files to be newer than their sources so make treats the
        # distributed Makefile.in/configure as current and skips regeneration
        # entirely — no automake, no missing aux files. This only changes file
        # mtimes in the copy of the source tree Conan made for this build; it
        # does not modify any upstream source content.
        src = self.source_folder
        sources = [
            os.path.join(src, "configure.in"),
            os.path.join(src, "Makefile.am"),
            os.path.join(src, "src", "Makefile.am"),
            os.path.join(src, "man", "Makefile.am"),
        ]
        generated = [
            os.path.join(src, "aclocal.m4"),
            os.path.join(src, "configure"),
            os.path.join(src, "Makefile.in"),
            os.path.join(src, "src", "Makefile.in"),
            os.path.join(src, "man", "Makefile.in"),
        ]
        import time
        for path in sources:
            if os.path.exists(path):
                os.utime(path, None)
        time.sleep(0.05)
        now = time.time()
        for path in generated:
            if os.path.exists(path):
                os.utime(path, (now, now))

    def _configure_command(self):
        configure = os.path.join(self.source_folder, "configure")
        args = [
            configure,
            f"--prefix={self.package_folder}",
            "--bindir=${prefix}/bin",
            "--sbindir=${prefix}/bin",
            "--libdir=${prefix}/lib",
            "--includedir=${prefix}/include",
            f"--build={self._ohos_triplet()}",
            f"--host={self._ohos_triplet()}",
        ]
        return shlex.join(args)

    def _run_ohos(self, command, description):
        self.run(command, env="conanautotoolstoolchain")

    def package_info(self):
        # Command-line tool: declare bindirs so consumers get the binaries on PATH.
        bindir = os.path.join(self.package_folder, "bin")
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        # zmergelog needs zlib at runtime via the musl dynamic linker.
        self.cpp_info.system_libs = ["z"]
        self.runenv_info.append_path("PATH", bindir)
        self.buildenv_info.append_path("PATH", bindir)

    # ── OHOS environment helpers (mirrors the m4 recipe's robustness) ──

    def _prepare_build_environment(self):
        if str(self.settings.os) != "OHOS":
            return
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir
        os.environ.setdefault("TMPPREFIX", os.path.join(tmpdir, "zsh"))
        shell = self._select_shell()
        os.environ["CONFIG_SHELL"] = shell
        os.environ["SHELL"] = shell

    def _select_shell(self):
        # Prefer CONFIG_SHELL/SHELL from the environment, then fall back to
        # standard, user-independent system shells. (The shared OHOS profile
        # pins CONFIG_SHELL to a node-specific path that is absent on some
        # build workers, so this list only contains portable fallbacks — no
        # hard-coded user/SDK paths.)
        for shell in (
            os.environ.get("CONFIG_SHELL"),
            os.environ.get("SHELL"),
            "/bin/bash",
            "/bin/sh",
            "/system/bin/sh",
        ):
            if not shell:
                continue
            if os.path.isabs(shell):
                if os.path.isfile(shell) and os.access(shell, os.X_OK):
                    return shell
            elif shutil.which(shell):
                return shell
        return "sh"

    def _select_compiler_command(self, compiler):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        command = compilers.get(compiler)
        if command and self._is_executable_path(command):
            return command
        # Fall back to a PATH-discovered clang for environments where the
        # profile's hard-coded prefix is absent.
        fallback = shutil.which("clang" if compiler == "c" else "clang++")
        return fallback or command

    def _select_tool_command(self, candidates):
        for candidate in candidates:
            command = shutil.which(candidate)
            if command:
                return command
        return candidates[0] if candidates else None

    @staticmethod
    def _is_executable_path(command):
        try:
            parts = shlex.split(command)
        except ValueError:
            return command and os.path.isfile(command)
        return bool(parts) and MergelogConan._is_executable(parts[0])

    @staticmethod
    def _is_executable(command):
        if os.path.isabs(command):
            return os.path.isfile(command) and os.access(command, os.X_OK)
        return shutil.which(command) is not None

    def _ohos_triplet(self):
        arch = str(self.settings.arch)
        cpu = {
            "armv8": "aarch64",
            "armv8.3": "aarch64",
            "x86_64": "x86_64",
        }.get(arch, arch)
        return f"{cpu}-unknown-linux-ohos"
