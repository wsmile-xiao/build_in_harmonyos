#!/usr/bin/env python3
"""Conan recipe — detachtty 11.0.0 (Makefile).

detachtty is a two-binary terminal session tool: detachtty (server, hosts
the child on a pty and serves a unix-domain socket) and attachtty
(client, connects to the socket directly or over ssh). Upstream build is
a plain Makefile with no configure step and no test target.
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class DetachttyConan(ConanFile):
    name = "detachtty"
    version = "11.0.0"
    description = "Attach/detach from interactive processes across the network"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/cosmos72/detachtty"
    url = "https://github.com/cosmos72/detachtty"
    topics = ("terminal", "pty", "detach", "attach")
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"][0], strip_root=True)
        self._patch_abstract_socket()

    def _patch_abstract_socket(self):
        # OHOS adaptation: filesystems under /storage and /dev/shm reject
        # bind() (EPERM/EACCES) and /tmp is read-only, so no filesystem
        # path can host the unix-domain socket. Support Linux abstract
        # namespace: a leading '@' maps to sun_path[0] = NUL (no file).
        # Both binaries share the same convention; tidy_up skips unlink
        # for abstract names. Upstream behavior for regular paths unchanged.
        det = os.path.join(self.source_folder, "detachtty.c")
        with open(det, "r", encoding="utf-8", errors="replace") as handle:
            text = handle.read()
        old_det = (
            "    addr.sun_family=AF_UNIX;\n"
            "    strncpy(addr.sun_path, socket_path, UNIX_PATH_MAX);\n"
            "    addr.sun_path[UNIX_PATH_MAX-1] = '\\0';"
        )
        new_det = (
            "    addr.sun_family=AF_UNIX;\n"
            "    strncpy(addr.sun_path, socket_path, UNIX_PATH_MAX);\n"
            "    addr.sun_path[UNIX_PATH_MAX-1] = '\\0';\n"
            "    if (addr.sun_path[0] == '@')\n"
            "        addr.sun_path[0] = '\\0';"
        )
        if old_det not in text:
            raise ConanException("detachtty.c abstract patch anchor not found")
        text = text.replace(old_det, new_det)
        old_tidy = "    if (unlink(socket_path))"
        new_tidy = "    if (socket_path[0] != '@' && unlink(socket_path))"
        if old_tidy not in text:
            raise ConanException("detachtty.c tidy anchor not found")
        text = text.replace(old_tidy, new_tidy)
        with open(det, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        att = os.path.join(self.source_folder, "attachtty.c")
        with open(att, "r", encoding="utf-8", errors="replace") as handle:
            text = handle.read()
        old_att = (
            "    s_a.sun_family=AF_UNIX;\n"
            "    strncpy(s_a.sun_path,path,UNIX_PATH_MAX);\n"
            "    s_a.sun_path[UNIX_PATH_MAX-1]='\\0';"
        )
        new_att = (
            "    s_a.sun_family=AF_UNIX;\n"
            "    strncpy(s_a.sun_path,path,UNIX_PATH_MAX);\n"
            "    s_a.sun_path[UNIX_PATH_MAX-1]='\\0';\n"
            "    if (s_a.sun_path[0] == '@')\n"
            "        s_a.sun_path[0] = '\\0';"
        )
        if old_att not in text:
            raise ConanException("attachtty.c abstract patch anchor not found")
        text = text.replace(old_att, new_att)
        with open(att, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)

    def _get_cc(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = (compilers or {}).get("c", "clang")
        if os.path.isfile(cc):
            return cc
        found = shutil.which(os.path.basename(cc))
        return found or cc

    def build(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "detachtty requires a POSIX host (Linux or OHOS), got %s"
                % self.settings.os
            )
        cc = self._get_cc()
        # E563: OHOS musl merges forkpty/openpty into libc; the sysroot
        # ships only an empty libutil.a stub. Drop -lutil on OHOS so the
        # link resolves against libc. Linux keeps the upstream default.
        if str(self.settings.os) == "OHOS":
            make_cmd = "make -j1 CC={cc} OS_LDLIBS=".format(cc=cc)
        else:
            make_cmd = "make -j1 CC={cc}".format(cc=cc)
        self.run(make_cmd, cwd=self.source_folder)

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        # Do not rely on upstream make install (needs external install
        # program plus DESTDIR handling, fragile on OHOS where the binary
        # was missing from bin/). Copy the already-built binaries directly.
        for binary in ("detachtty", "attachtty"):
            src = os.path.join(self.source_folder, binary)
            if not os.path.isfile(src):
                raise ConanException("build produced no binary: %s" % src)
            copy(self, binary, src=self.source_folder, dst=bindir, keep_path=False)
        copy(
            self,
            "detachtty.1",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "man", "man1"),
            keep_path=False,
        )
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        for binary in ("detachtty", "attachtty"):
            path = os.path.join(bindir, binary)
            if os.path.isfile(path):
                try:
                    os.chmod(path, 0o755)
                except OSError:
                    pass

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libs = []
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
