#!/usr/bin/env python3
"""Conan recipe for socklog 2.1.2 (smarden makefile build)."""
import os
from pathlib import Path

from conan import ConanFile
from conan.tools.files import (apply_conandata_patches, chdir, copy,
                               export_conandata_patches, get, save)
from conan.tools.layout import basic_layout


class SocklogConan(ConanFile):
    name = "socklog"
    version = "2.1.2"
    description = ("System and kernel logging services: a small and secure "
                   "replacement for syslogd.")
    license = "BSD-3-Clause"
    homepage = "https://smarden.org/socklog/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("syslog", "logging", "daemon", "smarden", "runit")

    settings = "os", "compiler", "build_type", "arch"

    # Programs shipped by upstream package/commands.
    commands = ("socklog", "socklog-check", "socklog-conf", "tryto", "uncat")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)
        # Upstream ships a "smarden" layout: <root>/src holds the buildable tree
        # (Makefile, conf-cc, conf-ld) and <root>/{man,doc,package} sit next to
        # it. strip_root only removes a single common directory, so the archive
        # can still land as socklog-<v>/src or admin/socklog-<v>/src. Locate the
        # real root via src/Makefile and flatten every sibling into the source
        # folder, otherwise man/ and package/ stay unreachable from package().
        source_folder = Path(self.source_folder)
        matches = sorted(source_folder.glob("**/src/Makefile"),
                         key=lambda p: (len(p.parts), str(p)))
        if not matches:
            raise RuntimeError(
                "upstream src/Makefile not found under {}".format(source_folder))
        upstream_root = matches[0].parent.parent
        for item in sorted(upstream_root.iterdir()):
            target = source_folder / item.name
            if item.is_dir() and (item / "Makefile").is_file():
                for inner in sorted(item.iterdir()):
                    inner.rename(source_folder / inner.name)
                item.rmdir()
            elif item != target:
                item.rename(target)
        # Prune the now-empty intermediate directories (e.g. the leftover
        # "admin/socklog-2.1.2" chain) back down to the source folder. rmdir
        # only succeeds on an empty dir, so anything unexpected stops the walk.
        current = upstream_root
        while current != source_folder and current.is_dir():
            try:
                current.rmdir()
            except OSError:
                break
            current = current.parent

    def build(self):
        # socklog has no configure script. The generated ./compile and ./load
        # wrappers take their whole command line from the first line of
        # conf-cc / conf-ld (see src/print-cc.sh, src/print-ld.sh), so those
        # two files are the injection point for the Conan toolchain.
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        cc = compilers.get("c") or "clang"
        if self.settings.build_type == "Debug":
            cflags = "-g -Wall"
            ldflags = ""
        else:
            cflags = "-O2 -Wall"
            ldflags = "-s"
        save(self, os.path.join(self.build_folder, "conf-cc"),
             "{} {}\n".format(cc, cflags))
        save(self, os.path.join(self.build_folder, "conf-ld"),
             " ".join([x for x in (cc, ldflags) if x]) + "\n")
        # -j1: the GNU make jobserver needs mkfifo, which HMDFS restricts.
        with chdir(self, self.build_folder):
            self.run("make -j1")

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        for program in self.commands:
            copied = copy(self, program, src=self.build_folder, dst=bin_dir)
            if not copied:
                raise RuntimeError(
                    "missing built executable: {}".format(program))
        man_dir = os.path.join(self.source_folder, "man")
        share_man = os.path.join(self.package_folder, "share", "man")
        for pattern, section in (("*.8", "man8"), ("*.1", "man1")):
            copied = copy(self, pattern, src=man_dir,
                          dst=os.path.join(share_man, section))
            if not copied:
                raise RuntimeError("missing man pages: {} in {}".format(
                    pattern, man_dir))
        copy(self, "COPYING",
             src=os.path.join(self.source_folder, "package"),
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # socklog installs programs only: no libraries and no headers.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
