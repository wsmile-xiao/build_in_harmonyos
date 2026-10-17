#!/usr/bin/env python3
"""Conan recipe for wmnd 0.4.18 — Window Maker Network Devices (X11 dockapp).

wmnd is a network-interface traffic monitor written for Window Maker and any
other window manager that handles dock windows.  It ships a pre-generated
Autotools ``configure`` plus an in-tree driver framework: the driver used on
HarmonyOS is ``linux_proc`` (selected by ``configure`` through
``AC_CHECK_FILE(/proc/net/dev)``), with ``testing_dummy`` kept as the upstream
fallback driver.

OHOS specifics handled here:

* ``config.guess``/``config.sub`` do not know HarmonyOS (``uname -s`` returns
  ``HarmonyOS``, kernel ``HongMeng Kernel``), so ``configure`` aborts with
  "unable to guess system type".  ``patches/`` maps the platform onto the
  ``aarch64-unknown-linux-ohos`` triplet that the OHOS clang target uses.
* The dependency libraries are shared, so ``configure`` runtime probes
  (``AC_CHECK_SIZEOF``) only succeed when the consumers' ``lib`` directories are
  on ``LD_LIBRARY_PATH``; the toolchain environment below provides that.
  Without it ``config.h`` silently records ``SIZEOF_UNSIGNED_LONG 0``.
* HarmonyOS only loads an ELF from the Conan package cache when it carries an
  ``.codesign`` section, so the installed executable is self-signed in
  ``package()``.
* HMDFS (the filesystem backing the default ``~/.conan2`` on HarmonyOS PC)
  cannot be used to build Autotools recipes: the Conan client runs in the
  SELinux domain ``adhoc_bin``, which the platform forbids from executing any
  file on a user-writable mount, so ``./configure`` dies with ``Permission
  denied`` (exit 126) no matter what mode the helper scripts carry.  Building
  therefore needs ``CONAN_HOME`` on a non-HMDFS filesystem; the recipe keeps
  the E490 helper-script mitigation anyway because it does help on the normal
  filesystems the CI uses.
* The generated ``configure`` creates the private config.status temp dir with
  ``umask 077``.  On the CI worker's HMDFS build tree the setgid bit is forced
  onto that directory and the owner uid is remapped, so the 0700 directory
  ends up unwritable even for its own owner and config.status dies with
  "can't create ./confXXXXXX/subs1.awk: Permission denied"
  (E011/E114/E129 — same root cause as wmtop 0.85).  The generated script is
  rewritten to ``umask 022`` before it runs; this is the only viable remedy
  because autoconf 2.71 hardcodes the relative ``mktemp -d "./confXXXXXX"``
  and ignores ``TMPDIR`` here.

Upstream 0.4.18 has no automated test suite: ``Makefile.am`` and
``src/Makefile.am`` define only ``SUBDIRS``/``bin_PROGRAMS`` and ``make check``
reports "Nothing to be done for 'check'".  The consumer test therefore exercises
the installed executable itself (version, usage, headless driver initialisation
and the signed-ELF delivery condition).
"""

import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


# E011/E114/E129 (see the module docstring): the generated configure embeds
# "umask 077" when it creates the config.status private temp dir.  Rewritten
# to a group-accessible umask before the script runs.
_UMASK_INSECURE = "umask 077"
_UMASK_HMDFS_SAFE = "umask 022"


class WmndConan(ConanFile):
    name = "wmnd"
    version = "0.4.18"
    description = ("WMND — Window Maker network devices dockapp, a customizable "
                   "network interface traffic monitor")
    license = "GPL-2.0-or-later"
    homepage = "https://www.thregr.org/~wavexx/software/wmnd/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    # E490: Autotools helper scripts are programs, not data.  HarmonyOS PC
    # adaptation paths (HMDFS under ~/.conan2) can hand the extracted sources
    # over without an effective execute bit, and configure then dies with
    # "Permission denied" (exit 126) before anything is compiled.
    _AUTOTOOLS_HELPERS = (
        "configure",
        "config.guess",
        "config.sub",
        "install-sh",
        "missing",
        "compile",
        "depcomp",
        "ar-lib",
        "ltmain.sh",
        "test-driver",
        "ylwrap",
    )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Xlib, the shape extension and Xpm are linked by the upstream
        # configure checks (AC_HAVE_LIBRARY X11/Xext/Xpm).  libxpm and libxext
        # both sit on the cmd-pkgs ABI track, which forces libx11/6.4.0.
        self.requires("libx11/6.4.0", transitive_headers=True, transitive_libs=True)
        self.requires("libxext/6.4.0", transitive_headers=True, transitive_libs=True)
        self.requires("libxpm/3.5.17", transitive_headers=True, transitive_libs=True)
        self.requires("xorgproto/2025.1", transitive_headers=True)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"wmnd is only adapted for Linux/OHOS, got {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        toolchain = AutotoolsToolchain(self)
        environment = toolchain.environment()

        # ``AutotoolsToolchain`` forwards the dependencies' defines but neither
        # their include nor their library directories, so configure would not
        # see the X11 stack and ``AC_HAVE_LIBRARY(X11)`` would abort with
        # "X11 library is required".  Both flag sets are therefore added
        # explicitly.
        #
        # The library directories are also put on LD_LIBRARY_PATH: configure
        # runs AC_CHECK_SIZEOF probes through those very libraries, and they are
        # shared objects outside the default loader path, so every probe would
        # otherwise exit 127 with "Error loading shared library libX11.so.6"
        # and silently record every detected size as 0.
        for dependency in self.dependencies.host.values():
            cpp_info = dependency.cpp_info.aggregated_components()
            include_flags = [
                "-I" + os.path.join(dependency.package_folder, include_dir)
                for include_dir in cpp_info.includedirs
            ]
            library_flags = [
                "-L" + os.path.join(dependency.package_folder, lib_dir)
                for lib_dir in cpp_info.libdirs
            ]
            if include_flags:
                environment.append("CPPFLAGS", include_flags, separator=" ")
            if library_flags:
                environment.append("LDFLAGS", library_flags, separator=" ")
            for lib_dir in cpp_info.libdirs:
                environment.append_path(
                    "LD_LIBRARY_PATH",
                    os.path.join(dependency.package_folder, lib_dir),
                )

        # Keep configure/make scratch space inside the Conan build folder.
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        environment.define_path("TMPDIR", tmpdir)
        environment.define_path("TMP", tmpdir)
        environment.define_path("TEMP", tmpdir)

        # The system sh is pinned here for the same reason as in
        # ``_pin_posix_config_shell``; that method re-pins the variables
        # after generate() because the profile buildenv is sourced *after*
        # the toolchain environment inside the aggregated conanbuild.sh.
        environment.define("CONFIG_SHELL", "/system/bin/sh")
        environment.define("SHELL", "/system/bin/sh")

        toolchain.generate(env=environment)

    def build(self):
        apply_conandata_patches(self)
        self._ensure_helper_exec_bits()
        self._fix_config_status_umask()
        self._pin_posix_config_shell()
        autotools = Autotools(self)
        autotools.configure()
        # A single job avoids make jobserver FIFO failures on HMDFS.
        autotools.make(args=["-j1"])
        # Upstream has no test suite: Makefile.am defines no TESTS or
        # check_PROGRAMS and `make check` prints "Nothing to be done".

    def _fix_config_status_umask(self):
        """E011/E114/E129 — see the module docstring.

        The generated ``configure`` embeds ``umask 077`` in the tmp-directory
        setup that config.status inherits.  On an HMDFS build tree the setgid
        bit is forced onto that 0700 directory and the owner uid is remapped,
        making it unwritable even for its own owner, so config.status dies
        with "can't create ./confXXXXXX/subs1.awk: Permission denied" before
        any file machinery is set up.  autoconf 2.71 hardcodes the relative
        ``mktemp -d "./confXXXXXX"`` (``TMPDIR`` is ignored), so rewriting the
        umask in the generated script is the only workable mitigation.  Both
        occurrences (the ``mktemp`` fast path and the ``mkdir`` fallback) are
        rewritten; the generated config.status inherits the fix because
        configure emits it at runtime.
        """
        candidates = []
        for folder in (self.source_folder, self.build_folder):
            if folder:
                candidates.append(os.path.join(folder, "configure"))
        rewritten_any = False
        for path in sorted(set(candidates)):
            if not os.path.isfile(path):
                continue
            with open(path, encoding="utf-8") as handle:
                content = handle.read()
            if _UMASK_INSECURE not in content:
                continue
            with open(path, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content.replace(_UMASK_INSECURE, _UMASK_HMDFS_SAFE))
            self.output.info(
                "configure: rewrote %d occurrence(s) of '%s' to '%s' "
                "(HMDFS/E011 config.status tmp dir)"
                % (
                    content.count(_UMASK_INSECURE),
                    _UMASK_INSECURE,
                    _UMASK_HMDFS_SAFE,
                )
            )
            rewritten_any = True
        if not rewritten_any:
            raise ConanException(
                "no configure script with '%s' found; the HMDFS config.status "
                "workaround has to be revisited" % _UMASK_INSECURE
            )

    def _pin_posix_config_shell(self):
        """Pin CONFIG_SHELL/SHELL to the system sh before configure.

        The CI profile's buildenv pins both variables to
        /data/service/hnp/bin/bash, whose behaviour inside an HMDFS build
        tree is unreliable (documented getcwd/relative-path limitations,
        E431).  The system sh is what configure itself runs as (its
        shebang), so re-pinning keeps config.status on the same, better
        tested interpreter.  Conan composes the aggregated conanbuild.sh by
        sourcing the toolchain environment *before* the profile buildenv,
        so a toolchain-level definition is overridden and the variables
        must be re-pinned directly inside the generated buildenv scripts.
        Note: this does NOT address the config.status "Permission denied"
        failure — that is the umask 077/HMDFS issue handled by
        ``_fix_config_status_umask``.
        """
        generators = self.generators_folder
        if not generators or not os.path.isdir(generators):
            return
        for name in sorted(os.listdir(generators)):
            if not (name.startswith("conanbuildenv") and name.endswith(".sh")):
                continue
            path = os.path.join(generators, name)
            with open(path, "r", encoding="utf-8") as handle:
                lines = handle.readlines()
            changed = False
            for index, line in enumerate(lines):
                stripped = line.strip()
                for variable in ("CONFIG_SHELL", "SHELL"):
                    prefix = f'export {variable}="'
                    if stripped.startswith(prefix) and stripped.endswith('"'):
                        value = stripped[len(prefix):-1]
                        if value != "/system/bin/sh":
                            lines[index] = f'export {variable}="/system/bin/sh"\n'
                            changed = True
            if changed:
                with open(path, "w", encoding="utf-8") as handle:
                    handle.writelines(lines)

    def _ensure_helper_exec_bits(self):
        """E490 — restore the execute bit on the Autotools helper scripts.

        Some HarmonyOS PC adaptation paths hand the extracted sources over
        without a usable mode, so ``configure`` would abort with ``Permission
        denied`` before anything is compiled.  Only the known helper scripts
        are touched, and scripts that already carry the world-execute bit are
        left alone.

        Measured limitation: this mitigation cannot help while the Conan cache
        lives on HMDFS.  There ``chmod()`` is ignored (E046) and, more
        fundamentally, the Conan client runs in the SELinux domain
        ``adhoc_bin``, which the platform forbids from executing *any* file on
        a user-writable HMDFS mount — including a script the recipe had just
        created and chmod-ed itself (verified: EACCES even for a private
        ``0o755`` probe script).  ``conan create`` for Autotools recipes must
        therefore run with ``CONAN_HOME`` on a non-HMDFS filesystem.
        """
        normalised = []
        for root, _dirs, files in os.walk(self.source_folder):
            for name in files:
                if name not in self._AUTOTOOLS_HELPERS:
                    continue
                path = os.path.join(root, name)
                if os.path.islink(path) or os.stat(path).st_mode & 0o001:
                    continue
                os.chmod(path, os.stat(path).st_mode | 0o111)
                normalised.append(os.path.relpath(path, self.source_folder))
        if normalised:
            self.output.info(
                "E490: normalised execute bit on helper scripts: "
                + ", ".join(sorted(normalised))
            )

    def package(self):
        Autotools(self).install()
        if self.settings.os == "OHOS":
            self._sign_ohos_elf(os.path.join(self.package_folder, "bin", "wmnd"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )

    @staticmethod
    def _sign_ohos_elf(path):
        """Self-sign the packaged executable (HarmonyOS refuses unsigned ELF)."""
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        readelf = shutil.which("llvm-readelf") or "/data/service/hnp/bin/llvm-readelf"
        if not os.path.isfile(path):
            raise ConanException(f"Missing packaged executable: {path}")
        if not os.path.isfile(signer) or not os.path.isfile(readelf):
            raise ConanException("Required OHOS signing tools are missing")
        output = path + ".signed"
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", output, "-selfSign", "1"],
            check=True,
            timeout=60,
        )
        sections = subprocess.run(
            [readelf, "-SW", output],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        if sections.count(".codesign") != 1:
            raise ConanException("Signed packaged executable has invalid .codesign count")
        os.chmod(output, (os.stat(path).st_mode & 0o777) | 0o055)
        os.replace(output, path)
