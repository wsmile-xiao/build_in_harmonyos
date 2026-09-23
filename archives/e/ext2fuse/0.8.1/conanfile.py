#!/usr/bin/env python3
"""Conan recipe for ext2fuse 0.8.1."""

import glob
import os
import shlex
import time

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class Ext2fuseConan(ConanFile):
    name = "ext2fuse"
    version = "0.8.1"
    description = "FUSE-based ext2 filesystem implementation"
    license = "GPL-2.0-or-later"
    homepage = "https://sourceforge.net/projects/ext2fuse/"
    url = ""  # CI fills this
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # The upstream code targets FUSE 2.x; the port uses libfuse 3.x.
        self.requires("libfuse/3.18.2")

    def build_requirements(self):
        # configure.ac is regenerated after applying the FUSE 3 port patches.
        self.tool_requires("autoconf/2.72")
        self.tool_requires("automake/1.18")
        # pkgconf provides pkg.m4 and the pkg-config-compatible executable.
        self.tool_requires("pkgconf/3.0.5")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"ext2fuse supports only Linux and OHOS, got {self.settings.os}"
            )
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(
                "ext2fuse/0.8.1 currently supports only OHOS armv8"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()

        tc = AutotoolsToolchain(self)
        tc.parallel = False
        if self.settings.os == "OHOS":
            tc.configure_args.extend(
                [
                    "--build=aarch64-unknown-linux-ohos",
                    "--host=aarch64-unknown-linux-ohos",
                ]
            )

        # pkgconf 3.0.5 deliberately installs `pkgconf`, not a pkg-config
        # alias. Keep the generated metadata available for consumers.
        env = tc.environment()
        env.define("PKG_CONFIG", "pkgconf")
        env.append_path("PKG_CONFIG_PATH", self.generators_folder)
        pkgconf = self.dependencies.build["pkgconf"].package_folder
        env.append_path("ACLOCAL_PATH", os.path.join(pkgconf, "share", "aclocal"))
        for aclocal_dir in sorted(
            glob.glob("/data/service/hnp/*/*/share/aclocal")
        ):
            env.append_path("ACLOCAL_PATH", aclocal_dir)

        # The OHOS worker keeps the Conan cache on HMDFS. Scripts and ELF
        # files there cannot be executed directly by the build user, while
        # the SDK shell and compiler under /data/service/hnp are executable.
        # The release tarball already contains generated Autotools output, so
        # use it directly instead of bootstrapping with autoreconf.
        if self.settings.os == "OHOS":
            tmpdir = os.path.join(self.build_folder, "tmp")
            os.makedirs(tmpdir, exist_ok=True)
            bash = "/data/service/hnp/bin/bash"
            env.define("TMPDIR", tmpdir)
            env.define("CONFIG_SHELL", bash)
            env.define("SHELL", bash)
            env.define("AR", "/data/service/hnp/bin/ar")
            env.define("ACLOCAL", ":")
            env.define("AUTOMAKE", ":")
            env.define("AUTOCONF", ":")
            env.define("AUTOHEADER", ":")
            env.define("AUTOM4TE", ":")

            # The upstream generated Makefile.in predates the FUSE3 patch and
            # has no @FUSE_CFLAGS@/@FUSE_LIBS@ substitutions. Inject the
            # Conan dependency paths through the standard Autotools flags.
            fuse = self.dependencies["libfuse"]
            # OHOS Clang emits external definitions for the legacy
            # `extern __inline__` helpers; use the library's inline.c copies.
            env.append("CPPFLAGS", "-DNO_INLINE_FUNCS")
            # OHOS may expose Linux kernel headers while lacking the legacy
            # `_llseek` syscall macro ABI; select the POSIX lseek fallback.
            env.append("CPPFLAGS", "-DEXT2FUSE_USE_PORTABLE_LSEEK")
            env.append("CPPFLAGS", "-I{}".format(os.path.join(self.source_folder, "lib")))
            for include_dir in fuse.cpp_info.includedirs:
                env.append("CPPFLAGS", "-I{}".format(include_dir))
                fuse3_include = os.path.join(include_dir, "fuse3")
                if os.path.isdir(fuse3_include):
                    env.append("CPPFLAGS", "-I{}".format(fuse3_include))
            for lib_dir in fuse.cpp_info.libdirs:
                env.append("LDFLAGS", "-L{}".format(lib_dir))
            for library in fuse.cpp_info.libs:
                env.append("LIBS", "-l{}".format(library))

        tc.generate(env=env)

    def build(self):
        os.umask(0)
        apply_conandata_patches(self)

        if self.settings.os == "OHOS":
            # The source archive ships configure/Makefile.in/aclocal.m4.
            # HMDFS refuses direct execution of the Conan-cached autoreconf
            # scripts, so use the shipped generated files instead.
            configure = os.path.join(self.source_folder, "configure")
            if not os.path.isfile(configure):
                raise ConanInvalidConfiguration(
                    "ext2fuse source archive must contain generated configure"
                )
            from conan.tools.files import replace_in_file

            # HMDFS setgid directories make Autoconf's umask 077 temporary
            # directory unusable for config.status.
            replace_in_file(self, configure, "umask 077", "umask 022")
            self._pin_generated_autotools_files()
        else:
            self.run(
                "autoreconf --install --verbose",
                cwd=self.source_folder,
                env="conanbuild",
            )

        autotools = Autotools(self)
        if self.settings.os == "OHOS":
            self.run(
                "sh {} {}".format(
                    shlex.quote(configure),
                    autotools._configure_args,
                ),
                cwd=self.build_folder,
                env="conanbuild",
            )
        else:
            autotools.configure()
        # The device sandbox does not reliably support Autotools jobserver
        # FIFOs, so keep this small legacy tree single-threaded.
        autotools.make(
            args=[
                "-j1",
                "SHELL=/data/service/hnp/bin/bash",
                "AR=/data/service/hnp/bin/ar",
                "ACLOCAL=:",
                "AUTOMAKE=:",
                "AUTOCONF=:",
                "AUTOHEADER=:",
                "AUTOM4TE=:",
            ]
        )

    def _pin_generated_autotools_files(self):
        """Prevent make from re-running unavailable Autotools generators."""
        now = time.time()
        generated = []
        inputs = []
        for root, _, files in os.walk(self.source_folder):
            for name in files:
                path = os.path.join(root, name)
                if name in {
                    "configure",
                    "aclocal.m4",
                    "config.h.in",
                    "Makefile.in",
                }:
                    generated.append(path)
                elif name == "Makefile.am" or name == "configure.ac":
                    inputs.append(path)

        for path in inputs:
            os.utime(path, (now, now))
        for path in generated:
            os.utime(path, (now + 1, now + 1))

    def package(self):
        if self.settings.os == "OHOS":
            self.run(
                "make install DESTDIR={} SHELL=/data/service/hnp/bin/bash "
                "ACLOCAL=: AUTOMAKE=: AUTOCONF=: AUTOHEADER=: AUTOM4TE=:".format(
                    shlex.quote(self.package_folder)
                ),
                cwd=self.build_folder,
                env="conanbuild",
            )
        else:
            Autotools(self).install()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
