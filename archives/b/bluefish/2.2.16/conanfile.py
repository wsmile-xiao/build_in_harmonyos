#!/usr/bin/env python3
"""Conan recipe for bluefish 2.2.16, a GTK web-development editor (C/autotools).

OHOS PC adaptation notes
------------------------
- bluefish 2.2.16's configure defaults to GTK3 (``gtk+-3.0 >= 3.2.2``);
  GTK2 is only used when ``--with-gtk2`` is requested explicitly, so the
  GTK3 dependency chain already published to the artifact repository
  (gtk/3.24.43 + glib + pango + gdk-pixbuf + libxml2) covers this release.
  No GTK2 package is required.
- HarmonyOS PC has no X server, so the GTK3 GUI cannot open a display at
  runtime. The recipe therefore compiles and installs the full application
  (binary + share data), self-signs the packaged executable, and validates
  the result headlessly (``--version``/``--help``/``--selftest`` plus the
  expected no-display failure path).
- Upstream ships generated Autotools files, so no autoreconf is needed.
  Four patches are applied:
    * config.guess/config.sub learn the HarmonyOS ``uname`` and the
      ``aarch64-unknown-linux-ohos`` triplet (the bundled 2018 files do
      not recognize them);
    * configure creates its config.status temporary directory with
      ``umask 022`` instead of ``077`` (HMDFS setgid semantics make 0700
      directories unusable);
    * src/bluefish.c adds a headless ``--selftest`` option that runs before
      the GTK display is opened and exercises production string helpers
      (bf_lib.c), the libxml2 binding, and the GLib/GTK version contract.

Self-test coverage: 14 programmatic checks inside ``bluefish --selftest``
(config escape round trips, string repeat/truncate, word count incl. UTF-8
and empty input, integer parsing incl. error path, XML parse success/error,
GLib/GTK runtime version) plus CLI assertions in test_package.
"""
import os
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class BluefishConan(ConanFile):
    name = "bluefish"
    version = "2.2.16"
    description = "Bluefish is a GTK3 editor for experienced web designers and programmers"
    license = "GPL-3.0-or-later"
    homepage = "https://bluefish.openoffice.nl"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("gtk/3.24.43", transitive_headers=True, transitive_libs=True)
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)
        self.requires("pango/1.50.14.1.1", transitive_headers=True, transitive_libs=True)
        self.requires("gdk-pixbuf/2.44.6.1", transitive_headers=True, transitive_libs=True)
        self.requires("libxml2/2.15.3.1", transitive_headers=True, transitive_libs=True)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"bluefish supports Linux/OHOS native builds, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # bluefish's configure.ac probes pkg-config modules; PkgConfigDeps
        # writes relocatable .pc files into the generators folder.
        PkgConfigDeps(self).generate()
        self._write_alias_pkgconfig("gdk-3.0", "gtk+-3.0")
        self._write_alias_pkgconfig("gio-unix-2.0", "gio-2.0")

        VirtualBuildEnv(self).generate()
        toolchain = AutotoolsToolchain(self)
        environment = toolchain.environment()
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        environment.define_path("TMPDIR", tmpdir)
        environment.define_path("TMP", tmpdir)
        environment.define_path("TEMP", tmpdir)
        if self.settings.os == "OHOS":
            # The Conan-package gdk-pixbuf-csource (which the bluefish
            # Makefiles run at build time to embed PNGs as C arrays) is an
            # unsigned ELF and cannot be executed from the cache; point the
            # build at the self-signed copy prepared in build().
            tools_root = os.path.join(self.build_folder, "host-tools")
            environment.define_path(
                "GDK_PIXBUF_CSOURCE",
                os.path.join(tools_root, "gdk-pixbuf-csource"),
            )
        toolchain.generate(env=environment)

    def build(self):
        apply_conandata_patches(self)
        if self.settings.os == "OHOS":
            self._prepare_ohos_host_tools()
        environment = self._build_environment()
        with environment.vars(self).apply():
            if self.settings.os == "OHOS":
                self._run_ohos_configure()
            else:
                Autotools(self).configure()
            Autotools(self).make(args=["-j1"])
            # Upstream has no TESTS/check_PROGRAMS; `make check` only runs
            # desktop-file sanity targets and reports success (verified).
            Autotools(self).make(target="check", args=["-j1"])

    def package(self):
        if self.settings.os == "OHOS":
            destination = shlex.quote(self.package_folder)
            with self._build_environment().vars(self).apply():
                self.run(f"make -j1 install DESTDIR={destination}")
            self._sign_ohos_elf(
                os.path.join(self.package_folder, "bin", "bluefish")
            )
        else:
            Autotools(self).install(args=["-j1"])
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))

    def _write_alias_pkgconfig(self, alias_name, source_name):
        """PkgConfigDeps emits no pc for gdk-3.0/gio-unix-2.0 (the packaged
        GTK merges gdk into gtk+-3.0 and the GLib build ships gio-2.0 only).
        The configure probes still ask for the traditional module names, so
        provide them as aliases that carry the same flags as their parent
        when the generators folder does not already contain the module."""
        alias_pc = os.path.join(self.generators_folder, f"{alias_name}.pc")
        if os.path.isfile(alias_pc):
            return
        source_pc = os.path.join(self.generators_folder, f"{source_name}.pc")
        if not os.path.isfile(source_pc):
            raise ConanException(f"expected generated pc file: {source_pc}")
        lines = open(source_pc, encoding="utf-8").readlines()
        rewritten = []
        for line in lines:
            if line.startswith("Name: "):
                rewritten.append(f"Name: {alias_name}\n")
            elif line.startswith("Description: "):
                rewritten.append(f"Description: {alias_name} (OHOS alias for {source_name})\n")
            else:
                rewritten.append(line)
        open(alias_pc, "w", encoding="utf-8", newline="\n").write("".join(rewritten))

    def _build_environment(self):
        environment = Environment()
        if self.settings.os == "OHOS":
            tools_root = os.path.join(self.build_folder, "host-tools")
            if os.path.isdir(tools_root):
                environment.prepend_path("PATH", tools_root)
                environment.define_path(
                    "GDK_PIXBUF_CSOURCE",
                    os.path.join(tools_root, "gdk-pixbuf-csource"),
                )
            for dependency in self.dependencies.host.values():
                for libdir in dependency.cpp_info.libdirs:
                    directory = libdir
                    if not os.path.isabs(directory):
                        directory = os.path.join(dependency.package_folder, libdir)
                    if os.path.isdir(directory):
                        environment.prepend_path("LD_LIBRARY_PATH", directory)
        return environment

    def _prepare_ohos_host_tools(self):
        """Conan-package host tools (gdk-pixbuf-csource, ...) are unsigned
        ELF binaries and cannot run from the cache; copy and self-sign
        working copies into the build tree."""
        tools_root = os.path.join(self.build_folder, "host-tools")
        os.makedirs(tools_root, exist_ok=True)
        wanted = {
            "glib": ["glib-compile-resources"],
            "gdk-pixbuf": ["gdk-pixbuf-csource", "gdk-pixbuf-pixdata"],
        }
        for package_name, tools in wanted.items():
            package = self.dependencies.host[package_name]
            for tool in tools:
                source = os.path.join(package.package_folder, "bin", tool)
                if not os.path.isfile(source):
                    continue
                target = os.path.join(tools_root, tool)
                shutil.copy2(source, target)
                self._sign_ohos_elf(target)

    def _run_ohos_configure(self):
        configure_script = os.path.join(self.source_folder, "configure")
        options = [
            "--prefix=/",
            "--disable-nls",
            "--disable-spell-check",
            "--disable-python",
            "--disable-update-databases",
            "--with-freedesktop_org-menu=no",
            "--with-freedesktop_org-mime=no",
            "--with-freedesktop_org-appdata=no",
            "--without-theme-path",
            "--without-icon-path",
        ]
        command = (
            "CONFIG_SHELL=/system/bin/sh SHELL=/system/bin/sh "
            + shlex.join(["/system/bin/sh", configure_script] + options)
        )
        self.run(command, cwd=self.build_folder, env="conanbuild")

    @staticmethod
    def _sign_ohos_elf(path):
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        readelf = shutil.which("llvm-readelf") or "/data/service/hnp/bin/llvm-readelf"
        if not os.path.isfile(path):
            raise ConanException(f"Missing executable to sign: {path}")
        if not os.path.isfile(signer) or not os.path.isfile(readelf):
            raise ConanException("Required OHOS signing tools are missing")
        output = path + ".signed"
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", output, "-selfSign", "1"],
            check=True,
            timeout=120,
        )
        sections = subprocess.run(
            [readelf, "-SW", output],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        if sections.count(".codesign") != 1:
            raise ConanException("Signed executable has invalid .codesign count")
        os.chmod(output, (os.stat(path).st_mode & 0o777) | 0o055)
        os.replace(output, path)
