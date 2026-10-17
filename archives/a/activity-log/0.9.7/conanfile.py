#!/usr/bin/env python3
"""Conan recipe for activity-log-manager 0.9.7.

The release is an Autotools GTK application with Vala sources and pre-generated
C files.  Optional control-center, Whoopsie, and Switchboard integrations are
disabled because they are not part of the standalone OHOS package.
"""
import filecmp
import os
import shutil
import stat

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


def prepend_probe_path(probe_dir, current_path):
    """Keep recipe-local configure probes ahead of worker tools."""
    if not current_path:
        return probe_dir
    return os.pathsep.join((probe_dir, current_path))


class ActivityLogManagerConan(ConanFile):
    name = "activity-log"
    version = "0.9.7"
    description = "GTK activity log and privacy manager"
    license = "LGPL-2.0-or-later"
    homepage = "https://launchpad.net/activity-log-manager"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "activity-log-manager is supported only on Linux and OHOS"
            )

    def requirements(self):
        self.requires("libgee/0.6.8", transitive_headers=True, transitive_libs=True)
        self.requires("libzeitgeist/1.0.4", transitive_headers=True, transitive_libs=True)
        self.requires("gtk/3.24.43", transitive_headers=True, transitive_libs=True)
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)
        # The OHOS GLib package exposes libpcre2-8 in its public pkg-config
        # requirements, so keep the provider in the host graph.
        self.requires("pcre2/10.45", transitive_headers=True, transitive_libs=True)
        # gobject-2.0.pc likewise exposes libffi as a public requirement.
        self.requires("libffi/3.4.4", transitive_headers=True, transitive_libs=True)
        # harfbuzz.pc exposes graphite2 as a public pkg-config requirement.
        self.requires("graphite2/1.3.14", transitive_headers=True, transitive_libs=True)
        # libtiff-4.pc exposes liblzma as a public pkg-config requirement.
        self.requires("xz/5.6.2", transitive_headers=True, transitive_libs=True)

    def build_requirements(self):
        # The generated C files are shipped, but the Automake Vala stamp can
        # regenerate them.  Keep that path reproducible in a clean worker.
        self.tool_requires("vala/0.56.18")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _build_env(self):
        env = Environment()
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        env.define("TEMP", tmpdir)
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        if compiler_executables.get("c"):
            env.define("CC", compiler_executables["c"])
        if compiler_executables.get("cpp"):
            env.define("CXX", compiler_executables["cpp"])
        for dep in self.dependencies.host.values():
            if not dep.package_folder:
                continue
            pc_dir = os.path.join(dep.package_folder, "lib", "pkgconfig")
            if os.path.isdir(pc_dir):
                env.prepend_path("PKG_CONFIG_PATH", pc_dir)

        # Prefer Conan's absolute-path .pc files over package-local files that
        # may still contain the original prefix from the producer build.
        env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)

        for dep in self.dependencies.build.values():
            if not dep.package_folder:
                continue
            bin_dir = os.path.join(dep.package_folder, "bin")
            if os.path.isdir(bin_dir):
                env.prepend_path("PATH", bin_dir)

        return env

    def _stage_dependency_libraries(self):
        """Expose only .la-affected host libraries without their metadata."""
        stage_dir = os.path.join(self.build_folder, "dependency-libs")
        os.makedirs(stage_dir, exist_ok=True)
        staged_packages = set()

        for dep in self.dependencies.host.values():
            if not dep.package_folder:
                continue
            lib_dir = os.path.join(dep.package_folder, "lib")
            if not os.path.isdir(lib_dir):
                continue
            if not any(name.endswith(".la") for name in os.listdir(lib_dir)):
                continue
            staged_packages.add(os.path.normpath(dep.package_folder))
            for name in sorted(os.listdir(lib_dir)):
                if not name.startswith("lib") or name.endswith(".la"):
                    continue
                if not (name.endswith(".a") or ".so" in name):
                    continue
                source = os.path.join(lib_dir, name)
                if not os.path.isfile(source):
                    continue
                target = os.path.join(stage_dir, name)
                if os.path.exists(target):
                    if filecmp.cmp(source, target, shallow=False):
                        continue
                    raise ConanInvalidConfiguration(
                        "ambiguous dependency library basename: %s" % name
                    )
                shutil.copy2(source, target)

        return stage_dir, staged_packages

    def _rewrite_generated_pkgconfig_libdirs(self, stage_dir, staged_packages):
        """Point only .la-affected generated pkg-config files at staging."""
        stage_posix = stage_dir.replace(os.sep, "/")
        for name in os.listdir(self.generators_folder):
            if not name.endswith(".pc"):
                continue
            path = os.path.join(self.generators_folder, name)
            with open(path, "r", encoding="utf-8") as handle:
                lines = handle.readlines()
            prefix = next(
                (line.rstrip("\n")[len("prefix="):] for line in lines
                 if line.startswith("prefix=")),
                "",
            )
            if os.path.normpath(prefix) not in staged_packages:
                continue
            with open(path, "w", encoding="utf-8", newline="\n") as handle:
                for line in lines:
                    if line.startswith("libdir="):
                        line = "libdir=%s\n" % stage_posix
                    handle.write(line)

    def _write_intltool_probe_shims(self):
        # configure's generated intltool macro requires these names even when
        # the package-local desktop rule does not invoke intltool-merge.
        shim_dir = os.path.join(self.build_folder, "ohos-build-tools")
        os.makedirs(shim_dir, exist_ok=True)
        scripts = {
            "intltool-update": (
                "#!/bin/sh\n"
                "case \"$1\" in\n"
                "  --version) echo 'intltool-update (intltool) 0.51.0' ;;\n"
                "esac\n"
            ),
            "intltool-merge": "#!/bin/sh\nexit 0\n",
            "intltool-extract": "#!/bin/sh\nexit 0\n",
            "msgmerge": (
                "#!/bin/sh\n"
                "if [ \"$1\" = \"--version\" ]; then\n"
                "  echo 'msgmerge (GNU gettext-tools) 0.22'\n"
                "  exit 0\n"
                "fi\n"
                "exit 1\n"
            ),
            # The bundled intltool.m4 also probes the raw gettext tools even
            # with --disable-nls.  This release ships no translation catalogs,
            # so these answer the version probes and no-op for anything else.
            "xgettext": (
                "#!/bin/sh\n"
                "if [ \"$1\" = \"--version\" ]; then\n"
                "  echo 'xgettext (GNU gettext-tools) 0.22'\n"
                "  exit 0\n"
                "fi\n"
                "exit 0\n"
            ),
            "msgfmt": (
                "#!/bin/sh\n"
                "if [ \"$1\" = \"--version\" ]; then\n"
                "  echo 'msgfmt (GNU gettext-tools) 0.22'\n"
                "  exit 0\n"
                "fi\n"
                "exit 0\n"
            ),
            "gmsgfmt": (
                "#!/bin/sh\n"
                "if [ \"$1\" = \"--version\" ]; then\n"
                "  echo 'msgfmt (GNU gettext-tools) 0.22'\n"
                "  exit 0\n"
                "fi\n"
                "exit 0\n"
            ),
        }
        for name, content in scripts.items():
            path = os.path.join(shim_dir, name)
            with open(path, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
            os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        return shim_dir

    def generate(self):
        PkgConfigDeps(self).generate()
        stage_dir, staged_packages = self._stage_dependency_libraries()
        self._rewrite_generated_pkgconfig_libdirs(stage_dir, staged_packages)
        shim_dir = self._write_intltool_probe_shims()
        env = self._build_env()
        env.prepend_path("PATH", shim_dir)

        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(
            [
                "--prefix=/",
                "--disable-nls",
                "--with-whoopsie=no",
                "--with-ccpanel=no",
                "--with-switchboard=no",
            ]
        )
        # glib 2.84 on musl routes g_libintl_* through its proxy-libintl
        # subproject.  glib-2.0.pc does not propagate it, so consumers that
        # call Intl textdomain helpers (Vala _vala_main does) fail to link.
        glib = self.dependencies.get("glib")
        glib_libdir = ""
        if glib and glib.package_folder:
            for libdir in glib.cpp_info.libdirs:
                if os.path.isfile(os.path.join(glib.package_folder, libdir, "libintl.so.8")):
                    glib_libdir = os.path.join(glib.package_folder, libdir)
                    break
        if glib_libdir:
            tc.configure_args.append(
                "LDFLAGS=-L{} -lintl".format(glib_libdir.replace(os.sep, "/"))
            )
        tc.generate(env=env)

    def _vala_assignment(self):
        """AM_VALAFLAGS override with dependency vapidirs.

        src/Makefile.am's list is replaced wholesale, so it is replicated
        here plus the Conan packages' vapi directories (vala ships the core
        GLib/GTK vapis; libgee and libzeitgeist ship their own).
        """
        import glob
        import shlex

        vapidirs = []
        for dep in list(self.dependencies.build.values()) + list(self.dependencies.host.values()):
            if not dep.package_folder:
                continue
            for pattern in (
                os.path.join(dep.package_folder, "share", "vala*", "vapi"),
                os.path.join(dep.package_folder, "share", "vala", "vapi"),
            ):
                vapidirs.extend(glob.glob(pattern))
        flags = [
            "--pkg", "zeitgeist-2.0",
            "--pkg", "glib-2.0",
            "--pkg", "gtk+-3.0",
            "--pkg", "gee-1.0",
            "--target-glib=2.36",
            "--pkg", "gio-unix-2.0",
            "config.vapi",
        ]
        flags.extend("--vapidir={}".format(path) for path in dict.fromkeys(vapidirs))
        if str(self.settings.os) == "OHOS":
            flags.append("--define=OHOS")
        return "AM_VALAFLAGS={}".format(shlex.quote(" ".join(flags)))

    def build(self):
        apply_conandata_patches(self)
        # The release tarball ships C files generated on Ubuntu with
        # -D DIAGNOSTIC, so the whoopsie calls bypass the upstream
        # "#if DIAGNOSTIC" guards and fail to link without libwhoopsie.
        # Touch the Vala sources so Automake regenerates the C files with
        # this build's defines (DIAGNOSTIC undefined for the standalone app).
        src_dir = os.path.join(self.source_folder, "src")
        if os.path.isdir(src_dir):
            for name in os.listdir(src_dir):
                if name.endswith(".vala"):
                    os.utime(os.path.join(src_dir, name), None)
        # HNP bash may call getcwd() after Conan changes cwd.  Exporting the
        # actual build path lets Autoconf retain the cwd on OHOS/HMDFS.
        os.environ["PWD"] = str(self.build_folder)
        env = self._build_env()
        probe_dir = os.path.join(self.build_folder, "ohos-build-tools")
        env.prepend_path("PATH", probe_dir)
        with env.vars(self).apply():
            # Conan's generated environment can be superseded by the worker's
            # profile when Autotools launches configure.  Re-assert the probe
            # directory in the live process environment at the boundary that
            # matters, so broken worker gettext binaries are never selected.
            os.environ["PATH"] = prepend_probe_path(
                probe_dir, os.environ.get("PATH", "")
            )
            autotools = Autotools(self)
            autotools.configure()
            vala_assignment = self._vala_assignment()
            autotools.make(args=["-j1", vala_assignment])
            # The release check target validates generated desktop files.
            # Skip it when desktop-file-validate is not installed; the
            # consumer test still checks the installed desktop entry.
            if shutil.which("desktop-file-validate"):
                autotools.make(target="check")
            else:
                self.output.warning(
                    "desktop-file-validate not found; skipping upstream "
                    "desktop file validation"
                )

    def package(self):
        Autotools(self).install()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
