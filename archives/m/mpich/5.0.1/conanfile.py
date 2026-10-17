#!/usr/bin/env python3
"""Conan recipe for MPICH 5.0.1."""

import os
import shutil
from shlex import quote

from conan import ConanFile
from conan.tools.files import collect_libs, copy, get, replace_in_file, rm, rmdir
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class MpichConan(ConanFile):
    name = "mpich"
    version = "5.0.1"
    description = "Portable implementation of the Message Passing Interface (MPI)"
    license = "MPICH"
    homepage = "https://www.mpich.org/"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build_requirements(self):
        if str(self.settings_build.os) in ("Linux", "OHOS"):
            self.tool_requires("perl/5.42.2")

    def _config_shell(self):
        configured = os.environ.get("CONFIG_SHELL")
        if configured and os.path.isfile(configured) and os.access(configured, os.X_OK):
            return configured
        return shutil.which("bash") or shutil.which("sh") or "/system/bin/sh"

    def _compiler_executable(self, key, fallback):
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        configured = compilers.get(key)
        candidate = configured
        if not (candidate and os.path.isfile(candidate)):
            candidate = shutil.which(fallback) or configured or fallback
        return self._shell_wrapped(candidate)

    def _tool_executable(self, *names):
        for name in names:
            candidate = shutil.which(name)
            if candidate:
                return self._shell_wrapped(candidate)
        return names[-1]

    def _shell_wrapped(self, candidate):
        if candidate and os.path.isfile(candidate):
            with open(candidate, "r", encoding="utf-8", errors="ignore") as wrapper:
                first_line = wrapper.readline()
            if first_line.startswith("#!") and "/bin/sh" in first_line:
                return f"{self._config_shell()} {candidate}"
        return candidate

    def _relax_autoconf_tmp_permissions(self):
        shell = self._config_shell()
        for root, _, files in os.walk(self.source_folder):
            for filename in files:
                path = os.path.join(root, filename)
                with open(path, "r", encoding="utf-8", errors="ignore") as script:
                    content = script.read()
                relaxed = content
                if filename == "configure":
                    relaxed = relaxed.replace("umask 077", "umask 002")
                first_line, separator, rest = relaxed.partition("\n")
                if first_line.startswith("#!") and "/bin/sh" in first_line:
                    relaxed = f"#!{shell}{separator}{rest}"
                if relaxed != content:
                    with open(path, "w", encoding="utf-8") as script:
                        script.write(relaxed)

    def _configure_args(self):
        shared = bool(self.options.shared)
        args = [
            "--prefix=/",
            "--disable-fortran",
            "--disable-cxx",
            "--disable-romio",
            "--with-device=ch3:sock",
            "--with-pm=gforker",
            "--with-pmi=pmi1",
            "--with-pmilib=install",
            "--with-hwloc=no",
            "--with-wrapper-dl-type=none",
            "--with-datatype-engine=dataloop",
            "--enable-fast=all",
            "--enable-g=none",
            "--enable-shared" if shared else "--disable-shared",
            "--disable-static" if shared else "--enable-static",
        ]
        if self.settings.os in ("Linux", "OHOS"):
            args.append("--build=aarch64-unknown-linux-gnu")
        args.append(f"CONFIG_SHELL={self._config_shell()}")
        return args

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(self._configure_args())
        tc.generate()

    def build(self):
        self._relax_autoconf_tmp_permissions()

        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMPPREFIX"] = os.path.join(tmpdir, "sh")

        bash = self._config_shell()
        cc = self._compiler_executable("c", "clang")
        cxx = self._compiler_executable("cpp", "clang++")
        ar = self._tool_executable("llvm-ar", "ar")
        ranlib = self._tool_executable("llvm-ranlib", "ranlib")
        nm = self._tool_executable("llvm-nm", "nm")
        ld = self._tool_executable("ld.lld", "lld", "ld")
        os.environ["SHELL"] = bash
        os.environ["CONFIG_SHELL"] = bash
        os.environ["CC"] = cc
        os.environ["CXX"] = cxx
        os.environ["AR"] = ar
        os.environ["RANLIB"] = ranlib
        os.environ["NM"] = nm
        os.environ["LD"] = ld

        configure = os.path.join(self.source_folder, "configure")
        configure_args = " ".join(quote(arg) for arg in self._configure_args())
        shell_env = (
            f"SHELL={quote(bash)} CONFIG_SHELL={quote(bash)} "
            f"CC={quote(cc)} CXX={quote(cxx)} "
            f"AR={quote(ar)} RANLIB={quote(ranlib)} NM={quote(nm)} LD={quote(ld)}"
        )
        self.run(f"{shell_env} {quote(bash)} {quote(configure)} {configure_args}", env="conanbuild")
        self.run(
            " ".join([
                "make -j1",
                f"SHELL={quote(bash)}",
                f"CONFIG_SHELL={quote(bash)}",
                f"CC={quote(cc)}",
                f"CXX={quote(cxx)}",
                f"AR={quote(ar)}",
                f"RANLIB={quote(ranlib)}",
                f"NM={quote(nm)}",
                f"LD={quote(ld)}",
            ]),
            env="conanbuild",
        )

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYRIGHT", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        package_root_from_bin = "\n".join([
            'script_dir=$(dirname "$0")',
            'prefix=$(cd "$script_dir/.." && pwd)',
            'exec_prefix=$prefix',
            'sysconfdir=$prefix/etc',
            'includedir=$prefix/include',
            'libdir=$prefix/lib',
        ])
        for wrapper in ("mpicc", "mpicxx", "mpifort"):
            wrapper_path = os.path.join(self.package_folder, "bin", wrapper)
            if os.path.exists(wrapper_path):
                replace_in_file(
                    self,
                    wrapper_path,
                    "prefix=/\nexec_prefix=/\nsysconfdir=//etc\nincludedir=//include\nlibdir=//lib",
                    package_root_from_bin,
                )
        for pattern in ("*.la", "*.dylib"):
            rm(self, pattern, folder=os.path.join(self.package_folder, "lib"))
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        libs = collect_libs(self)
        self.cpp_info.libs = libs or ["mpi"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "MPI")
        self.cpp_info.set_property("cmake_target_name", "MPI::MPI_C")
        self.cpp_info.set_property("pkg_config_name", "mpich")
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
        self.buildenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
