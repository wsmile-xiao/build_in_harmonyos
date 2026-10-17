#!/usr/bin/env python3
"""Conan recipe for X.Org libXext 1.3.7."""

import os
import re
import shlex
import shutil
from pathlib import Path, PurePosixPath

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import (
    Autotools,
    AutotoolsDeps,
    AutotoolsToolchain,
    PkgConfigDeps,
)
from conan.tools.layout import basic_layout


class LibxextConan(ConanFile):
    name = "libxext"
    version = "1.3.7"
    description = "X.Org miscellaneous extension client library"
    license = "MIT"
    homepage = "https://gitlab.freedesktop.org/xorg/lib/libxext"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libx11/1.8.13", transitive_headers=True)
        self.requires("xorgproto/2025.1", transitive_headers=True)

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libxext supports Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()
        if str(self.settings.os) == "OHOS":
            self._prepare_ohos_libtool_shadow()
        self._autotools_toolchain().generate()

    def build(self):
        apply_conandata_patches(self)
        if str(self.settings.os) == "OHOS":
            self._generate_ohos_configure()
        environment = self._build_environment()
        with environment.vars(self).apply():
            if str(self.settings.os) == "OHOS":
                self._configure_ohos()
                self._run_ohos("make -j1")
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
        self._relocate_metadata()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = ["Xext"]
        self.cpp_info.requires = ["libx11::libx11", "xorgproto::xorgproto"]
        self.cpp_info.set_property("cmake_file_name", "libxext")
        self.cpp_info.set_property("cmake_target_name", "libxext::libxext")
        self.cpp_info.set_property("pkg_config_name", "xext")
        pc_dir = os.path.join(self.package_folder, "lib", "pkgconfig")
        self.buildenv_info.append_path("PKG_CONFIG_PATH", pc_dir)
        self.runenv_info.append_path("PKG_CONFIG_PATH", pc_dir)

    def _build_environment(self):
        temporary = Path(self.build_folder, ".tmp")
        temporary.mkdir(parents=True, exist_ok=True)
        environment = Environment()
        environment.define_path("TMPDIR", str(temporary))
        environment.define("TMPPREFIX", str(temporary / "zsh-tmp-"))
        if str(self.settings.os) == "OHOS":
            shadow_dir = Path(self.build_folder, "libtool-shadow")
            if not shadow_dir.is_dir():
                raise ConanException(
                    f"libtool shadow directory is missing: {shadow_dir}"
                )
            environment.prepend("LDFLAGS", f"-L{shadow_dir}", separator=" ")
        for dependency in self.dependencies.host.values():
            for libdir in dependency.cpp_info.libdirs:
                if not os.path.isabs(libdir):
                    libdir = os.path.join(dependency.package_folder, libdir)
                if os.path.isdir(libdir):
                    environment.prepend_path("LD_LIBRARY_PATH", libdir)
        if str(self.settings.os) == "OHOS":
            environment.define("MKDIR_P", "/system/bin/mkdir -p")
        return environment

    def _autotools_toolchain(self):
        toolchain = AutotoolsToolchain(self)
        if self.options.shared:
            toolchain.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            toolchain.configure_args.extend(["--disable-shared", "--enable-static"])
        return toolchain

    def _prepare_ohos_libtool_shadow(self):
        libtool_archives = {}
        for dependency in self.dependencies.host.values():
            for libdir in dependency.cpp_info.libdirs:
                directory = Path(libdir)
                if not directory.is_absolute():
                    directory = Path(dependency.package_folder, libdir)
                if not directory.is_dir():
                    continue
                for archive in directory.glob("*.la"):
                    libtool_archives.setdefault(archive.name, []).append(archive)

        shadow_dir = Path(self.build_folder, "libtool-shadow")
        shadow_dir.mkdir(parents=True, exist_ok=True)
        ambiguous = sorted(
            name for name, paths in libtool_archives.items() if len(paths) != 1
        )
        if ambiguous:
            raise ConanException(
                f"libtool archive basenames are ambiguous: {ambiguous}"
            )
        archives_by_name = {
            name: paths[0] for name, paths in libtool_archives.items()
        }
        if "libX11.la" not in archives_by_name:
            raise ConanException("expected one installed libX11.la, found 0")

        artifact_sources = {}
        for archive in archives_by_name.values():
            content = archive.read_text(encoding="utf-8")
            for field in ("library_names", "old_library"):
                field_match = re.search(
                    rf"^{field}='(.*)'$", content, flags=re.MULTILINE
                )
                if field_match is None:
                    raise ConanException(f"{archive.name} has no {field} field")
                for library_name in shlex.split(field_match.group(1)):
                    source = archive.parent / library_name
                    if not source.is_file():
                        raise ConanException(
                            f"{archive.name} references a missing library: {source}"
                        )
                    previous = artifact_sources.get(library_name)
                    if previous is not None and previous != source:
                        raise ConanException(
                            f"library basename is ambiguous: {library_name}"
                        )
                    if previous is None:
                        shutil.copy2(source, shadow_dir / library_name)
                        artifact_sources[library_name] = source

        known_libdirs = {
            str(archive.parent) for archive in archives_by_name.values()
        }
        total_replacements = 0
        for archive_name, archive in archives_by_name.items():
            content = archive.read_text(encoding="utf-8")
            dependency_match = re.search(
                r"^dependency_libs='(.*)'$", content, flags=re.MULTILINE
            )
            if dependency_match is None:
                raise ConanException(
                    f"{archive_name} has no dependency_libs field"
                )

            repaired_tokens = []
            shadow_libdir_added = False
            for token in shlex.split(dependency_match.group(1)):
                if token.startswith("-L"):
                    directory = Path(token[2:])
                    if (
                        str(directory) in known_libdirs
                        or self._is_stale_conan_cache_path(directory)
                    ):
                        if not shadow_libdir_added:
                            repaired_tokens.append(f"-L{shadow_dir}")
                            shadow_libdir_added = True
                        total_replacements += 1
                    elif directory.is_dir():
                        repaired_tokens.append(token)
                    elif os.name == "nt" and token.startswith("-L/"):
                        repaired_tokens.append(token)
                    else:
                        raise ConanException(
                            f"{archive_name} references a missing non-Conan "
                            f"libdir: {directory}"
                        )
                    continue
                if token.endswith(".la"):
                    dependency_name = (
                        PurePosixPath(token).name
                        if token.startswith("/")
                        else Path(token).name
                    )
                    if dependency_name not in archives_by_name:
                        raise ConanException(
                            f"cannot uniquely rebind {dependency_name}: found 0"
                        )
                    repaired_tokens.append(str(shadow_dir / dependency_name))
                    total_replacements += 1
                    continue
                repaired_tokens.append(token)

            dependency_libs = " ".join(
                shlex.quote(token) for token in repaired_tokens
            )
            content = (
                content[: dependency_match.start(1)]
                + dependency_libs
                + content[dependency_match.end(1) :]
            )
            content, libdir_count = re.subn(
                r"^libdir='.*'$",
                lambda _match: f"libdir='{shadow_dir}'",
                content,
                count=1,
                flags=re.MULTILINE,
            )
            if libdir_count != 1:
                raise ConanException(
                    f"{archive_name} has no unique libdir field"
                )
            (shadow_dir / archive_name).write_text(
                content, encoding="utf-8", newline="\n"
            )

        for shadow_archive in shadow_dir.glob("*.la"):
            content = shadow_archive.read_text(encoding="utf-8")
            dependency_match = re.search(
                r"^dependency_libs='(.*)'$", content, flags=re.MULTILINE
            )
            for token in shlex.split(dependency_match.group(1)):
                if token.endswith(".la") and not Path(token).is_file():
                    raise ConanException(
                        f"sanitized {shadow_archive.name} has a missing "
                        f"archive: {token}"
                    )
        self.output.info(
            f"prepared {len(archives_by_name)} libtool shadows with "
            f"{total_replacements} path replacements"
        )

        x11_pc = Path(self.generators_folder, "x11.pc")
        if not x11_pc.is_file():
            raise ConanException(f"generated x11.pc is missing: {x11_pc}")
        pc_content = x11_pc.read_text(encoding="utf-8")
        pc_content, pc_count = re.subn(
            r"^libdir=.*$",
            lambda _match: f"libdir={shadow_dir}",
            pc_content,
            count=1,
            flags=re.MULTILINE,
        )
        if pc_count != 1:
            raise ConanException("generated x11.pc has no unique libdir field")
        x11_pc.write_text(pc_content, encoding="utf-8", newline="\n")

    @staticmethod
    def _is_stale_conan_cache_path(path):
        normalized = path.as_posix()
        return "/.conan2/" in normalized or "/.cache/conan2/" in normalized

    def _configure_ohos(self):
        shell = self._ohos_shell_path()
        configure = self._ohos_configure_path()
        configure_args = [
            f"--srcdir={self.source_folder}",
            *self._autotools_toolchain().configure_args,
        ]
        arguments = " ".join(
            shlex.quote(argument)
            for argument in configure_args
        )
        self._run_ohos(f'"{shell}" "{configure}" {arguments}')

    def _generate_ohos_configure(self):
        upstream = self._upstream_configure_path()
        generated = self._ohos_configure_path()
        config_guess = self._generate_compiler_config_guess()
        if any(character.isspace() for character in str(config_guess)):
            raise ConanException("config.guess build path contains whitespace")
        content = upstream.read_text(encoding="utf-8")
        needle = "umask 077"
        if content.count(needle) != 2:
            raise ConanException("configure umask contract changed")
        replacements = (
            (
                'ac_config_guess="$SHELL ${ac_aux_dir}config.guess"',
                f'ac_config_guess="$SHELL {config_guess}"',
            ),
            (
                'ac_build_alias=`$SHELL "${ac_aux_dir}config.guess"`',
                f'ac_build_alias=`$SHELL "{config_guess}"`',
            ),
        )
        for original, replacement in replacements:
            if content.count(original) != 1:
                raise ConanException("configure config.guess contract changed")
            content = content.replace(original, replacement)
        generated.parent.mkdir(parents=True, exist_ok=True)
        generated.write_text(
            content.replace(needle, "umask 022"),
            encoding="utf-8",
            newline="\n",
        )
        return generated

    def _generate_compiler_config_guess(self):
        self._upstream_config_guess_path()
        generated = Path(self.build_folder, "config.guess-compiler")
        content = """#!/data/service/hnp/bin/bash
set -eu
compiler="${CC_FOR_BUILD:-${CC:-}}"
if [ -z "$compiler" ]; then
    echo "config.guess compiler is unavailable" >&2
    exit 1
fi
tuple="$("$compiler" -dumpmachine)"
case "$tuple" in
    ""|*[!A-Za-z0-9._+-]*)
        echo "config.guess compiler tuple is invalid" >&2
        exit 1
        ;;
esac
printf '%s\\n' "$tuple"
"""
        generated.parent.mkdir(parents=True, exist_ok=True)
        generated.write_text(
            content,
            encoding="utf-8",
            newline="\n",
        )
        return generated

    def _upstream_configure_path(self):
        configure = Path(self.source_folder, "configure")
        if not configure.is_file():
            raise ConanException(f"configure script is missing: {configure}")
        return configure

    def _upstream_config_guess_path(self):
        config_guess = Path(self.source_folder, "config.guess")
        if config_guess.is_symlink() or not config_guess.is_file():
            raise ConanException(
                f"config.guess script is missing or unsafe: {config_guess}"
            )
        return config_guess

    def _ohos_configure_path(self):
        return Path(self.build_folder, "configure-ohos")

    def _ohos_shell_path(self):
        shell = "/data/service/hnp/bin/bash"
        if not os.path.isfile(shell):
            raise ConanInvalidConfiguration(f"OHOS configure shell is missing: {shell}")
        return shell

    def _run_ohos(self, command):
        shell = self._ohos_shell_path()
        prefix = f"export SHELL={shell} CONFIG_SHELL={shell}; "
        self.run(prefix + command, cwd=self.build_folder, env="conanbuild")

    def _relocate_metadata(self):
        pc_path = Path(self.package_folder, "lib", "pkgconfig", "xext.pc")
        if not pc_path.is_file():
            raise ConanException("installed xext.pc is missing")
        pc_content = pc_path.read_text(encoding="utf-8")
        pc_content, count = re.subn(
            r"^prefix=.*$",
            "prefix=${pcfiledir}/../..",
            pc_content,
            count=1,
            flags=re.MULTILINE,
        )
        if count != 1:
            raise ConanException("xext.pc has no unique prefix field")
        pc_path.write_text(pc_content, encoding="utf-8")

        la_path = Path(self.package_folder, "lib", "libXext.la")
        if la_path.is_file():
            la_path.unlink()
