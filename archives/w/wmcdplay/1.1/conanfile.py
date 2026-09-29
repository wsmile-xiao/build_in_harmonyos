#!/usr/bin/env python3
"""Conan recipe for wmcdplay 1.1.

wmcdplay is the Window Maker dockapp CD player (an ascd derivative).  It is an
X11 client executable: the artwork is compiled into the binary through
``#include "XPM/standard.art"`` and the CD device is driven with Linux
``<linux/cdrom.h>`` ioctls.

The upstream release tarball ships ``configure.ac``/``Makefile.am`` only -- no
generated ``configure`` and no ``Makefile.in`` -- so ``build()`` bootstraps
autotools before running the canonical configure/make/check/install sequence.
The build is intentionally performed in-source: the artwork rules in
``Makefile.am`` (``XPM/%.art: cd XPM && ./makeart $*``) address paths relative
to the current directory, so an out-of-source build cannot work unpatched, and
upstream documents the in-source flow (``autoreconf -i && ./configure && make``).
"""

import os
import shlex
import shutil
import stat
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class WmcdplayConan(ConanFile):
    name = "wmcdplay"
    version = "1.1"
    description = "CD player dockapp based on ascd, designed for Window Maker"
    license = "GPL-2.0-or-later"
    homepage = "https://www.dockapps.net/"
    url = "https://www.dockapps.net/"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Keep the whole X11 graph on the published 6.4.0 track: libx11's
        # x11.pc is installed with prefix=/ and is not relocatable, so the
        # include/lib paths have to come from cpp_info (AutotoolsDeps) while
        # staying on the same revision family the rest of the X11 packages use.
        self.requires(
            "libx11/6.4.0",
            force=True,
            transitive_headers=True,
            transitive_libs=True,
        )
        self.requires("libxext/6.4.0", transitive_headers=True, transitive_libs=True)
        self.requires("libxpm/3.5.17", transitive_headers=True, transitive_libs=True)

    def build_requirements(self):
        # The release has no configure/Makefile.in, so aclocal/automake must run.
        # The OHOS image ships the autoconf family but no automake/aclocal, hence
        # the tool_requires (same pattern as the abiword plugin recipes).
        self.tool_requires("automake/1.18")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"wmcdplay needs a POSIX X11 platform, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def generate(self):
        # tool_requires(automake) exports ACLOCAL/AUTOMAKE/ACLOCAL_PATH/PERL5LIB
        # only through the conanbuild environment, so it must be materialised.
        VirtualBuildEnv(self).generate()
        PkgConfigDeps(self).generate()
        AutotoolsDeps(self).generate()
        self._toolchain = AutotoolsToolchain(self, prefix="/")
        if str(self.settings.os) == "OHOS":
            # HarmonyOS is not recognised by the automake-shipped config.guess,
            # so the target triplet is stated explicitly.  Declaring it also
            # puts configure into cross-compiling mode, where the compiler
            # works-check only links and never runs the OHOS conftest binary.
            self._toolchain.configure_args.append("--host=aarch64-linux-ohos")
        self._toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        with self._build_environment().vars(self).apply():
            self._bootstrap_autotools()
            self._harden_config_status_tmpdir()
            self._restore_autotools_script_modes()
            self._configure()
            self._run_build("make -j1")
            # The release declares neither TESTS nor check_PROGRAMS, so this is
            # the canonical (empty) upstream test target; it is still executed
            # to prove the test entry point is intact.
            self._run_build("make -j1 check")

    def package(self):
        with self._build_environment().vars(self).apply():
            destination = shlex.quote(self.package_folder)
            self._run_build(f"make -j1 install DESTDIR={destination}")
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        self._normalise_installed_permissions()
        if str(self.settings.os) == "OHOS":
            binary = Path(self.package_folder, "bin", "wmcdplay")
            if not binary.is_file():
                raise ConanException("the installed wmcdplay binary is missing")
            self._drop_build_rpath(binary)
            self._sign_ohos_elf(binary)

    def package_info(self):
        # Command-line tool: nothing to link against, but the executable must be
        # exported on PATH for the consumer test and for downstream use.
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
        self.cpp_info.set_property("cmake_file_name", "wmcdplay")
        self.cpp_info.set_property("cmake_target_name", "wmcdplay::wmcdplay")

    # ── build helpers ────────────────────────────────────────────────────

    def _build_shell(self):
        return "/system/bin/sh" if str(self.settings.os) == "OHOS" else "/bin/sh"

    def _run_build(self, command):
        shell = self._build_shell()
        self.run(
            f"export SHELL={shell} CONFIG_SHELL={shell}; {command}",
            cwd=self.source_folder,
            env="conanbuild",
        )

    def _build_environment(self):
        temporary = Path(self.build_folder, ".tmp")
        temporary.mkdir(parents=True, exist_ok=True)
        environment = Environment()
        environment.define_path("TMPDIR", str(temporary))
        environment.define("MKDIR_P", "/system/bin/mkdir -p")
        return environment

    def _bootstrap_autotools(self):
        """Generate configure/Makefile.in from configure.ac/Makefile.am.

        ``autoreconf`` is deliberately not used: on OHOS its m4 cache chain
        (``autoconf.m4f``) resolves to a different autoconf than the one on
        PATH and the core ``AM_*``/``AC_*`` macros are then reported as
        undefined.  Driving aclocal/autoconf/automake individually is
        equivalent and deterministic.  ``autoheader`` is unnecessary because
        configure.ac declares no ``AC_CONFIG_HEADERS``.

        ``aclocal``/``automake`` are addressed through the ``$ACLOCAL`` and
        ``$AUTOMAKE`` variables exported by ``automake/1.18`` rather than by
        bare name.  Those wrappers derive ``--automake-acdir``,
        ``--system-acdir`` and ``--libdir`` from their own location, so the
        absolute path the package exports is what keeps the bundled aclocal
        data reachable; invoking them by name is what made the first build fail
        with ``aclocal: Permission denied``.  This follows the abiword plugin
        recipes.  ``autoconf`` itself comes from the image
        (``/data/service/hnp/bin/autoconf``, already first on the build PATH).
        """
        self._run_build('"${ACLOCAL:-aclocal}" --force')
        self._run_build("autoconf -o configure configure.ac")
        self._run_build('"${AUTOMAKE:-automake}" --add-missing --copy')
        for generated in ("configure", "Makefile.in"):
            if not os.path.isfile(os.path.join(self.source_folder, generated)):
                raise ConanException(
                    f"autotools bootstrap did not produce {generated}"
                )

    def _harden_config_status_tmpdir(self):
        """Replace ``mktemp -d`` in the generated config.status temp-dir logic.

        autoconf 2.72 (shipped by the ``automake/1.18`` tool requirement) makes
        the generated ``config.status`` create its scratch directory with
        ``mktemp -d`` (forced mode 0700).  On HMDFS/FUSE build folders the
        resulting directory is not writable by build subprocesses, which aborts
        the build with ``can't create ./confXXXXXX/subs1.awk: Permission
        denied``.  Replace the ``mktemp -d`` line with a plain ``mkdir``
        (mode 0755), following the upstream-proven pattern first established
        for ``archives/4/4ti2/1.6.10``.
        """
        configure = os.path.join(self.source_folder, "configure")
        with open(configure, "r", encoding="utf-8", errors="ignore") as handle:
            text = handle.read()
        old = (
            'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&\n'
            '  test -d "$tmp"'
        )
        new = (
            'tmp="./conf$$-$RANDOM"\n'
            '  (mkdir "$tmp" 2>/dev/null)\n'
            '  test -d "$tmp"'
        )
        if old not in text:
            self.output.warning(
                "config.status tmpdir pattern not found in configure; leaving it untouched"
            )
            return
        with open(configure, "w", encoding="utf-8") as handle:
            handle.write(text.replace(old, new))
        self.output.info(
            "hardened config.status tmpdir creation (mktemp 0700 -> mkdir 0755)"
        )

    def _restore_autotools_script_modes(self):
        """Restore POSIX execute bits on the generated Autotools helpers (E490).

        Some HarmonyOS PC adaptation paths preserve file content but not the
        POSIX execute mode bits, and the build drives several helper scripts
        directly (``./install-sh`` and ``./depcomp`` from ``make install``,
        ``./missing`` from automake rules, and upstream's ``./XPM/makeart``
        from the artwork pattern rules).  A missing bit surfaces as
        ``Permission denied`` before any compilation happens, so the known
        helpers are chmod'ed right after the bootstrap produced them.
        """
        known = {
            "configure", "config.guess", "config.sub", "install-sh",
            "missing", "depcomp", "compile", "ylwrap", "test-driver",
        }
        restored = []
        for path in Path(self.source_folder).rglob("*"):
            if not path.is_file() or path.is_symlink():
                continue
            if path.name in known or path.name == "makeart":
                mode = path.stat().st_mode
                os.chmod(
                    path,
                    mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH,
                )
                restored.append(path.relative_to(self.source_folder).as_posix())
        if restored:
            self.output.info(
                "  restored execute bits on: " + " ".join(sorted(restored))
            )

    def _configure(self):
        arguments = " ".join(
            shlex.quote(argument) for argument in self._toolchain.configure_args
        )
        self._run_build(f"{self._build_shell()} ./configure {arguments}")

    # ── OHOS packaging helpers ───────────────────────────────────────────

    def _normalise_installed_permissions(self):
        """HMDFS ignores chmod on some mounts, so re-apply the exec bits.

        Without this the installed ``bin/wmcdplay`` (and the ``makeart`` helper
        script) can end up non-executable, which would silently turn the CI
        smoke test into a skip.
        """
        binary = Path(self.package_folder, "bin", "wmcdplay")
        if binary.is_file():
            os.chmod(binary, 0o755)
        helper = Path(self.package_folder, "share", "wmcdplay", "makeart")
        if helper.is_file():
            os.chmod(helper, 0o755)

    def _drop_build_rpath(self, binary):
        """Replace the task-local dependency search path with the run env.

        Conan injects ``-Wl,-rpath`` for the shared X11 dependencies, which
        would pin the published binary to this machine's cache layout.  The
        consumer resolves the libraries through ``conanrun``/``LD_LIBRARY_PATH``
        instead.
        """
        patchelf = shutil.which("patchelf") or "/data/service/hnp/bin/patchelf"
        readelf = shutil.which("llvm-readelf") or "/data/service/hnp/bin/llvm-readelf"
        for tool in (patchelf, readelf):
            if not os.path.isfile(tool):
                raise ConanInvalidConfiguration(
                    f"OHOS packaging requires the tool {tool}"
                )

        def dynamic_section():
            return subprocess.run(
                [readelf, "-d", str(binary)],
                check=True,
                capture_output=True,
                text=True,
                timeout=60,
            ).stdout

        before = dynamic_section()
        if "(RPATH)" in before or "(RUNPATH)" in before:
            subprocess.run(
                [patchelf, "--remove-rpath", str(binary)],
                check=True,
                capture_output=True,
                text=True,
                timeout=120,
            )
        after = dynamic_section()
        if "(RPATH)" in after or "(RUNPATH)" in after:
            raise ConanException("the wmcdplay build rpath was not removed")

    def _sign_ohos_elf(self, binary):
        """Re-create the ELF signature after the ELF has been rewritten.

        Removing the rpath invalidates the signature the toolchain attached at
        link time, so the ``.codesign`` section is dropped and the binary is
        re-signed with the SDK self-signed tool.
        """
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        readelf = shutil.which("llvm-readelf") or "/data/service/hnp/bin/llvm-readelf"
        for tool in (objcopy, signer, readelf):
            if not os.path.isfile(tool):
                raise ConanInvalidConfiguration(
                    f"OHOS packaging requires the tool {tool}"
                )

        subprocess.run(
            [objcopy, "--remove-section", ".codesign", str(binary)],
            check=True,
            capture_output=True,
            text=True,
            timeout=120,
        )
        signed = Path(f"{binary}.signed")
        try:
            subprocess.run(
                [
                    signer,
                    "sign",
                    "-inFile",
                    str(binary),
                    "-outFile",
                    str(signed),
                    "-selfSign",
                    "1",
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=180,
            )
            if not signed.is_file():
                raise ConanException("binary-sign-tool produced no output")
            sections = subprocess.run(
                [readelf, "-SW", str(signed)],
                check=True,
                capture_output=True,
                text=True,
                timeout=60,
            ).stdout
            if sections.count(".codesign") != 1:
                raise ConanException("the signed wmcdplay has an invalid .codesign section")
            os.chmod(signed, 0o755)
            os.replace(signed, binary)
        finally:
            if signed.exists():
                signed.unlink()
