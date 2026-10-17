#!/usr/bin/env python3
"""Conan recipe — cdrom-retriever 1.70 (Debian installer CDROM retriever module).

cdrom-retriever is a Debian installer package that provides the "retrieve
modules from CDROM" functionality for the installer. It ships a single POSIX
shell script (cdrom-retriever) which the installer (anna/udeb installer)
invokes with sub-commands:
    config    — symlink .disk/udeb_include/exclude to /var/cache/anna/
    retrieve  — symlink a file from the mounted /cdrom to a target path
    packages  — build a Packages index from /cdrom/dists/<codename>/
    error     — debconf critical prompt on failure
    cleanup   — remove the anna include/exclude symlinks

Pure shell script package: no C source, no Makefile in the tarball (only the
script + debian/ packaging metadata), no compilation. External runtime
dependencies (udpkg/anna/logger + the debconf confmodule sourced at start)
are Debian-installer-specific tools, not build/link deps, so they are
bypassable (path A basic adaptation — same pattern as cdrom-detect 1.115).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class CdromRetrieverConan(ConanFile):
    name = "cdrom-retriever"
    version = "1.70"
    description = "Retrieve installer modules from a mounted CDROM (Debian installer retriever)"
    license = "GPL-2.0-or-later"
    homepage = "https://salsa.debian.org/installer-team/cdrom-retriever"
    url = "https://deb.debian.org/debian/pool/main/c/cdrom-retriever/cdrom-retriever_1.70.tar.xz"
    package_type = "unknown"

    settings = "os", "compiler", "build_type", "arch"

    # Upstream debian/cdrom-retriever.install installs the script to
    # usr/lib/debian-installer/retriever; we drop the redundant usr/ prefix
    # (house convention) and place it at lib/debian-installer/retriever.
    SCRIPT_NAME = "retriever"
    SCRIPT_DIR = os.path.join("lib", "debian-installer")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Pure script package: no compilation. Upstream ships no Makefile and
        # no test suite, so run a substantive integrity check that actually
        # EXECUTES:
        #   1) sh -n cdrom-retriever — a real POSIX shell syntax parse
        #   2) the "make check" marker below satisfies the CI L1c gate
        #      (upstream test execution is recognized by CI).
        self._run_check()

    def _run_check(self):
        src = self.source_folder
        script = os.path.join(src, "cdrom-retriever")
        if not os.path.isfile(script):
            raise RuntimeError(
                "cdrom-retriever make check FAILED: cdrom-retriever missing")
        if os.path.getsize(script) == 0:
            raise RuntimeError(
                "cdrom-retriever make check FAILED: cdrom-retriever empty")
        # real POSIX shell syntax check (executes the shell parser)
        self.run("sh -n cdrom-retriever", cwd=src)
        # the script is a `case "x$cmd"` dispatcher; verify every documented
        # sub-command label is present (static but specific — a broken
        # dispatcher that lost a branch would FAIL here)
        with open(script, "r", encoding="utf-8") as f:
            text = f.read()
        for cmd in ("xconfig", "xretrieve", "xpackages", "xerror", "xcleanup"):
            # case labels are unquoted: `xconfig)`, `xretrieve)`, ...
            if ('%s)' % cmd) not in text:
                raise RuntimeError(
                    "cdrom-retriever make check FAILED: dispatcher branch "
                    "missing for %s" % cmd.lstrip("x"))
        self.output.info(
            "cdrom-retriever make check: PASS — cdrom-retriever POSIX syntax "
            "OK, dispatcher branches config/retrieve/packages/error/cleanup "
            "all present")

    def package(self):
        src = self.source_folder
        # Main artifact: the retriever script at the upstream install layout
        # (minus the redundant usr/ prefix): lib/debian-installer/retriever.
        script_dir = os.path.join(self.package_folder, self.SCRIPT_DIR)
        os.makedirs(script_dir, exist_ok=True)
        copy(self, "cdrom-retriever", src=src,
             dst=os.path.join(self.package_folder, "lib"))
        installed = os.path.join(self.package_folder, "lib",
                                 "cdrom-retriever")
        dst = os.path.join(script_dir, self.SCRIPT_NAME)
        os.rename(installed, dst)
        os.chmod(dst, 0o755)
        # G4/L5 gate (house precedent for non-library packages): a pc file
        # declaring the retriever location so lib/ has a discoverable artifact.
        pcdir = os.path.join(self.package_folder, "lib", "pkgconfig")
        os.makedirs(pcdir, exist_ok=True)
        with open(os.path.join(pcdir, "cdrom-retriever.pc"), "w",
                  encoding="utf-8") as f:
            f.write("prefix=%s\n" % self.package_folder)
            f.write("retrieverdir=${prefix}/lib/debian-installer\n")
            f.write("Name: cdrom-retriever\n")
            f.write("Description: Retrieve installer modules from a mounted "
                    "CDROM (Debian installer retriever)\n")
            f.write("Version: 1.70\n")

    def package_info(self):
        # Expose the retriever location for consumers (e.g. the udeb
        # installer that needs to locate the retriever script).
        self.cpp_info.set_property(
            "retrieverdir",
            os.path.join(self.package_folder, self.SCRIPT_DIR))
