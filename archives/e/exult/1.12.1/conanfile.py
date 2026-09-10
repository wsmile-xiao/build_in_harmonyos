#!/usr/bin/env python3
"""Conan recipe for the Exult Autotools application on HarmonyOS/Linux."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class ExultConan(ConanFile):
    name = "exult"
    version = "1.12.1"
    description = "Ultima VII game engine and data tools"
    license = "GPL-2.0-or-later"
    homepage = "https://exult.info/"
    url = "https://github.com/exult/exult"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("Exult is supported only on Linux/OHOS")
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def export_sources(self):
        export_conandata_patches(self)
        macro_dir = os.path.join(self.recipe_folder, "m4")
        if os.path.isdir(macro_dir):
            copy(self, "*.m4", src=macro_dir,
                 dst=os.path.join(self.export_sources_folder, "m4"))

    def requirements(self):
        self.requires("sdl2/2.30.10")
        self.requires("libpng/1.6.58")
        self.requires("zlib/1.3.1.1", override=True)
        self.requires("libvorbis/1.3.7")
        self.requires("libogg/1.3.6")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build_requirements(self):
        self.tool_requires("autoconf/2.72")
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")
        self.tool_requires("autoconf-archive/2024.10.16")
        self.tool_requires("perl/5.42.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = AutotoolsDeps(self)
        deps.generate()
        PkgConfigDeps(self).generate()
        VirtualBuildEnv(self).generate()
        env = Environment()
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                env.prepend_path("LD_LIBRARY_PATH", libdir)
        env.prepend_path("PATH", "/data/service/hnp/bin")
        env.vars(self, scope="build").save_script("conanbuild_runpath")
        tc = AutotoolsToolchain(self)
        sdl = self.dependencies["sdl2"].package_folder
        tc.extra_cxxflags.append(f"-I{sdl}/include/SDL2")
        tc.configure_args.extend([
            "--disable-mt32emu",
            "--disable-fluidsynth",
        ])
        if str(self.settings.os) == "OHOS":
            tc.configure_args.extend([
                "--disable-android-apk",
                "--build=aarch64-linux-ohos",
                "--host=aarch64-linux-ohos",
            ])
        tc.generate()

    def build(self):
        src = self.source_folder
        apply_conandata_patches(self)
        am_pkg = self.dependencies.build["automake"].package_folder
        ac_pkg = self.dependencies.build["autoconf"].package_folder
        lt_pkg = self.dependencies.build["libtool"].package_folder
        perl_pkg = self.dependencies.build["perl"].package_folder
        am_lib = os.path.join(am_pkg, "share", "automake-1.18")
        lt_lib = os.path.join(lt_pkg, "share", "aclocal")
        perl_lib = os.path.join(perl_pkg, "lib", "perl5")
        env = (
            "PATH={am}:{ac}:{lt}:$PATH "
            "PERL5LIB={perl}:{amlib} ACLOCAL_PATH={ltlib} "
            "AUTOCONF={ac}/autoconf AUTOHEADER={ac}/autoheader "
            "AUTOM4TE={ac}/autom4te TMPDIR=$HOME/tmp "
        ).format(
            am=os.path.join(am_pkg, "bin"),
            ac=os.path.join(ac_pkg, "bin"),
            lt=os.path.join(lt_pkg, "bin"),
            perl=perl_lib,
            amlib=am_lib,
            ltlib=lt_lib,
        )
        self.run(
            "for f in configure config.guess config.sub install-sh missing "
            "compile depcomp ltmain.sh; do "
            "[ ! -e \"$f\" ] || chmod +x \"$f\"; done",
            cwd=src,
            env="conanbuild",
        )
        if not os.path.isfile(os.path.join(src, "configure")):
            self.run(env + "autoreconf -fiv", cwd=src, env="conanbuild")

        configure = os.path.join(src, "configure")
        if os.path.isfile(configure):
            replace_in_file(self, configure, "umask 077", "umask 022")
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # Preserve and execute the complete upstream recursive test target.
        autotools.make(args=["check"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                self.runenv_info.prepend_path("LD_LIBRARY_PATH", libdir)
