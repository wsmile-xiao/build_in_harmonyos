"""PSORTb's SVM and HMM support libraries for OpenHarmony PC."""

import os
import shlex
import shutil
from pathlib import Path

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import Environment, VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.microsoft import unix_path


class LibpsortbConan(ConanFile):
    name = "libpsortb"
    version = "1.0"
    description = "SVM and HMM support libraries for PSORTb"
    license = "GPL-2.0-only"
    homepage = "https://www.psort.org/"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    # PSORTb loads both libraries dynamically from its Perl runtime.
    options = {"shared": [True]}
    default_options = {"shared": True}
    win_bash = True

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # The DFSG-clean source omits its bundled, old libsvm copy.
        # Public svmloc headers include <svm.h>, so consumers need these
        # headers transitively as well as the runtime library.
        self.requires("libsvm/3.37.1.1", run=True, transitive_headers=True)

    def build_requirements(self):
        self.tool_requires("autoconf/2.72")
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        source = dict(self.conan_data["sources"][self.version])
        local_archive = os.getenv("LIBPSORTB_SOURCE_ARCHIVE")
        if local_archive:
            archive = Path(local_archive).resolve(strict=True)
            if not archive.is_file():
                raise ValueError("LIBPSORTB_SOURCE_ARCHIVE is not a file")
            source["url"] = archive.as_uri()
            source["filename"] = archive.name
        get(self, **source, strip_root=True)

    def generate(self):
        AutotoolsToolchain(self).generate()
        AutotoolsDeps(self).generate()
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()

    def _runtime_environment(self):
        env = Environment()
        for dependency in self.dependencies.host.values():
            if not dependency.package_folder:
                continue
            for lib_dir in dependency.cpp_info.libdirs:
                resolved = lib_dir if os.path.isabs(lib_dir) else os.path.join(
                    dependency.package_folder, lib_dir)
                if os.path.isdir(resolved):
                    env.prepend_path("LD_LIBRARY_PATH", resolved)
        return env

    def _automake_commands(self):
        # The published Automake package wraps scripts whose embedded Perl
        # shebang is not valid on HarmonyOS PC. Keep the package untouched and
        # invoke its real scripts through the Perl on the build PATH instead.
        package_folder = self.dependencies.build["automake"].package_folder
        binary_dir = os.path.join(package_folder, "bin")
        share_dir = os.path.join(package_folder, "share")
        aclocal = os.path.join(binary_dir, ".aclocal-real")
        automake = os.path.join(binary_dir, ".automake-real")
        perl = shutil.which("perl")
        if not perl:
            raise ValueError("A native Perl interpreter is required for Autotools")
        perl = unix_path(self, perl)
        automake_perllib = unix_path(self, os.path.join(share_dir, "automake-1.18"))
        automake_acdir = unix_path(self, os.path.join(share_dir, "aclocal-1.18"))
        aclocal_command = "{} {} --automake-acdir={} --system-acdir={}".format(
            shlex.quote(perl),
            shlex.quote(unix_path(self, aclocal)),
            shlex.quote(automake_acdir),
            shlex.quote(unix_path(self, os.path.join(share_dir, "aclocal"))))
        automake_command = "{} {} --libdir={}".format(
            shlex.quote(perl),
            shlex.quote(unix_path(self, automake)),
            shlex.quote(automake_perllib))
        return perl, automake_perllib, aclocal_command, automake_command

    def build(self):
        apply_conandata_patches(self)
        source = self.source_folder
        configure = unix_path(self, os.path.join(source, "configure"))
        perl, perl5lib, aclocal, automake = self._automake_commands()
        with self._runtime_environment().vars(self).apply():
            self.run("PERL={} PERL5LIB={} ACLOCAL={} AUTOMAKE={} autoreconf -fi".format(
                shlex.quote(perl), shlex.quote(perl5lib),
                shlex.quote(aclocal), shlex.quote(automake)),
                cwd=source, env="conanbuild")
            command = ("CONFIG_SHELL=/bin/sh SHELL=/bin/sh sh {} "
                       "--build=aarch64-unknown-linux-ohos "
                       "--host=aarch64-unknown-linux-ohos --prefix=/ "
                       "--libdir=/lib --enable-shared --disable-static").format(
                           shlex.quote(configure))
            self.run(command, cwd=source, env="conanbuild")
            self.run("make -j2", cwd=source, env="conanbuild")
            if can_run(self):
                self.run("make check -j1", cwd=source, env="conanbuild")

    def package(self):
        with self._runtime_environment().vars(self).apply():
            self.run("make install DESTDIR={}".format(
                shlex.quote(unix_path(self, self.package_folder))),
                cwd=self.source_folder, env="conanbuild")
        license_dir = os.path.join(self.package_folder, "licenses")
        copy(self, "COPYING", src=self.source_folder, dst=license_dir)
        copy(self, "LICENCE", src=os.path.join(self.source_folder, "modhmm0.92b"),
             dst=license_dir)

    def package_info(self):
        self.cpp_info.libs = ["svmloc", "modhmm"]
        self.cpp_info.requires = ["libsvm::libsvm"]
        self.cpp_info.set_property("cmake_file_name", "libpsortb")
        self.cpp_info.set_property("cmake_target_name", "libpsortb::libpsortb")
