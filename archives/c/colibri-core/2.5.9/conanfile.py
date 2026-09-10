#!/usr/bin/env python3
"""Conan recipe for the Colibri Core 2.5.9 C++ library and tools."""

import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
    rm,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


required_conan_version = ">=2"


class ColibriCoreConan(ConanFile):
    name = "colibri-core"
    version = "2.5.9"
    description = "C++ library and tools for compact pattern and corpus models"
    license = "GPL-3.0-only"
    homepage = "https://proycon.github.io/colibri-core/"
    url = "https://github.com/proycon/colibri-core"
    topics = ("nlp", "corpus", "n-gram", "skipgram", "text-processing")

    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("colibri-core supports Linux and OHOS")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(
                "colibri-core HarmonyOS validation requires armv8"
            )

    def requirements(self):
        self.requires("bzip2/1.0.8")

    def build_requirements(self):
        # Native HarmonyOS workers obtain the complete Autotools chain from
        # Conan. Cross-build hosts use their local Autotools installation;
        # running target Perl/Autoconf through user-mode emulation is neither
        # required nor representative of the native worker.
        if self._native_ohos_build():
            self.tool_requires("autoconf/2.72")
            self.tool_requires("automake/1.18")
            self.tool_requires("libtool/2.5.4")
            self.tool_requires("pkgconf/3.0.5")
            self.tool_requires("autoconf-archive/2024.10.16")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        VirtualBuildEnv(self).generate()
        AutotoolsDeps(self).generate()

        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(["--enable-static", "--disable-shared"])
        if self.options.fPIC:
            tc.extra_cxxflags.append("-fPIC")
        tc.generate()

        VirtualRunEnv(self).generate(scope="build")

    def _native_ohos_build(self):
        return (
            self.settings_build.os == "OHOS"
            and not self.conf.get(
                "tools.build.cross_building:cross_build", default=False
            )
        )

    def _bootstrap_autotools(self):
        if not self._native_ohos_build():
            self.run("autoreconf -fiv", cwd=self.source_folder)
            return

        automake = self.dependencies.build["automake"]
        automake_share = os.path.join(
            automake.package_folder, "share", "automake-1.18"
        )
        libtool = self.dependencies.build["libtool"]
        pkgconf = self.dependencies.build["pkgconf"]
        autoconf_archive = self.dependencies.build["autoconf-archive"]
        libtool_aclocal = os.path.join(
            libtool.package_folder, "share", "aclocal"
        )
        pkgconf_aclocal = os.path.join(
            pkgconf.package_folder, "share", "aclocal"
        )
        aclocal_dirs = [
            libtool_aclocal,
            pkgconf_aclocal,
            os.path.join(autoconf_archive.package_folder, "share", "aclocal"),
        ]
        missing_aclocal_dirs = [
            path for path in aclocal_dirs if not os.path.isdir(path)
        ]
        if missing_aclocal_dirs:
            raise ConanInvalidConfiguration(
                "Missing Conan Autotools macro directories: "
                + ", ".join(missing_aclocal_dirs)
            )
        libtool_aux = os.path.join(
            libtool.package_folder, "share", "libtool", "build-aux"
        )
        ltmain = os.path.join(libtool_aux, "ltmain.sh")
        if not os.path.isfile(ltmain):
            raise ConanInvalidConfiguration(
                f"Missing Conan libtool bootstrap file: {ltmain}"
            )

        source_m4 = os.path.join(self.source_folder, "m4")
        copy(self, "*.m4", src=libtool_aclocal, dst=source_m4)
        copy(self, "pkg.m4", src=pkgconf_aclocal, dst=source_m4)
        copy(self, "ltmain.sh", src=libtool_aux, dst=self.source_folder)
        aclocal_path = os.pathsep.join(aclocal_dirs)
        native_perl = "/data/service/hnp/bin/perl"
        if not os.path.isfile(native_perl):
            native_perl = shutil.which("perl") or "perl"
        no_op = shutil.which("true") or "true"
        automake_bin = os.path.join(automake.package_folder, "bin")
        aclocal_real = os.path.join(automake_bin, ".aclocal-real")
        automake_real = os.path.join(automake_bin, ".automake-real")
        missing_automake_scripts = [
            path
            for path in (aclocal_real, automake_real)
            if not os.path.isfile(path)
        ]
        if missing_automake_scripts:
            raise ConanInvalidConfiguration(
                "Missing Conan Automake scripts: "
                + ", ".join(missing_automake_scripts)
            )
        aclocal_command = (
            f"{native_perl} {aclocal_real} "
            f"--automake-acdir={os.path.join(automake.package_folder, 'share', 'aclocal-1.18')} "
            f"--system-acdir={os.path.join(automake.package_folder, 'share', 'aclocal')}"
        )
        automake_command = (
            f"{native_perl} {automake_real} "
            f"--libdir={automake_share}"
        )

        # Conan's Autotools packages remain first on PATH, but their
        # transitive Perl package exports an XS module directory on HMFS.
        # Native Perl cannot dlopen Cwd.so from there (Permission denied).
        # Autoreconf only needs Automake's pure-Perl modules, so keep the
        # packaged tools and replace PERL/PERL5LIB for this bootstrap step.
        # Conan's tool packages do not consistently propagate their m4 macro
        # directories on native OHOS.  Inject all macros used by configure.ac:
        # LT_INIT (libtool), PKG_PROG_PKG_CONFIG (pkgconf), and AX_* helpers.
        # libtool/2.5.4's libtoolize embeds its installation prefix, so copy
        # its generated inputs above and replace only that autoreconf substep
        # with a successful no-op.  All other Conan tools still run normally.
        self.run(
            f"PERL={shlex.quote(native_perl)} "
            f"PERL5LIB={shlex.quote(automake_share)} "
            f"ACLOCAL_PATH={shlex.quote(aclocal_path)} "
            f"ACLOCAL={shlex.quote(aclocal_command)} "
            f"AUTOMAKE={shlex.quote(automake_command)} "
            f"LIBTOOLIZE={shlex.quote(no_op)} "
            "autoreconf -fiv",
            cwd=self.source_folder,
            env="conanbuild",
        )

    def build(self):
        self._bootstrap_autotools()

        if self.settings.os == "OHOS":
            configure = os.path.join(self.source_folder, "configure")
            config_guess = os.path.join(self.source_folder, "config.guess")
            config_sub = os.path.join(self.source_folder, "config.sub")

            # HMFS/HMDFS can make Autoconf's mode-0700 temporary directories
            # unwritable after its platform permission mediation.  These are
            # generated files, so adjust them after autoreconf rather than
            # carrying release-source patches that autoreconf would overwrite.
            replace_in_file(
                self, configure, "umask 077", "umask 022", strict=False
            )
            replace_in_file(
                self, config_guess, "umask 077", "umask 022", strict=False
            )

            # GNU config does not universally recognize a native HarmonyOS
            # uname yet.  Keep config.guess active for native builds (R23) and
            # teach the freshly generated script the canonical OHOS triplet.
            guess_case = (
                "case $UNAME_MACHINE:$UNAME_SYSTEM:$UNAME_RELEASE:"
                "$UNAME_VERSION in"
            )
            harmony_case = (
                guess_case
                + "\n    *:HarmonyOS:*:* | *:HongMeng:*:*)\n"
                + "\tGUESS=$UNAME_MACHINE-unknown-linux-ohos\n\t;;"
            )
            replace_in_file(self, config_guess, guess_case, harmony_case)
            self.run(f'"{config_sub}" aarch64-unknown-linux-ohos')

        autotools = Autotools(self)
        configure_env = Environment()
        if self._native_ohos_build():
            pkgconf = self.dependencies.build["pkgconf"]
            configure_env.define(
                "PKG_CONFIG",
                os.path.join(pkgconf.package_folder, "bin", "pkgconf"),
            )
        with configure_env.vars(self).apply():
            autotools.configure(build_script_folder=self.source_folder)
        # The tag archive ships config.h.in with a timestamp that can make
        # config.status report an absent config.h as "unchanged". An empty
        # output file forces config.status's content comparison to regenerate
        # the configured header before compilation.
        self.run(": > config.h && ./config.status config.h", cwd=self.build_folder)
        autotools.make(args=["-j1"])

        test_tmpdir = os.path.join(self.build_folder, "upstream-test-tmp")
        os.makedirs(test_tmpdir, exist_ok=True)
        test_env = Environment()
        test_env.define("TMPDIR", test_tmpdir)
        test_env.prepend_path("PATH", os.path.join(self.build_folder, "src"))
        shell = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "sh"
        with test_env.vars(self).apply():
            autotools.make(
                target="check",
                args=["-j1", f"LOG_COMPILER={shell}"],
            )

    def package(self):
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        Autotools(self).install(args=["-j1"])
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["colibricore"]
        self.cpp_info.includedirs = ["include/colibri-core"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.requires = ["bzip2::bzip2"]
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
        self.cpp_info.set_property("cmake_file_name", "colibri-core")
        self.cpp_info.set_property(
            "cmake_target_name", "colibri-core::colibri-core"
        )
        self.cpp_info.set_property("pkg_config_name", "colibri-core")
