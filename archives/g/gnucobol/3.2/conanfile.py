#!/usr/bin/env python3
"""Conan recipe for GnuCOBOL 3.2 on OpenHarmony/HarmonyOS."""
import os
import shlex

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class GnucobolConan(ConanFile):
    name = "gnucobol"
    version = "3.2"
    description = "GnuCOBOL compiler and COBOL runtime library"
    license = "GPL-3.0-or-later AND LGPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/gnucobol/"
    url = "https://www.gnu.org/software/gnucobol/"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("gmp/6.3.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = AutotoolsDeps(self)
        deps.generate()

        tc = AutotoolsToolchain(self)
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--disable-shared", "--enable-static"])
        tc.configure_args.extend([
            "--with-math=gmp",
            "--with-curses=no",
            "--with-json=no",
            "--with-db=no",
            "--with-xml2=no",
        ])
        env = tc.environment()
        if str(self.settings.os) == "OHOS":
            env.define("STRIP", ":")
        tc.generate(env=env)

    def build(self):
        apply_conandata_patches(self)

        configure_path = os.path.join(self.source_folder, "configure")
        typo = b"clang \xfcrototype warning"
        replacement = b"clang prototype warning"
        with open(configure_path, "rb") as source_file:
            configure_content = source_file.read()
        if configure_content.count(typo) != 2:
            raise ConanException("Unexpected configure encoding typo count")
        with open(configure_path, "wb") as source_file:
            source_file.write(configure_content.replace(typo, replacement))

        # E089: patch 0006 modifies configure.ac, which would make `make`
        # regenerate aclocal.m4/configure/Makefile.in via aclocal/autoconf/
        # automake; the OHOS build host has no automake, and the release
        # tarball already ships complete generated files. Align the mtimes
        # of the shipped generated files with a time strictly newer than
        # configure.ac (the patched configure.ac mtime is the newest input)
        # but older than the Makefile that configure will generate, so make
        # treats them as up to date without re-running config.status.
        import time
        _gen_mtime = time.time()
        for _f in ("aclocal.m4", "configure", "config.h.in", "Makefile.in"):
            _p = os.path.join(self.source_folder, _f)
            if os.path.exists(_p):
                os.utime(_p, (_gen_mtime, _gen_mtime))
        # The shipped man pages (cobcrun.1, cob-config.1, cobc.1) depend on
        # configure.ac in their make rules; after patch 0006 touches
        # configure.ac, make would regenerate them via help2man, which is
        # not installed on the OHOS build host. Bump their mtimes too so
        # make keeps the pre-generated man pages.
        for _root, _dirs, _files in os.walk(self.source_folder):
            for _fn in _files:
                if _fn.endswith(".1"):
                    _p = os.path.join(_root, _fn)
                    os.utime(_p, (_gen_mtime, _gen_mtime))

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

        check_log = os.path.join(self.build_folder, "gnucobol-check.log")
        quoted_log = shlex.quote(check_log)
        rc = self.run(
            "make MAKEINFO=true -j1 check > " + quoted_log + " 2>&1; "
            "rc=$?; "
            "grep -a -E 'tests behaved as expected|tests were skipped|tests were run|failed \\(' "
            + quoted_log
            + " || true; "
            "if grep -aqE ':( FAILED| XPASS| ERROR)' " + quoted_log + "; then "
            + "  echo 'make check: FAIL/XPASS/ERROR detected in testsuite log'; rc=1; "
            + "fi; "
            "exit $rc"
        )
        if rc != 0:
            raise ConanException("make check failed (exit code %d), see %s" % (rc, check_log))

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["MAKEINFO=true"])

    def package_info(self):
        bin_dir = self.package_folder + "/bin"
        lib_dir = self.package_folder + "/lib"
        include_dir = self.package_folder + "/include"
        config_dir = self.package_folder + "/share/gnucobol/config"
        copy_dir = self.package_folder + "/share/gnucobol/copy"
        module_dir = self.package_folder + "/lib/gnucobol"

        self.cpp_info.libs = ["cob"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.requires = ["gmp::gmp"]

        for env in (self.runenv_info, self.buildenv_info):
            env.append_path("PATH", bin_dir)
            env.append_path("LD_LIBRARY_PATH", lib_dir)
            env.define_path("COB_CONFIG_DIR", config_dir)
            env.define_path("COB_COPY_DIR", copy_dir)
            env.define_path("COB_LIBRARY_PATH", module_dir)
            env.define("COB_CFLAGS", f"-I{include_dir}")
            env.define("COB_LDFLAGS", f"-L{lib_dir}")
            env.define("COB_LIBS", f"-L{lib_dir} -lcob")
