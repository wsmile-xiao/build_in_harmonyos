"""Libctl 4.5.1 for OpenHarmony PC."""

import os
import shlex
from pathlib import Path

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import Environment, VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import copy, get, replace_in_file
from conan.tools.gnu import AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.microsoft import unix_path


class LibctlConan(ConanFile):
    name = "libctl"
    version = "4.5.1"
    description = "Guile-based control files and geometric utilities"
    license = "LGPL-2.0-or-later"
    homepage = "https://github.com/NanoComp/libctl"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    exports_sources = "patches/*"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    win_bash = True

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # --without-guile omits libctl itself; it is not a valid package fallback.
        self.requires("guile/2.2.7.1", run=True,
                      transitive_headers=True, transitive_libs=True)
        # Guile's published package loads these shared libraries at runtime.
        # Keep them in the consuming graph even when Conan marks Guile's
        # transitive binaries as skippable for an ordinary shared-library link.
        # libguile.h exposes both <gc/gc.h> and <gmp.h> to consumers.
        self.requires("gc/8.2.12", run=True, transitive_headers=True)
        self.requires("gmp/6.3.0", run=True, transitive_headers=True)
        self.requires("libffi/3.4.4", run=True)
        self.requires("libunistring/1.0", run=True)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        source = dict(self.conan_data["sources"][self.version])
        local_archive = os.environ.get("LIBCTL_SOURCE_ARCHIVE")
        if local_archive:
            archive = Path(local_archive).resolve(strict=True)
            if not archive.is_file():
                raise ValueError("LIBCTL_SOURCE_ARCHIVE must name a regular file")
            source["url"] = archive.as_uri()
            source["filename"] = archive.name
        get(self, **source, strip_root=True)
        # The published Guile binary contains libguile/* but omitted its
        # public umbrella header. Keep the upstream 2.2.7 header in this
        # recipe, rather than changing the shared Guile package in place.
        copy(self, "libguile.h", src=os.path.join(self.export_sources_folder, "patches"),
             dst=self.source_folder)

    def generate(self):
        AutotoolsToolchain(self).generate()
        AutotoolsDeps(self).generate()
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()

    def _guile_environment(self):
        guile = self.dependencies["guile"]
        env = Environment()
        bin_dir = os.path.join(guile.package_folder, "bin")
        env.prepend_path("PATH", bin_dir)
        env.define("GUILE", os.path.join(bin_dir, "guile"))
        # The packaged guile-config is a shell script; execute it through sh
        # because direct script execution can be denied on an OHOS data mount.
        config = unix_path(self, os.path.join(bin_dir, "guile-config"))
        env.define("GUILE_CONFIG", "sh " + shlex.quote(config))
        for dependency in self.dependencies.host.values():
            if not dependency.package_folder:
                continue
            for lib_dir in dependency.cpp_info.libdirs:
                resolved = lib_dir if os.path.isabs(lib_dir) else os.path.join(
                    dependency.package_folder, lib_dir)
                if os.path.isdir(resolved):
                    env.prepend_path("LD_LIBRARY_PATH", resolved)
        return env

    def build(self):
        configure_path = os.path.join(self.source_folder, "configure")
        # HMDFS presents new files with a different numeric owner. Autoconf's
        # mktemp -d forces mode 0700, making its generated config.status unable
        # to write inside that directory. Use an atomic mkdir with group access
        # inside this task-local build tree; never broaden permissions globally.
        private_mktemp = 'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&'
        private_mkdir = '(umask 077 && mkdir "$tmp")'
        configure_text = Path(configure_path).read_text(encoding="utf-8")
        if configure_text.count(private_mktemp) != 1 or configure_text.count(private_mkdir) != 1:
            raise ValueError("unexpected Autoconf temporary-directory template")
        replace_in_file(self, configure_path, private_mktemp,
                        'tmp=./conf$$-$RANDOM; (umask 007 && mkdir "$tmp") &&')
        replace_in_file(self, configure_path, private_mkdir,
                        '(umask 007 && mkdir "$tmp")')
        configure = unix_path(self, configure_path)
        # The bundled config.guess creates mode-0700 scratch directories on a
        # shared OHOS mount whose numerical owner can differ between sessions.
        # Its config.sub also predates the OHOS triplet, so pass the compatible
        # native Linux/AArch64 canonical tuple explicitly.
        args = ["--prefix=/", "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-gnu",
                "--enable-shared" if self.options.shared else "--disable-shared"]
        args.append("--disable-static" if self.options.shared else "--enable-static")
        with self._guile_environment().vars(self).apply():
            include_flag = "-I" + unix_path(self, self.source_folder)
            self.run('CPPFLAGS="{} $CPPFLAGS" bash {} {}'.format(
                include_flag, shlex.quote(configure), " ".join(args)), env="conanbuild")
            self.run("make -j2", env="conanbuild")
            if can_run(self):
                self.run("make check -j1", env="conanbuild")

    def package(self):
        with self._guile_environment().vars(self).apply():
            self.run("make install DESTDIR={}".format(
                shlex.quote(unix_path(self, self.package_folder))), env="conanbuild")
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "COPYRIGHT", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "libguile.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.libs = ["ctl", "ctlgeom"]
        self.cpp_info.set_property("cmake_file_name", "libctl")
        self.cpp_info.set_property("cmake_target_name", "libctl::libctl")
        self.runenv_info.prepend_path("GUILE_LOAD_PATH",
                                      os.path.join(self.package_folder, "share", "libctl"))
