#!/usr/bin/env python3
"""Conan recipe for avr-libc 2.2.1.

The package is built on Linux/OHOS, but its headers, startup objects and
archives target AVR microcontrollers.  They must never be exposed as native
OHOS link libraries.
"""

import glob
import os
import shlex
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.gnu.get_gnu_triplet import _get_gnu_triplet
from conan.tools.layout import basic_layout


class AvrLibcConan(ConanFile):
    name = "avr-libc"
    version = "2.2.1"
    description = "C runtime library for AVR microcontrollers"
    license = "BSD-3-Clause"
    homepage = "https://github.com/avrdudes/avr-libc"
    # AVR target sysroot resources, neither an OHOS library nor a CLI tool.
    package_type = "unknown"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "avr-libc can only be built with the AVR cross-toolchain on Linux/OHOS"
            )

    def build_requirements(self):
        # W0: the two AVR packages are intentionally separate adaptations.
        # Neither recipe is published on ohpcd as of 2026-08-17.
        self.tool_requires("avr-binutils/2.43.1")
        self.tool_requires("avr-gcc-bootstrap/14.2.0")
        self.tool_requires("autoconf/2.72")
        self.tool_requires("automake/1.18")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        dispatcher_bin = self._materialize_target_tool_root()
        tools = {
            "CC": self._required_build_tool("avr-gcc"),
            "AS": self._required_build_tool("avr-as"),
            "AR": self._required_build_tool("avr-ar"),
            "LD": self._required_build_tool("avr-ld"),
            "NM": self._required_build_tool("avr-nm"),
            "OBJCOPY": self._required_build_tool("avr-objcopy"),
            "OBJDUMP": self._required_build_tool("avr-objdump"),
            "RANLIB": self._required_build_tool("avr-ranlib"),
            "STRIP": self._required_build_tool("avr-strip"),
        }
        compiler = shlex.join(
            [tools["CC"], "-B{}{}".format(dispatcher_bin, os.sep)]
        )

        build_env = VirtualBuildEnv(self)
        env = build_env.environment()
        for variable, executable in tools.items():
            env.define(
                variable, compiler if variable == "CC" else executable
            )
        env.define("CCAS", compiler)
        env.define("AVR_GCC", compiler)
        env.define("AVR_NM", tools["NM"])
        env.define("AVR_OBJCOPY", tools["OBJCOPY"])
        env.define("PYTHON", sys.executable)
        autotools_scripts = {
            name: self._required_build_script(name)
            for name in ("aclocal", "autoheader", "autoconf", "automake")
        }
        # Conan's Autotools packages install wrapper and real Perl scripts with
        # mode 0640 on HMDFS.  Invoke the real scripts through an executable
        # HNP Perl runtime instead of relying on either file's execute bit.
        perl = self._required_build_script("perl")
        m4 = self._required_build_script("m4")
        m4_runtime = ("/data/service/hnp/bin/m4" if self.settings.os == "OHOS" else m4)
        if self.settings.os == "OHOS":
            perl_runtime = os.path.join(self.build_folder, ".conan-perl")
            shutil.copy2(perl, perl_runtime)
            os.chmod(perl_runtime, 0o755)
        else:
            perl_runtime = perl
        autoconf_bin = os.path.dirname(autotools_scripts["autoconf"])
        automake_bin = os.path.dirname(autotools_scripts["aclocal"])
        autoheader_real = os.path.join(autoconf_bin, ".autoheader-real")
        if self.settings.os == "OHOS":
            autoheader_real = os.path.join(self.build_folder, ".autoheader-real")
            shutil.copy2(
                os.path.join(autoconf_bin, ".autoheader-real"), autoheader_real
            )
            replace_in_file(
                self,
                autoheader_real,
                'my $autoconf = "\'$autom4te\' --language=autoconf ";',
                'my $autoconf = "$autom4te --language=autoconf ";',
            )
        autom4te_command = shlex.join(
            [
                perl_runtime,
                os.path.join(autoconf_bin, ".autom4te-real"),
                "--prepend-include",
                os.path.join(os.path.dirname(autoconf_bin), "share", "autoconf"),
            ]
        )
        env.define("AUTOM4TE", autom4te_command)
        env.define("M4", m4_runtime)
        autotools_commands = {
            "ACLOCAL": shlex.join(
                [
                    perl_runtime,
                    os.path.join(automake_bin, ".aclocal-real"),
                    "--automake-acdir={}".format(
                        os.path.join(os.path.dirname(automake_bin), "share", "aclocal-1.18")
                    ),
                    "--system-acdir={}".format(
                        os.path.join(os.path.dirname(automake_bin), "share", "aclocal")
                    ),
                ]
            ),
            "AUTOHEADER": shlex.join(
                [perl_runtime, autoheader_real]
            ),
            "AUTOCONF": shlex.join(
                [perl_runtime, os.path.join(autoconf_bin, ".autoconf-real")]
            ),
            "AUTOMAKE": shlex.join(
                [
                    perl_runtime,
                    os.path.join(automake_bin, ".automake-real"),
                    "--libdir={}".format(
                        os.path.join(os.path.dirname(automake_bin), "share", "automake-1.18")
                    ),
                ]
            ),
        }
        for variable, command in autotools_commands.items():
            env.define(variable, command)
        build_env.generate()

        tc = AutotoolsToolchain(self)
        build_triplet = _get_gnu_triplet(
            str(self.settings.os),
            str(self.settings.arch),
            str(self.settings.compiler),
        )["triplet"]
        tc.configure_args.extend(
            [
                "--build={}".format(build_triplet),
                "--host=avr",
                "--disable-doc",
                "--disable-html-doc",
                "--disable-pdf-doc",
                "--disable-man-doc",
            ]
        )
        # AutotoolsToolchain normally rewrites CC/CXX from the OHOS profile.
        # Override that generator environment as well as VirtualBuildEnv so
        # its later activation cannot replace avr-gcc with native clang.
        tc_env = tc.environment()
        for variable, executable in tools.items():
            tc_env.define(
                variable, compiler if variable == "CC" else executable
            )
        tc_env.define("CCAS", compiler)
        tc_env.define("M4", m4_runtime)
        tc.generate(env=tc_env)

    def build(self):
        apply_conandata_patches(self)

        # The authoritative tag snapshot does not contain generated top-level
        # configure/Makefile.in files.  bootstrap also generates the AVR
        # device and multilib source trees before running Autoconf/Automake.
        bootstrap = os.path.join(self.source_folder, "bootstrap")
        if self.settings.os == "OHOS":
            devtools_configure = os.path.join(
                self.source_folder, "devtools", "configure"
            )
            # E114: HMDFS turns Autoconf's umask-077 temp directory into
            # an unwritable setgid directory, so config.status cannot create
            # subs1.awk.  Preserve the random directory but use the runner's
            # normal umask instead.
            replace_in_file(
                self,
                devtools_configure,
                'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
                'tmp=`mktemp -d "./confXXXXXX" 2>/dev/null`',
            )
            replace_in_file(
                self,
                devtools_configure,
                '(umask 077 && mkdir "$tmp")',
                'mkdir "$tmp"',
            )
        replace_in_file(
            self,
            bootstrap,
            "(cd devtools; ./configure)",
            "(cd devtools; sh ./configure)",
        )
        replace_in_file(
            self,
            bootstrap,
            "./devtools/gen-avr-lib-tree.sh || exit 1",
            "sh ./devtools/gen-avr-lib-tree.sh || exit 1",
        )
        self.run("sh bootstrap", cwd=self.source_folder, env="conanbuild")

        autotools = Autotools(self)
        configure_script = os.path.join(self.source_folder, "configure")
        self.run(
            "sh {} {}".format(
                shlex.quote(configure_script), autotools._configure_args
            ),
            cwd=self.build_folder,
            env="conanbuild",
        )
        autotools.make(args=["-j1"])

        # The complete upstream suite requires avrtest or simulavr.  Keep a
        # representative compile/link subset in the build so the generated
        # libc, libm, CRT and device archive are all exercised without running
        # AVR machine code on the OHOS host.
        tests = os.path.join(self.source_folder, "tests", "simulate")
        command = (
            'sh runtest.sh -c -a "{}" '
            "string/strcmp.c stdlib/atoi-1.c math/cos-01.c"
        ).format(self.build_folder)
        self.run(command, cwd=tests, env="conanbuild")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        self._validate_packaged_artifacts()

    def package_info(self):
        # These are AVR target artifacts, not native OHOS libraries.  Consumers
        # must use AVR tools and explicit paths (or AVR_LIBC_ROOT).
        # The package contains no native executable payload.
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.resdirs = ["avr"]
        self.buildenv_info.define_path(
            "AVR_LIBC_ROOT", os.path.join(self.package_folder, "avr")
        )

    def _materialize_target_tool_root(self):
        binutils_root = self.dependencies.build[
            "avr-binutils"
        ].package_folder
        root = os.path.join(
            self.build_folder, ".avr-binutils-dispatch"
        )
        bin_dir = os.path.join(root, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        for name in ("as", "ld", "nm"):
            shutil.copy2(
                os.path.join(binutils_root, "bin", "avr-{}".format(name)),
                os.path.join(bin_dir, name),
            )

        source_scripts = os.path.join(
            binutils_root, "avr", "lib", "ldscripts"
        )
        if not os.path.isdir(source_scripts):
            raise ConanInvalidConfiguration(
                "AVR linker scripts were not found: {}".format(
                    source_scripts
                )
            )
        shutil.copytree(
            source_scripts,
            os.path.join(root, "avr", "lib", "ldscripts"),
            dirs_exist_ok=True,
        )
        return bin_dir

    def _required_build_tool(self, executable):
        for dependency in self.dependencies.build.values():
            package_folder = dependency.package_folder
            if not package_folder:
                continue
            candidate = os.path.join(package_folder, "bin", executable)
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
        raise ConanInvalidConfiguration(
            "Required AVR tool '{}' was not provided by tool_requires".format(executable)
        )

    def _required_build_script(self, executable):
        for dependency in self.dependencies.build.values():
            package_folder = dependency.package_folder
            if not package_folder:
                continue
            candidate = os.path.join(package_folder, "bin", executable)
            if os.path.isfile(candidate):
                return candidate
        raise ConanInvalidConfiguration(
            "Required build script '{}' was not provided by tool_requires".format(executable)
        )

    def _validate_packaged_artifacts(self):
        avr_root = os.path.join(self.package_folder, "avr")
        required_header = os.path.join(avr_root, "include", "avr", "version.h")
        if not os.path.isfile(required_header):
            raise ConanInvalidConfiguration(
                "Packaged avr-libc version header is missing: {}".format(required_header)
            )
        for archive in ("libc.a", "libm.a"):
            if not glob.glob(os.path.join(avr_root, "lib", "**", archive), recursive=True):
                raise ConanInvalidConfiguration(
                    "Packaged AVR archive is missing: {}".format(archive)
                )
        if not glob.glob(os.path.join(avr_root, "lib", "**", "crt*.o"), recursive=True):
            raise ConanInvalidConfiguration("Packaged AVR startup objects are missing")
