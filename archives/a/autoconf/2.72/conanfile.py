#!/usr/bin/env python3
"""Conan recipe for GNU Autoconf 2.72."""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import copy, export_conandata_patches, get, save
from conan.tools.files import apply_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class AutoconfConan(ConanFile):
    name = "autoconf"
    version = "2.72"
    description = "GNU Autoconf configure script generator"
    license = "GPL-3.0-or-later WITH Autoconf-exception-3.0"
    homepage = "https://www.gnu.org/software/autoconf/"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("perl/5.42.2")
        self.requires("m4/1.4.19")

    def build_requirements(self):
        self.tool_requires("perl/5.42.2")
        self.tool_requires("m4/1.4.19")

    def layout(self):
        basic_layout(self, src_folder=".")
        self.folders.build = "."

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("autoconf recipe supports Linux and OHOS native builds only")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        build_env = VirtualBuildEnv(self)
        shell = self._config_shell()
        env = build_env.environment()
        env.define("SHELL", shell)
        env.define("CONFIG_SHELL", shell)
        build_env.generate()
        run_env = VirtualRunEnv(self)
        run_env.generate()

        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--disable-dependency-tracking")
        tc.configure_args.append("--disable-silent-rules")
        tc.generate()

    def build(self):
        self._prepare_build_environment()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1", "MAKEINFO=true"])

    def package(self):
        self._prepare_build_environment()
        autotools = Autotools(self)
        autotools.install(args=["MAKEINFO=true"])

        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(
            self,
            "COPYING.EXCEPTION",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        self._wrap_perl_tools()

    def _prepare_build_environment(self):
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        shell = self._config_shell()
        os.environ["SHELL"] = shell
        os.environ["CONFIG_SHELL"] = shell
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMPPREFIX"] = os.path.join(tmpdir, "autoconf")
        os.environ.setdefault("M4", "m4")

    def _config_shell(self):
        candidates = [
            os.environ.get("CONFIG_SHELL"),
            os.environ.get("SHELL"),
            shutil.which("sh"),
            "/system/bin/sh",
            "/bin/sh",
            "sh",
        ]
        for candidate in candidates:
            if candidate and (not os.path.isabs(candidate) or os.access(candidate, os.X_OK)):
                return candidate
        return "sh"

    def _wrap_perl_tools(self):
        bindir = os.path.join(self.package_folder, "bin")
        if not os.path.isdir(bindir):
            return

        tools = ("autoconf", "autoheader", "autom4te", "autoreconf", "autoscan", "autoupdate", "ifnames")
        for tool in tools:
            script = os.path.join(bindir, tool)
            if not os.path.isfile(script):
                continue
            real_name = f".{tool}-real"
            real_script = os.path.join(bindir, real_name)
            if os.path.exists(real_script):
                os.remove(real_script)
            os.replace(script, real_script)
            save(self, script, self._tool_wrapper(tool, real_name))
            os.chmod(script, 0o755)
            os.chmod(real_script, 0o755)

    def _tool_wrapper(self, tool, real_name):
        return f"""#!/bin/sh
here=$(CDPATH= cd "$(dirname "$0")" && pwd)
prefix=$(dirname "$here")
share="$prefix/share/autoconf"

: "${{PERL:=perl}}"
: "${{M4:=m4}}"

if [ -n "${{CONFIG_SHELL:-}}" ] && [ ! -x "$CONFIG_SHELL" ]; then
    CONFIG_SHELL=
fi
if [ -z "${{CONFIG_SHELL:-}}" ]; then
    for candidate in "${{SHELL:-}}" /system/bin/sh /bin/sh sh; do
        if [ -z "$candidate" ]; then
            continue
        fi
        case "$candidate" in
            /*) [ -x "$candidate" ] || continue ;;
        esac
        CONFIG_SHELL="$candidate"
        break
    done
fi
: "${{CONFIG_SHELL:=sh}}"
: "${{SHELL:=$CONFIG_SHELL}}"

export SHELL CONFIG_SHELL
export M4
export autom4te_perllibdir="${{autom4te_perllibdir:-$share}}"
export AC_MACRODIR="${{AC_MACRODIR:-$share}}"
export trailer_m4="${{trailer_m4:-$share/autoconf/trailer.m4}}"
export autom4te_buildauxdir="${{autom4te_buildauxdir:-$share/build-aux}}"
export AUTOCONF="${{AUTOCONF:-$here/autoconf}}"
export AUTOHEADER="${{AUTOHEADER:-$here/autoheader}}"
export AUTOM4TE="${{AUTOM4TE:-$here/autom4te}}"
export AUTORECONF="${{AUTORECONF:-$here/autoreconf}}"
export AUTOSCAN="${{AUTOSCAN:-$here/autoscan}}"
export AUTOUPDATE="${{AUTOUPDATE:-$here/autoupdate}}"
export IFNAMES="${{IFNAMES:-$here/ifnames}}"

if [ "{tool}" = "autom4te" ]; then
    exec "$PERL" "$here/{real_name}" --prepend-include "$share" "$@"
fi
exec "$PERL" "$here/{real_name}" "$@"
"""

    def package_info(self):
        bindir = os.path.join(self.package_folder, "bin")
        sharedir = os.path.join(self.package_folder, "share", "autoconf")
        shell = self._config_shell()

        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]

        for env_info in (self.buildenv_info, self.runenv_info):
            env_info.append_path("PATH", bindir)
            env_info.define("SHELL", shell)
            env_info.define("CONFIG_SHELL", shell)
            env_info.define_path("autom4te_perllibdir", sharedir)
            env_info.define_path("AC_MACRODIR", sharedir)
            env_info.define_path("trailer_m4", os.path.join(sharedir, "autoconf", "trailer.m4"))
            env_info.define_path("autom4te_buildauxdir", os.path.join(sharedir, "build-aux"))
            env_info.define_path("AUTOCONF", os.path.join(bindir, "autoconf"))
            env_info.define_path("AUTOHEADER", os.path.join(bindir, "autoheader"))
            env_info.define_path("AUTOM4TE", os.path.join(bindir, "autom4te"))
            env_info.define_path("AUTORECONF", os.path.join(bindir, "autoreconf"))
            env_info.define_path("AUTOSCAN", os.path.join(bindir, "autoscan"))
            env_info.define_path("AUTOUPDATE", os.path.join(bindir, "autoupdate"))
            env_info.define_path("IFNAMES", os.path.join(bindir, "ifnames"))
