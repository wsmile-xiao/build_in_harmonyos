#!/usr/bin/env python3
"""Conan recipe for cpdb-libs 1.2.0 using Autotools.

The upstream v1.2.0 tag ships no release dist tarball, so conandata.yml
points at the official GitHub archive.  That archive contains only
configure.ac / Makefile.am (no generated configure / Makefile.in), so the
build self-bootstraps with autoreconf using the published automake and
libtool tool packages.
"""

import os
import shlex
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    load,
    rm,
    save,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class CpdbLibsConan(ConanFile):
    name = "cpdb-libs"
    version = "1.2.0"
    description = "OpenPrinting Common Print Dialog Backends libraries"
    license = "MIT"
    homepage = "https://github.com/OpenPrinting/cpdb-libs"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # The v1.2.0 git archive contains no generated configure/Makefile.in,
        # so build() must self-bootstrap with autoreconf.  The CI worker
        # provides autoconf/autoreconf/m4 but no aclocal/automake/libtoolize;
        # automake/1.18 ships aclocal+automake and libtool/2.5.4 ships
        # libtoolize (published in the ohpcd registry).  autoconf is not
        # declared because the SDK already provides it (same precedent as
        # accel-config/abiword).
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def requirements(self):
        self.requires("glib/2.88.3", transitive_headers=True, transitive_libs=True)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "cpdb-libs supports Linux and HarmonyOS-compatible POSIX targets"
            )
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(
                "The HarmonyOS package is validated for AArch64"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _bootstrap_autotools(self):
        """Run autoreconf when the archive ships no generated configure."""
        configure = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure):
            return
        autogen = os.path.join(self.source_folder, "autogen.sh")
        shell = shutil.which("bash") or shutil.which("sh")
        if not shell:
            raise ConanInvalidConfiguration("A POSIX shell is required")
        if os.path.isfile(autogen):
            self.run("{} -e {}".format(shlex.quote(shell), shlex.quote(autogen)),
                     cwd=self.source_folder, env="conanbuild")
        else:
            self.run("autoreconf -fi", cwd=self.source_folder, env="conanbuild")
        if not os.path.isfile(configure):
            raise ConanInvalidConfiguration(
                "autoreconf did not produce configure; see build log")

    def _create_mktemp_wrapper(self):
        """Build-only mktemp wrapper (never committed).

        config.status in the generated configure runs
        ``(umask 077 && mktemp -d "./confXXXXXX")``.  On OHOS/HMDFS the
        toybox mktemp creates drwx--S--- directories that the build user
        cannot write into (remote CI: "confGfDnfg/subs1.awk: Permission
        denied / could not setup config files machinery"), while a plain
        mkdir produces drwxrws--x directories that stay writable.  The
        wrapper emulates ``mktemp -d`` with mkdir and prints the created
        path; non ``-d`` invocations and bad arguments are forwarded to the
        real mktemp, preserving exit codes.  It only affects the configure
        subprocess via a PATH prepend scoped to the conanbuild environment;
        nothing is written to system dirs (R6: no generated file modified).
        """
        wrapper_dir = os.path.join(self.build_folder, "mktemp-wrapper")
        os.makedirs(wrapper_dir, exist_ok=True)
        wrapper = os.path.join(wrapper_dir, "mktemp")
        if not os.path.exists(wrapper):
            with open(wrapper, "w", encoding="utf-8") as f:
                f.write("""#!/bin/sh
mode=""
for a in "$@"; do
  case "$a" in
    -d) mode="-d" ;;
  esac
done
if [ "$mode" != "-d" ]; then
  exec /usr/bin/mktemp "$@"
fi
dir=""
for a in "$@"; do
  case "$a" in
    -d) ;;
    *)  dir="$a" ;;
  esac
done
[ -n "$dir" ] || dir="./tmp.XXXXXX"
base=$(dirname "$dir")
pat=$(basename "$dir")
out=""
i=0
while [ -z "$out" ] && [ $i -lt 100 ]; do
  cand="$base/$(echo "$pat" | sed "s/XXXXXX/$$-$RANDOM/")"
  if (umask 077 && mkdir -p "$cand" 2>/dev/null); then out="$cand"; fi
  i=$((i+1))
done
if [ -n "$out" ]; then
  echo "$out"
  exit 0
fi
exit 1
""")
            os.chmod(wrapper, 0o755)
        return wrapper_dir

    def generate(self):
        PkgConfigDeps(self).generate()

        glib_package = self.dependencies["glib"].package_folder
        gio_unix_pc = os.path.join(
            glib_package, "lib", "pkgconfig", "gio-unix-2.0.pc"
        )
        if not os.path.isfile(gio_unix_pc):
            raise ConanInvalidConfiguration(
                "glib/2.88.3 does not provide gio-unix-2.0.pc"
            )
        gio_unix_metadata = load(self, gio_unix_pc)
        if "prefix=/\n" not in gio_unix_metadata:
            raise ConanInvalidConfiguration(
                "glib/2.88.3 gio-unix-2.0.pc has an unexpected prefix"
            )
        gio_unix_metadata = gio_unix_metadata.replace(
            "prefix=/\n", "prefix={}\n".format(glib_package), 1
        )
        save(
            self,
            os.path.join(self.generators_folder, "gio-unix-2.0.pc"),
            gio_unix_metadata,
        )

        toolchain = AutotoolsToolchain(self)
        toolchain.configure_args.append("--disable-nls")
        if self.settings.os == "OHOS":
            toolchain.configure_args.extend(
                [
                    "--build=aarch64-unknown-linux-gnu",
                    "--host=aarch64-unknown-linux-gnu",
                ]
            )
        if self.options.shared:
            toolchain.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            toolchain.configure_args.extend(["--disable-shared", "--enable-static"])

        environment = toolchain.environment()
        environment.prepend_path("PATH", os.path.join(glib_package, "bin"))
        if self.settings.os == "OHOS":
            # config.status creates 0700 temp dirs via toybox mktemp that the
            # HMDFS build user cannot write into (remote CI
            # "conf*/subs1.awk: Permission denied"); emulate mktemp -d with
            # plain mkdir so the autoconf temp dir stays writable.
            environment.prepend_path("PATH", self._create_mktemp_wrapper())
        environment.define("ac_cv_func_malloc_0_nonnull", "yes")
        if self.settings.os == "OHOS":
            # config.status creates 0700 temp dirs that the HMDFS build user
            # cannot write into; keep autoconf/autoreconf/configure temp files
            # inside the isolated Conan build directory instead.
            tmpdir = os.path.join(self.build_folder, "tmp")
            os.makedirs(tmpdir, exist_ok=True)
            environment.define_path("TMPDIR", tmpdir)
            environment.define_path("TMP", tmpdir)
            environment.define_path("TEMP", tmpdir)
            environment.define_path("TMPPREFIX", os.path.join(tmpdir, "zsh"))

            # The SDK copy of gdbus-codegen has a fixed /usr/bin/python3
            # shebang, but HarmonyOS provides the interpreter elsewhere.
            # Invoke the GLib package script with the interpreter already
            # running Conan, and discard the target-library search path
            # because this generator is pure Python.
            gdbus_codegen = os.path.join(glib_package, "bin", "gdbus-codegen")
            if not os.path.isfile(gdbus_codegen):
                raise ConanInvalidConfiguration(
                    "glib/2.88.3 does not provide gdbus-codegen"
                )
            python = os.path.realpath(sys.executable)
            if not python or not os.path.isfile(python):
                raise ConanInvalidConfiguration(
                    "A runnable Python 3 interpreter is required by gdbus-codegen"
                )
            environment.define(
                "GDBUS_CODEGEN",
                "LD_LIBRARY_PATH= {} {}".format(
                    shlex.quote(python),
                    shlex.quote(gdbus_codegen),
                ),
            )

        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = compilers.get("c") or ""
        tool_directory = os.path.dirname(compiler)
        for variable, executable in (
            ("AR", "llvm-ar"),
            ("RANLIB", "llvm-ranlib"),
            ("NM", "llvm-nm"),
            ("STRIP", "llvm-strip"),
        ):
            tool = compilers.get(variable.lower()) or os.path.join(
                tool_directory, executable
            )
            if tool_directory and os.path.isfile(tool):
                environment.define(variable, tool)

        for dependency in self.dependencies.host.values():
            if not dependency.package_folder:
                continue
            for libdir in dependency.cpp_info.libdirs:
                path = libdir if os.path.isabs(libdir) else os.path.join(
                    dependency.package_folder, libdir
                )
                if os.path.isdir(path):
                    environment.prepend_path("LD_LIBRARY_PATH", path)
        toolchain.generate(environment)

    def build(self):
        apply_conandata_patches(self)
        self._bootstrap_autotools()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        autotools.make(target="check", args=["-j1"])

    def package(self):
        Autotools(self).install()
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        copy(
            self,
            "LICENSE.md",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "cpdb-libs")
        self.cpp_info.set_property("cmake_target_name", "cpdb-libs::cpdb-libs")
        self.cpp_info.bindirs = []

        common = self.cpp_info.components["cpdb-libs-common"]
        common.libs = ["cpdb-libs-common"]
        common.requires = ["glib::glib", "glib::gobject", "glib::gio"]
        common.set_property("cmake_target_name", "cpdb-libs::common")
        common.set_property("pkg_config_name", "cpdb-libs-common")

        frontend = self.cpp_info.components["cpdb-libs-frontend"]
        frontend.libs = ["cpdb-libs-frontend"]
        frontend.requires = [
            "cpdb-libs-common",
            "glib::glib",
            "glib::gobject",
            "glib::gio",
        ]
        frontend.system_libs = ["pthread", "m", "crypt"]
        frontend.set_property("cmake_target_name", "cpdb-libs::frontend")
        frontend.set_property("pkg_config_name", "cpdb-libs-frontend")

        self.cpp_info.requires = ["cpdb-libs-common", "cpdb-libs-frontend"]
