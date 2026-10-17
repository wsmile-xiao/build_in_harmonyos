#!/usr/bin/env python3
"""Conan recipe for libdockapp 0.7.3."""

import os
import posixpath
import re
import shlex
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class LibdockappConan(ConanFile):
    name = "libdockapp"
    version = "0.7.3"
    description = "Library for writing Window Maker dock applications"
    license = "MIT"
    homepage = "https://www.dockapps.net/libdockapp"
    url = "https://www.dockapps.net/libdockapp"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Keep the complete X11 dependency graph on the published 6.4.0 track.
        self.requires(
            "libx11/6.4.0",
            force=True,
            transitive_headers=True,
            transitive_libs=True,
        )
        self.requires(
            "libxext/6.4.0",
            transitive_headers=True,
            transitive_libs=True,
        )
        self.requires(
            "libxpm/3.5.17",
            transitive_headers=True,
            transitive_libs=True,
        )

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libdockapp supports Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(
            self,
            **self.conan_data["sources"][str(self.version)],
            strip_root=True,
        )

    def generate(self):
        self._prepare_linker_view()
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()
        self._autotools_toolchain().generate()

    def build(self):
        apply_conandata_patches(self)
        environment = self._build_environment()
        with environment.vars(self).apply():
            if str(self.settings.os) == "OHOS":
                self._generate_ohos_configure()
                self._configure_ohos()
                self._run_ohos("make -j1")
                # The release has no TESTS/check_PROGRAMS, but its canonical
                # check target remains part of every package build.
                self._run_ohos("make -j1 check")
            else:
                autotools = Autotools(self)
                autotools.configure()
                autotools.make(args=["-j1"])
                autotools.make(target="check", args=["-j1"])

    def package(self):
        environment = self._build_environment()
        with environment.vars(self).apply():
            if str(self.settings.os) == "OHOS":
                destination = shlex.quote(self.package_folder)
                self._run_ohos(f"make -j1 install DESTDIR={destination}")
            else:
                Autotools(self).install(args=["-j1"])
        if str(self.settings.os) == "OHOS" and self.options.shared:
            self._drop_build_rpath()
        self._relocate_metadata()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = ["dockapp"]
        self.cpp_info.requires = [
            "libx11::libx11",
            "libxext::libxext",
            "libxpm::libxpm",
        ]
        self.cpp_info.set_property("cmake_file_name", "libdockapp")
        self.cpp_info.set_property("cmake_target_name", "libdockapp::libdockapp")
        self.cpp_info.set_property("pkg_config_name", "dockapp")
        pc_dir = os.path.join(self.package_folder, "lib", "pkgconfig")
        self.buildenv_info.append_path("PKG_CONFIG_PATH", pc_dir)
        self.runenv_info.append_path("PKG_CONFIG_PATH", pc_dir)

    def _autotools_toolchain(self):
        toolchain = AutotoolsToolchain(self)
        toolchain.configure_args.extend(
            [
                "--without-font",
                "--without-examples",
                "--disable-debug",
                "--enable-shared" if self.options.shared else "--disable-shared",
                "--disable-static" if self.options.shared else "--enable-static",
                f"LDFLAGS=-L{self._linker_view.as_posix()}",
                # XORG_FONT_COMMON_UTILS checks mkfontdir unconditionally even
                # when this library-only build disables the fonts subdirectory.
                "MKFONTDIR=/system/bin/true",
            ]
        )
        return toolchain

    def _configure_ohos(self):
        shell = "/system/bin/sh"
        if not os.path.isfile(shell):
            raise ConanInvalidConfiguration(f"OHOS configure shell is missing: {shell}")
        arguments = [
            f"--srcdir={self.source_folder}",
            "--host=aarch64-linux-ohos",
            *self._autotools_toolchain().configure_args,
        ]
        command = " ".join(shlex.quote(argument) for argument in arguments)
        self._run_ohos(f'"{shell}" "{self._ohos_configure_path()}" {command}')

    def _generate_ohos_configure(self):
        upstream = Path(self.source_folder, "configure")
        if not upstream.is_file():
            raise ConanException(f"configure script is missing: {upstream}")
        content = upstream.read_text(encoding="utf-8")
        if content.count("umask 077") != 2:
            raise ConanException("configure umask contract changed")
        generated = self._ohos_configure_path()
        generated.parent.mkdir(parents=True, exist_ok=True)
        generated.write_text(
            content.replace("umask 077", "umask 022"),
            encoding="utf-8",
            newline="\n",
        )

    def _ohos_configure_path(self):
        return Path(self.build_folder, "configure-ohos")

    def _run_ohos(self, command):
        shell = "/system/bin/sh"
        prefix = f"export SHELL={shell} CONFIG_SHELL={shell}; "
        self.run(prefix + command, cwd=self.build_folder, env="conanbuild")

    def _build_environment(self):
        temporary = Path(self.build_folder, ".tmp")
        temporary.mkdir(parents=True, exist_ok=True)
        environment = Environment()
        environment.define_path("TMPDIR", str(temporary))
        environment.define("MKDIR_P", "/system/bin/mkdir -p")
        environment.prepend_path("LD_LIBRARY_PATH", str(self._linker_view))

        linker = Path("/data/service/hnp/bin/ld.lld")
        if linker.exists():
            sdk_lib = linker.resolve().parent.parent / "lib"
            if sdk_lib.is_dir():
                environment.prepend_path("LD_LIBRARY_PATH", str(sdk_lib))

        for dependency in self.dependencies.host.values():
            for libdir in dependency.cpp_info.libdirs:
                path = Path(libdir)
                if not path.is_absolute():
                    path = Path(dependency.package_folder, libdir)
                if path.is_dir():
                    environment.prepend_path("LD_LIBRARY_PATH", str(path))
        return environment

    def _prepare_linker_view(self):
        """Provide libtool with relocatable copies of dependency metadata."""
        linker_view = Path(self.build_folder, "linker-view")
        linker_view.mkdir(parents=True, exist_ok=True)
        for dependency in self.dependencies.host.values():
            for libdir in dependency.cpp_info.libdirs:
                source_dir = Path(libdir)
                if not source_dir.is_absolute():
                    source_dir = Path(dependency.package_folder, libdir)
                if not source_dir.is_dir():
                    continue
                for source in source_dir.iterdir():
                    if source.suffix not in (".a", ".la", ".so") or not source.is_file():
                        continue
                    destination = linker_view / source.name
                    if source.suffix == ".la":
                        content = source.read_text(encoding="utf-8")
                        destination.write_text(
                            self._relocate_libtool_archive(content, linker_view),
                            encoding="utf-8",
                            newline="\n",
                        )
                    else:
                        shutil.copyfile(source, destination)
        self._linker_view = linker_view

    @staticmethod
    def _relocate_libtool_archive(content, linker_view):
        view = linker_view.as_posix()
        lines = []
        for line in content.splitlines():
            if line.startswith("libdir="):
                line = f"libdir='{view}'"
            elif line.startswith("dependency_libs="):
                match = re.match(r"dependency_libs='(.*)'$", line)
                if not match:
                    raise ConanException("unexpected libtool dependency_libs format")
                relocated = []
                for token in shlex.split(match.group(1)):
                    if token.startswith("-L"):
                        continue
                    if token.endswith(".la"):
                        name = posixpath.basename(token)
                        if not name.startswith("lib"):
                            raise ConanException(f"unexpected libtool archive: {token}")
                        token = "-l" + name[3:-3]
                    relocated.append(token)
                line = "dependency_libs='-L%s %s'" % (view, " ".join(relocated))
            lines.append(line)
        return "\n".join(lines) + "\n"

    def _relocate_metadata(self):
        pc_path = Path(self.package_folder, "lib", "pkgconfig", "dockapp.pc")
        if not pc_path.is_file():
            raise ConanException("installed dockapp.pc is missing")
        lines = pc_path.read_text(encoding="utf-8").splitlines()
        variables = ("prefix=", "exec_prefix=", "libdir=", "includedir=")
        payload = []
        for line in lines:
            if line.startswith(variables):
                continue
            if line.startswith("Libs:"):
                line = "Libs: -L${libdir} -ldockapp"
            elif line.startswith("Cflags:"):
                line = "Cflags: -I${includedir}"
            payload.append(line)
        pc_path.write_text(
            "\n".join(
                [
                    "prefix=${pcfiledir}/../..",
                    "exec_prefix=${prefix}",
                    "libdir=${prefix}/lib",
                    "includedir=${prefix}/include",
                    *payload,
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        libtool_archive = Path(self.package_folder, "lib", "libdockapp.la")
        if libtool_archive.is_file():
            libtool_archive.unlink()

    def _drop_build_rpath(self):
        """Remove the task-local linker view from the published ELF."""
        patchelf = shutil.which("patchelf") or "/data/service/hnp/bin/patchelf"
        readelf = shutil.which("llvm-readelf") or "/data/service/hnp/bin/llvm-readelf"
        if not os.path.isfile(patchelf) or not os.path.isfile(readelf):
            raise ConanInvalidConfiguration("OHOS packaging requires patchelf and llvm-readelf")
        library = Path(self.package_folder, "lib", "libdockapp.so.3.0.1")
        dynamic = subprocess.run(
            [readelf, "-d", str(library)],
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        ).stdout
        if "(RPATH)" in dynamic or "(RUNPATH)" in dynamic:
            if str(self._linker_view) not in dynamic:
                raise ConanException("libdockapp carries an unexpected runtime search path")
            subprocess.run(
                [patchelf, "--remove-rpath", str(library)],
                check=True,
                capture_output=True,
                text=True,
                timeout=120,
            )
        after = subprocess.run(
            [readelf, "-d", str(library)],
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        ).stdout
        if "(RPATH)" in after or "(RUNPATH)" in after:
            raise ConanException("libdockapp build rpath was not removed")
        self._sign_ohos_elf(library)

    @staticmethod
    def _sign_ohos_elf(path):
        """Replace the stale post-link signature after ELF rewriting."""
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        readelf = shutil.which("llvm-readelf") or "/data/service/hnp/bin/llvm-readelf"
        for tool in (objcopy, signer, readelf):
            if not os.path.isfile(tool):
                raise ConanInvalidConfiguration(f"required OHOS tool is missing: {tool}")
        subprocess.run(
            [objcopy, "--remove-section", ".codesign", str(path)],
            check=True,
            capture_output=True,
            text=True,
            timeout=120,
        )
        signed = Path(f"{path}.signed")
        try:
            subprocess.run(
                [signer, "sign", "-inFile", str(path), "-outFile", str(signed), "-selfSign", "1"],
                check=True,
                capture_output=True,
                text=True,
                timeout=180,
            )
            sections = subprocess.run(
                [readelf, "-SW", str(signed)],
                check=True,
                capture_output=True,
                text=True,
                timeout=60,
            ).stdout
            if sections.count(".codesign") != 1:
                raise ConanException("signed libdockapp has an invalid .codesign section")
            os.chmod(signed, (os.stat(path).st_mode & 0o777) | 0o055)
            os.replace(signed, path)
        finally:
            if signed.exists():
                signed.unlink()
