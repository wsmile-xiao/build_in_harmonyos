#!/usr/bin/env python3
"""Conan recipe for sfic (Simple File Integrity Checker), a C command-line tool.

sfic records file metadata (type/permissions/uid/gid/size/mtime/sha256) into a
tdb (Samba trivial database) file and can list or compare such databases to
detect filesystem changes.

OHOS adaptation notes
---------------------
* Hard dependency: tdb, linked dynamically. tdb/1.4.15 is already published to
  the ohpcd registry (armv8/OHOS shared library, SONAME libtdb.so.1), so this
  recipe declares ``requires("tdb/1.4.15")`` instead of vendoring tdb sources.
  The tdb 1.4.15 recipe runs its full upstream test suite (``make test``,
  37 test programs) during its own build.
* sfic's configure accepts the tdb include dir only through
  ``--with-tdb-headers=DIR`` (a configure.ac quirk: the default branch writes
  an empty value); the lib dir comes from ``--with-tdb-lib=DIR`` (-L path).
* The bundled 2006 config.sub does not know the aarch64-linux-ohos triplet.
* ``make check`` is invoked in build(); the upstream tarball defines the
  target but ships no test programs, so it exits cleanly with
  "Nothing to be done" — all functional coverage lives in test_package/.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class SficConan(ConanFile):
    name = "sfic"
    version = "0.1.7"
    description = "Simple File Integrity Checker - file metadata tdb database, list and compare"
    license = "GPL-2.0"
    homepage = "https://sfic.sourceforge.net/"
    url = "https://sourceforge.net/projects/sfic/"
    package_type = "application"
    topics = ("integrity", "security", "tdb", "cli")
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("sfic is supported only on Linux/OHOS")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def requirements(self):
        self.requires("tdb/1.4.15")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tdb = self.dependencies["tdb"]
        # configure.ac: --with-tdb-headers appends the dir to CPPFLAGS (the
        # default branch appends an empty value), --with-tdb-lib adds -L.
        tc.configure_args.append(
            f"--with-tdb-headers={os.path.join(tdb.package_folder, 'include')}"
        )
        tc.configure_args.append(
            f"--with-tdb-lib={os.path.join(tdb.package_folder, 'lib')}"
        )
        if str(self.settings.os) == "OHOS":
            # AutotoolsToolchain does not inject the OHOS triplets in this
            # conan build; config.sub only accepts the -ohos spelling after
            # patches/0001-config.sub-ohos-triplet.patch.
            tc.configure_args.append("--build=aarch64-linux-ohos")
            tc.configure_args.append("--host=aarch64-linux-ohos")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        if self.settings.os == "OHOS":
            bash = shutil.which("bash") or "/data/service/hnp/bin/bash"
            os.environ["CONFIG_SHELL"] = bash
            os.environ["SHELL"] = bash
            # The bundled configure (autoconf 2.61) runs under its
            # "#! /bin/sh" shebang; on OHOS that is mksh, whose $(...)
            # command substitution uses hardcoded /tmp tempfiles (TMPDIR is
            # ignored) — with read-only /tmp every autoconf conftest check
            # breaks ("C compiler cannot create executables"). bash honors
            # TMPDIR, so repoint the shebang. Inline edit (like 4ti2's
            # configure fix) instead of a patch: the bash path is
            # environment-specific and must not live in a repo patch file.
            _configure = os.path.join(self.source_folder, "configure")
            with open(_configure, "r", encoding="utf-8", errors="ignore") as f:
                _text = f.read()
            if _text.startswith("#! /bin/sh"):
                with open(_configure, "w", encoding="utf-8") as f:
                    f.write(f"#! {bash}\n" + _text[len("#! /bin/sh\n"):])
            # OHOS /tmp is read-only: point configure's temp dir into the
            # writable build workspace. The umask/mktemp hardening lives in
            # patches/0002.
            _tmpdir = os.path.join(self.build_folder, "tmp")
            os.makedirs(_tmpdir, exist_ok=True)
            os.environ["TMPDIR"] = _tmpdir
        # Embed RPATH to the tdb package lib dir: the L2 CI smoke gate runs
        # bin/sfic --version without any LD_LIBRARY_PATH, so the binary must
        # resolve libtdb.so.1 on its own (musl honors DT_RPATH).
        _tdb_lib = os.path.join(self.dependencies["tdb"].package_folder, "lib")
        os.environ["LDFLAGS"] = (
            f"-Wl,-rpath,{_tdb_lib} " + os.environ.get("LDFLAGS", "")
        )
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # Upstream check target exists but ships no test programs; running it
        # keeps the build contract honest (log evidence + future-proofing).
        autotools.make(target="check", args=["-j1"])

    def package(self):
        Autotools(self).install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
