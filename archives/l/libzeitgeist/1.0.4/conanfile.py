#!/usr/bin/env python3
"""Conan recipe for libzeitgeist 1.0.4 (Autotools and Vala)."""

import os
import glob
import shlex
import sys

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class LibzeitgeistConan(ConanFile):
    name = "libzeitgeist"
    version = "1.0.4"
    description = "Activity logging library and daemon using the Zeitgeist 2.0 API"
    license = "LGPL-2.1-or-later"
    homepage = "https://launchpad.net/zeitgeist"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)
        self.requires("sqlite/3.53.3", transitive_headers=True, transitive_libs=True)

    def build_requirements(self):
        self.tool_requires("vala/0.56.18")
        self.tool_requires("python3-rdflib/7.1.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _write_sqlite_pc(self):
        sqlite = self.dependencies["sqlite"]
        sqlite_root = sqlite.package_folder
        pc = os.path.join(self.generators_folder, "sqlite3.pc")
        with open(pc, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(
                "prefix={0}\n"
                "exec_prefix=${{prefix}}\n"
                "libdir=${{exec_prefix}}/lib\n"
                "includedir=${{prefix}}/include\n"
                "Name: sqlite3\n"
                "Description: SQLite database engine\n"
                "Version: 3.53.3\n"
                "Libs: -L${{libdir}} -lsqlite3\n"
                "Cflags: -I${{includedir}}\n".format(sqlite_root)
            )

    def _build_env(self):
        env = Environment()
        # R33: never fall back to a bare "clang" name — non-interactive CI
        # shells do not have the toolchain bindir on PATH.  Prefer the
        # profile's absolute compiler_executables, then a pre-set CC/CXX.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c") or os.environ.get("CC")
        cxx = compilers.get("cpp") or os.environ.get("CXX")
        if cc:
            env.define("CC", cc)
        if cxx:
            env.define("CXX", cxx)
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        env.define("TEMP", tmpdir)
        env.append_path("PKG_CONFIG_PATH", self.generators_folder)
        for dep in self.dependencies.values():
            if not dep.package_folder:
                continue
            pkg_dir = os.path.join(dep.package_folder, "lib", "pkgconfig")
            if os.path.isdir(pkg_dir):
                env.append_path("PKG_CONFIG_PATH", pkg_dir)
            for lib_dir in dep.cpp_info.libdirs:
                env.append_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, lib_dir))
        for site in self._python_build_paths():
            env.prepend_path("PYTHONPATH", site)
        return env

    def _python_build_paths(self):
        paths = []
        for dep in self.dependencies.build.values():
            site = os.path.join(
                dep.package_folder,
                "lib",
                f"python{sys.version_info.major}.{sys.version_info.minor}",
                "site-packages",
            )
            if os.path.isdir(site):
                paths.append(site)
        return paths

    def _write_python_wrapper(self, python_paths):
        if not python_paths:
            return None
        tools_dir = os.path.join(self.build_folder, "ohos-build-tools")
        os.makedirs(tools_dir, exist_ok=True)
        wrapper = os.path.join(tools_dir, "python-rdflib")
        path_value = os.pathsep.join(python_paths)
        with open(wrapper, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(
                "#!/bin/sh\n"
                "PYTHONPATH=\"{0}\" exec \"{1}\" \"$@\"\n".format(
                    path_value, sys.executable
                )
            )
        os.chmod(wrapper, 0o755)
        return wrapper

    def _vala_flags(self):
        vapidirs = []
        for dep in list(self.dependencies.build.values()) + list(self.dependencies.host.values()):
            if not dep.package_folder:
                continue
            for pattern in (
                os.path.join(dep.package_folder, "share", "vala*", "vapi"),
            ):
                vapidirs.extend(glob.glob(pattern))
        return ["--vapidir={}".format(path) for path in dict.fromkeys(vapidirs)]

    def _vala_assignment(self, extra_flags):
        flags = [
            "--target-glib=2.36",
            "--pkg",
            "gio-2.0",
            "--pkg",
            "gio-unix-2.0",
            "--pkg",
            "sqlite3",
            os.path.join(self.source_folder, "config.vapi"),
            "-C",
        ]
        if str(self.settings.os) == "OHOS":
            flags.append("--define=OHOS")
        flags.extend(self._vala_flags())
        flags.extend(extra_flags)
        return "AM_VALAFLAGS={}".format(shlex.quote(" ".join(flags)))

    def generate(self):
        PkgConfigDeps(self).generate()
        self._write_sqlite_pc()
        env = self._build_env()
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(
            [
                "--disable-fts",
                "--disable-datahub",
                "--disable-telepathy",
                "--disable-downloads-monitor",
                "--disable-docs",
                "--disable-introspection",
            ]
        )
        if not self.options.shared:
            tc.configure_args.extend(["--disable-shared", "--enable-static"])
        tc.generate(env=env)

    def build(self):
        apply_conandata_patches(self)
        # HNP bash may call getcwd() after Conan changes cwd.  Exporting the
        # actual build path lets Autoconf retain the cwd on OHOS/HMDFS.
        os.environ["PWD"] = str(self.build_folder)
        python_paths = self._python_build_paths()
        self.output.info("Python build paths: {}".format(python_paths))
        python_wrapper = self._write_python_wrapper(python_paths)
        if python_paths:
            existing = os.environ.get("PYTHONPATH")
            os.environ["PYTHONPATH"] = os.pathsep.join(
                python_paths + ([existing] if existing else [])
            )
        env = self._build_env()
        autotools = Autotools(self)
        build_root = self.build_folder
        with env.vars(self).apply():
            configure_args = []
            if python_wrapper:
                configure_args.append("PYTHON={}".format(python_wrapper))
            autotools.configure(args=configure_args)
            # Some OHOS Conan dependencies ship libtool .la files with a
            # baked-in /lib prefix.  libtool follows those archives to //lib
            # and fails; Conan metadata already provides the links.
            for dep in self.dependencies.values():
                if not dep.package_folder:
                    continue
                for libdir in dep.cpp_info.libdirs:
                    for la_file in glob.glob(os.path.join(dep.package_folder, libdir, "*.la")):
                        os.remove(la_file)
            # Each Vala subdirectory has additional flags in its Makefile.am.
            # A command-line AM_VALAFLAGS replaces those values, so generate
            # the dependent VAPI files in dependency order with directory-
            # specific additions before the final recursive build.
            autotools.make(
                args=["-C", "libzeitgeist", "-j1", self._vala_assignment([])],
            )
            core_vapis = [
                os.path.join(
                    build_root, "libzeitgeist", name
                )
                for name in (
                    "zeitgeist-internal.vapi",
                    "zeitgeist-datamodel-2.0.vapi",
                    "zeitgeist-2.0.vapi",
                )
            ]
            autotools.make(
                args=[
                    "-C",
                    "src",
                    "-j1",
                    self._vala_assignment(
                        ["--pkg", "posix", "--pkg", "gmodule-2.0"] + core_vapis
                    ),
                ],
            )
            autotools.make(
                args=[
                    "-C",
                    "extensions",
                    "-j1",
                    "top_builddir={}".format(build_root),
                    self._vala_assignment(
                        ["--pkg", "gmodule-2.0"]
                        + core_vapis
                        + [
                            os.path.join(
                                build_root,
                                "src",
                                "zeitgeist-engine.vapi",
                            )
                        ]
                    ),
                ],
            )
            autotools.make(
                args=[
                    "-j1",
                    "top_builddir={}".format(build_root),
                    self._vala_assignment(
                        ["--pkg", "posix", "--pkg", "gmodule-2.0"]
                        + core_vapis
                        + [
                            os.path.join(
                                build_root,
                                "src",
                                "zeitgeist-engine.vapi",
                            )
                        ]
                    ),
                ],
            )

    def package(self):
        Autotools(self).install(args=["-j1"])
        la_file = os.path.join(self.package_folder, "lib", "libzeitgeist-2.0.la")
        if os.path.isfile(la_file):
            os.remove(la_file)

    def package_info(self):
        self.cpp_info.libs = ["zeitgeist-2.0"]
        self.cpp_info.includedirs = ["include/zeitgeist-2.0"]
        self.cpp_info.requires = ["glib::glib", "sqlite::sqlite"]
        self.cpp_info.set_property("pkg_config_name", "zeitgeist-2.0")
        self.cpp_info.set_property("cmake_file_name", "libzeitgeist")
        self.cpp_info.set_property("cmake_target_name", "libzeitgeist::libzeitgeist")
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
