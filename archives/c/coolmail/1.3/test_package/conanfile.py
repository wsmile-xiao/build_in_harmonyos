#!/usr/bin/env python3
"""Conan test_package — coolmail 1.3.

coolmail is a GUI executable (R34: the test must exercise the packaged
artifact).  Neither the device nor the CI worker has an X server — there is
no Xorg/Xvfb binary in the image and no OHOS xorg-server implementation is
published on the remote — so the window/mailbox animation cannot be run
here.  test_coolmail.sh still asserts real behaviour of the packaged binary:

  * `coolmail -h` prints the usage screen and exits 0 (the only code path
    that finishes without an X display);
  * a run without DISPLAY must exit non-zero with Xt's "Can't open display"
    diagnostic — that loads the whole dynamic dependency chain
    (libXt -> libSM/libICE, libX11 -> libxcb/libXau/libXdmcp) and executes
    the login-name resolution at the top of main() before display init;
  * the installed man page and X11 app-defaults resource file are present.

The dependency libdirs are exported through LD_LIBRARY_PATH explicitly: OHOS
ships no system libX11/libXt, so runtime resolution depends entirely on the
Conan packages.
"""
import os
import shlex

from conan import ConanFile
from conan.tools.layout import basic_layout


class CoolmailTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _dependency_libdirs(self):
        """Absolute libdirs of the tested package and all its host deps."""
        libdirs, seen = [], set()
        for _, dep in self.dependencies.host.items():
            base = dep.package_folder or ""
            for entry in dep.cpp_info.libdirs:
                path = entry if os.path.isabs(entry) else os.path.join(base, entry)
                if os.path.isdir(path) and path not in seen:
                    seen.add(path)
                    libdirs.append(path)
        return libdirs

    def test(self):
        coolmail = self.dependencies["coolmail"]
        bindir = coolmail.cpp_info.bindirs[0] if coolmail.cpp_info.bindirs else "bin"
        if not os.path.isabs(bindir):
            bindir = os.path.join(coolmail.package_folder, bindir)
        binary = os.path.join(bindir, "coolmail")
        if not os.path.isfile(binary):
            raise FileNotFoundError(f"packaged coolmail binary missing: {binary}")

        script = os.path.join(self.source_folder, "test_coolmail.sh")
        shell = (os.environ.get("CONFIG_SHELL")
                 or os.environ.get("SHELL")
                 or "/bin/sh")
        ldpath = ":".join(self._dependency_libdirs())

        self.run(
            f"{shlex.quote(shell)} {shlex.quote(script)} "
            f"{shlex.quote(coolmail.package_folder)} {shlex.quote(binary)} "
            f"{shlex.quote(self.build_folder)} {shlex.quote(ldpath)}",
            env="conanrun",
        )
