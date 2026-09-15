#!/usr/bin/env python3
"""Conan recipe for dinit-shutdown 0.21.0 — system shutdown utilities of the dinit service manager.

`dinit-shutdown` is the shutdown half of dinit 0.21.0 (davmac314/dinit), packaged
separately the same way distributions split it (Alpine's `dinit-shutdown` subpackage,
Debian's dinit shutdown helpers). It ships the `dinit-shutdown` utility plus the
`dinit-halt`, `dinit-poweroff`, `dinit-reboot` and `dinit-soft-reboot` names that
upstream installs as symlinks to it. The service manager itself (`dinit`, `dinitctl`,
`dinit-check`, `dinit-monitor`) is not part of this package; at run time the utilities
talk to a dinit daemon over its control socket (`/var/run/dinitctl`, the upstream
default for non-Linux platforms, also used by the existing dinit 0.22.0 OHOS archive).

Upstream builds the utility from a single translation unit (`src/shutdown.cc`) and the
program derives its action from `argv[0]` (shutdown(8): the `halt`/`poweroff` names
have no special significance, the default action is power down; `-r` selects reboot,
`-s` soft reboot, `-h` halt, `-p` power off, `-k` kexec).

OHOS / HarmonyOS PC adaptation notes
------------------------------------
1. `--enable-shutdown --shutdown-prefix=dinit-`: upstream only builds the utility by
   default when `uname` reports Linux, and HarmonyOS PC reports "HarmonyOS", so
   configure would otherwise leave `BUILD_SHUTDOWN=no`. The `dinit-` name prefix
   matches the distribution-split names and keeps the `SHUTDOWN_PREFIX` compiled into
   `build/includes/mconfig.h` consistent with the installed file names — without it
   the `dinit-reboot` / `dinit-soft-reboot` names would no longer match the argv[0]
   dispatch table.
2. `--disable-strip`: HarmonyOS PC toolchain output carries a `.codesign` section;
   stripped binaries fail to load on this platform (exit 126).
3. `make ... SHUTDOWN_PREFIX=dinit-`: configure writes `SHUTDOWN_PREFIX='dinit-'`
   (single quotes included) into mconfig, so the generated make target name literally
   contains those quotes. Overriding the variable on the make command line keeps the
   target name clean; `mconfig.h` — and therefore the compiled-in prefix — is still
   generated from mconfig and stays `dinit-`.
4. Submission extraction skips the tarball's top-level `BUILD` documentation file.
   The release tarball contains both a `BUILD` file and a `build/` directory at its
   root. The workspace filesystem on HarmonyOS PC is case-insensitive (HMDFS folds
   case: `BUILD` and `build` resolve to the same directory entry), so Python's tarfile
   raises `FileExistsError` while creating `build/` and conan's `get()` fails before
   any build step runs. `BUILD` is plain build documentation that no build rule reads,
   so it is excluded from extraction; every other member is unpacked verbatim. The
   exclusion is applied on every platform, so device and CI build the identical tree.
5. Built with `make -j1` (R9) and the C++ compiler taken from the Conan profile conf
   (R33), not from shell variables.
6. The upstream unit test suite (`make -C src check`, src/tests + src/tests/cptests) is
   run as part of `build()`, so the `conan create` log of every round carries the real
   upstream test counts of that build.
"""

import os
import shutil

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

# Top-level documentation file of the dinit release tarball that collides with the
# `build/` directory on a case-insensitive filesystem (adaptation note 4).
_SOURCE_EXCLUDES = ["dinit-0.21.0/BUILD"]

# The utility is installed under these names; upstream installs the last four as
# symlinks to the first one and the program dispatches on basename(argv[0]).
_TOOL_ALIASES = ["dinit-halt", "dinit-poweroff", "dinit-reboot", "dinit-soft-reboot"]

# Name the build produces, installed as bin/dinit-shutdown.
_BUILT_TOOL = "dinit-shutdown"


class DinitShutdownConan(ConanFile):
    name = "dinit-shutdown"
    version = "0.21.0"
    description = ("System shutdown utilities (dinit-shutdown/-halt/-poweroff/-reboot/"
                   "-soft-reboot) of the dinit service manager")
    license = "Apache-2.0"
    homepage = "https://davmac.org/projects/dinit/"
    url = "https://github.com/davmac314/dinit"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        # get() = download + unzip against conandata sources (url/filename/sha256).
        # excludes drops the colliding top-level BUILD note (adaptation note 4);
        # strip_root is a no-op for a single-root tarball only when combined with
        # the filtered extraction path, which excludes guarantees.
        get(self, **self.conan_data["sources"], strip_root=True, excludes=_SOURCE_EXCLUDES)

    def _cxx(self):
        # R33: take the compiler from Conan conf, never from ${CXX}/${CC}.
        # Conan 2.29 raises on dotted sub-key access, so read the dict first.
        compilers = self.conf.get("tools.build:compiler_executables", check_type=dict) or {}
        return compilers.get("cpp") or compilers.get("c++") or "clang++"

    def build(self):
        apply_conandata_patches(self)

        # R5: configure scripts are run through an explicit shell when the build
        # environment provides one (the OHOS profile sets CONFIG_SHELL).
        config_shell = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/bin/sh"

        configure_cmd = " ".join([
            f'"{config_shell}" ./configure',
            "--enable-shutdown",
            "--shutdown-prefix=dinit-",
            "--disable-strip",
            f'CXX="{self._cxx()}"',
        ])
        # dinit's build system is an in-source configure + make: configure writes
        # mconfig at the top level, build/Makefile turns it into build/includes/mconfig.h
        # and the objects land next to the sources. basic_layout keeps the build folder
        # separate, so every step runs explicitly in the source tree.
        self.run(configure_cmd, cwd=self.source_folder)
        self.run("make -C build", cwd=self.source_folder)
        self.run(f"make -C src SHUTDOWN_PREFIX=dinit- {_BUILT_TOOL} -j1",
                 cwd=self.source_folder)

        # Upstream unit test suite (src/tests + src/tests/cptests). The suite covers the
        # option/env/iostream/control-protocol helpers shared with the daemon; it is run
        # here so every conan create round logs the real counts.
        self.run("make -C src check -j1", cwd=self.source_folder)

    def package(self):
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

        built = os.path.join(self.source_folder, "src", _BUILT_TOOL)
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        installed = os.path.join(bin_dir, _BUILT_TOOL)
        shutil.copyfile(built, installed)
        os.chmod(installed, 0o755)

        # Upstream installs these names as symlinks to the same binary. Regular copies
        # are shipped instead: the program only uses basename(argv[0]), so behaviour is
        # identical, and it keeps the package independent of symlink handling on HMDFS
        # and in the conan cache (which dereferences them on install anyway).
        for alias in _TOOL_ALIASES:
            alias_path = os.path.join(bin_dir, alias)
            shutil.copyfile(installed, alias_path)
            os.chmod(alias_path, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.output.info("dinit-shutdown tools: %s" %
                         ", ".join([_BUILT_TOOL] + _TOOL_ALIASES))
