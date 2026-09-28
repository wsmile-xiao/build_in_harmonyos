#!/usr/bin/env python3
"""Conan recipe — gnutrition 0.33 (Autotools, GTK3 application)

GNUtrition is a diet analysis GUI program built on gtk+-3.0 / gio-2.0 and
sqlite3 (all PKG_CHECK_MODULES hard requirements in configure.ac). The GNU
release tarball ships a pre-generated configure, but its config.guess/sub
predate HarmonyOS, so the OHOS-aware replacement (E007) and the HMDFS
PWD/ac_pwd + umask adaptations (E011, adms/2.3.7 + dcfldd/1.9.3 precedents)
are applied at build time.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class GnutritionConan(ConanFile):
    name = "gnutrition"
    version = "0.33"
    description = "GNUtrition 0.33 — diet analysis GUI application (GTK3)"
    license = "GPL-3.0-or-later"
    homepage = "http://www.gnu.org/software/gnutrition/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        # R32: settings.os must be Linux or OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # PKG_CHECK_MODULES hard requirements from configure.ac
        self.requires("gtk/3.24.43")
        self.requires("sqlite3/3.49.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # PKG_CHECK_MODULES needs gtk+-3.0.pc / gio-2.0.pc / sqlite3.pc; the
        # gtk recipe sets pkg_config_name="gtk+-3.0" and glib provides
        # gio-2.0.pc. PkgConfigDeps emits the .pc files and the toolchain
        # env points pkg-config at them.
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        # configure sanity-check RUNS its conftest; the loader must find
        # the glib proxy libintl.so (not in the default OHOS loader path)
        # or configure bails with "cannot run C compiled programs".
        glib_dep = self.dependencies["glib"]
        glib_libdir = os.path.join(glib_dep.package_folder,
                                   glib_dep.cpp_info.libdirs[0])
        tc.extra_ldflags.append(f"-L{glib_libdir}")
        tc.extra_ldflags.append("-lintl")
        tc.generate()
        env = Environment()
        env.prepend_path("LD_LIBRARY_PATH", glib_libdir)
        env.vars(self).save_script("conanbuild_glib_intl")

    def build(self):
        apply_conandata_patches(self)

        autotools = Autotools(self)

        # E490: restore exec bits HMDFS adaptation paths may have dropped.
        for _script in ("configure", "config.guess", "config.sub", "install-sh",
                        "missing", "compile", "depcomp", "ltmain.sh"):
            _path = os.path.join(self.source_folder, _script)
            if os.path.exists(_path):
                os.chmod(_path, 0o755)

        # E007: the shipped config.guess/sub predate HarmonyOS; replace
        # with self-contained OHOS-aware versions.
        self._replace_config_for_ohos()

        # HMDFS getcwd fix (adms/2.3.7): preset PWD (shell pwd builtin uses
        # the logical path) and give configure's ac_pwd probe a $PWD fallback;
        # config.status tmp dirs umask 077 -> 022 (E011: HMDFS setgid dirs
        # are unwritable even for the owner at 077).
        os.environ["PWD"] = self.build_folder
        _configure = os.path.join(self.source_folder, "configure")
        with open(_configure) as f:
            _cfg = f.read()
        _cfg = _cfg.replace(
            "ac_pwd=`pwd` && test -n \"$ac_pwd\" &&",
            "ac_pwd=`pwd` 2>/dev/null || ac_pwd=$PWD\ntest -n \"$ac_pwd\" &&",
        )
        _cfg = _cfg.replace("umask 077", "umask 022")
        with open(_configure, "w") as f:
            f.write(_cfg)

        autotools.configure()
        autotools.make(args=["-j1"])

    def _replace_config_for_ohos(self):
        """Replace config.guess/config.sub with OHOS-aware versions (E007)."""
        _guess = os.path.join(self.source_folder, "config.guess")
        _sub_path = os.path.join(self.source_folder, "config.sub")
        if not os.path.isfile(_guess) and not os.path.isfile(_sub_path):
            return

        ohos_config_guess = (
            '#!/bin/sh\n'
            '# OHOS-aware config.guess (self-contained)\n'
            'machine=$(uname -m 2>/dev/null || echo unknown)\n'
            'system=$(uname -s 2>/dev/null || echo unknown)\n'
            'case "$system" in\n'
            '    HarmonyOS|OHOS)\n'
            '        echo "${machine}-unknown-linux-ohos"\n'
            '        ;;\n'
            '    *)\n'
            '        echo "${machine}-unknown-linux-gnu"\n'
            '        ;;\n'
            'esac\n'
            'exit 0\n'
        )
        with open(_guess, "w") as f:
            f.write(ohos_config_guess)
        os.chmod(_guess, 0o755)

        ohos_config_sub = (
            '#!/bin/sh\n'
            '# OHOS-aware config.sub (self-contained)\n'
            '# Always pass through the input triplet\n'
            'if [ $# -eq 0 ] || [ -z "$1" ]; then\n'
            '    echo "aarch64-unknown-linux-ohos"\n'
            '    exit 0\n'
            'fi\n'
            'echo "$1"\n'
            'exit 0\n'
        )
        with open(_sub_path, "w") as f:
            f.write(ohos_config_sub)
        os.chmod(_sub_path, 0o755)

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # GUI application only: the installed artifact is the gnutrition
        # executable in bin/ (R38 tool — commands.json at software level).
        self.cpp_info.bindirs = ["bin"]
