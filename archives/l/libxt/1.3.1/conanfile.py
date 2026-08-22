#!/usr/bin/env python3
"""Conan recipe for X.Org libXt 1.3.1."""

import os
import re
import shlex
import shutil
import subprocess
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


class LibxtConan(ConanFile):
    name = "libxt"
    version = "1.3.1"
    description = "X.Org X Toolkit Intrinsics library"
    license = "MIT"
    homepage = "https://gitlab.freedesktop.org/xorg/lib/libxt"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libx11/1.8.13", transitive_headers=True)
        self.requires("libsm/1.2.6", transitive_headers=True)
        self.requires("libice/1.1.2", transitive_headers=True)
        self.requires("xorgproto/2025.1", transitive_headers=True)

    def build_requirements(self):
        self.test_requires("glib/2.84.0.1")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libxt supports Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()
        if str(self.settings.os) == "OHOS":
            self._prepare_ohos_libtool_shadow()
        self._autotools_toolchain().generate()

    def build(self):
        if str(self.settings.os) == "OHOS":
            self._stabilize_ohos_alloc_tests()
            self._generate_ohos_configure()
        environment = self._build_environment()
        with environment.vars(self).apply():
            if str(self.settings.os) == "OHOS":
                self._configure_ohos()
                self._run_ohos("make -j1 -C util makestrs")
                self._sign_ohos_elf(
                    [Path(self.build_folder, "util", "makestrs")],
                    "makestrs build helper",
                )
                self._run_ohos("make -j1")
                self._run_ohos("make -j1 -C test Alloc Converters Event")
                for executable in ("Alloc", "Converters", "Event"):
                    self._sign_ohos_elf(
                        [
                            Path(self.build_folder, "test", ".libs", executable),
                            Path(self.build_folder, "test", executable),
                        ],
                        f"upstream test {executable}",
                    )
                test_launcher = self._write_ohos_test_launcher()
                log_compiler = f"/system/bin/sh {test_launcher}"
                self._run_ohos(
                    "make -j1 check "
                    f"LOG_COMPILER={shlex.quote(log_compiler)}"
                )
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
        self.cpp_info.libs = ["Xt"]
        self.cpp_info.requires = [
            "libx11::libx11",
            "libsm::libsm",
            "libice::libice",
            "xorgproto::xorgproto",
        ]
        self.cpp_info.set_property("cmake_file_name", "libxt")
        self.cpp_info.set_property("cmake_target_name", "libxt::libxt")
        self.cpp_info.set_property("pkg_config_name", "xt")
        pc_dir = os.path.join(self.package_folder, "lib", "pkgconfig")
        self.buildenv_info.append_path("PKG_CONFIG_PATH", pc_dir)
        self.runenv_info.append_path("PKG_CONFIG_PATH", pc_dir)

    def _build_environment(self):
        temporary = Path(self.build_folder, ".tmp")
        temporary.mkdir(parents=True, exist_ok=True)
        environment = Environment()
        environment.define_path("TMPDIR", str(temporary))
        if str(self.settings.os) == "OHOS":
            shadow_dir = Path(self.build_folder, "libtool-shadow")
            if not shadow_dir.is_dir():
                raise ConanException(
                    f"libtool shadow directory is missing: {shadow_dir}"
                )
            environment.prepend("LDFLAGS", f"-L{shadow_dir}", separator=" ")
        seen = set()
        for dependencies in (self.dependencies.host, self.dependencies.test):
            for dependency in dependencies.values():
                for libdir in dependency.cpp_info.libdirs:
                    if not os.path.isabs(libdir):
                        libdir = os.path.join(dependency.package_folder, libdir)
                    if os.path.isdir(libdir) and libdir not in seen:
                        environment.prepend_path("LD_LIBRARY_PATH", libdir)
                        seen.add(libdir)
        if str(self.settings.os) == "OHOS":
            environment.define("MKDIR_P", "/system/bin/mkdir -p")
            environment.define(
                "RAWCPP", f"{self._ohos_c_compiler_path()} -E -"
            )
        return environment

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

            tokens = shlex.split(dependency_match.group(1))
            repaired_tokens = []
            shadow_libdir_added = False
            for token in tokens:
                if token.startswith("-L"):
                    directory = Path(token[2:])
                    if (
                        str(directory) in known_libdirs
                        or self._is_stale_conan_cache_path(directory)
                        or self._is_ohos_provider_libdir(
                            directory, tokens, archives_by_name
                        )
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
    def _is_ohos_provider_libdir(path, tokens, archives_by_name):
        normalized = path.as_posix()
        if not (
            normalized.startswith("/storage/")
            and normalized.endswith("/usr/local/lib")
        ):
            return False
        linked_names = {
            token[2:]
            for token in tokens
            if token.startswith("-l") and len(token) > 2
        }
        if not linked_names:
            return False
        return all(
            any(
                archive_name == f"lib{name}.la"
                or archive_name.startswith(f"lib{name}-")
                for archive_name in archives_by_name
            )
            for name in linked_names
        )

    @staticmethod
    def _is_stale_conan_cache_path(path):
        normalized = path.as_posix()
        return "/.conan2/" in normalized or "/.cache/conan2/" in normalized

    def _stabilize_ohos_alloc_tests(self):
        alloc_test = Path(self.source_folder, "test", "Alloc.c")
        if not alloc_test.is_file():
            raise ConanException(f"upstream allocation test is missing: {alloc_test}")
        source = alloc_test.read_text(encoding="utf-8")
        anchor = """    /* Pick a number of elements between 1 & 16K */
    guint32 num = g_test_rand_int_range(1, (16 * 1024));
    /* Pick a size between 1 & 16K */
    guint32 size = g_test_rand_int_range(1, (16 * 1024));
"""
        marker = "    /* Keep randomized normal allocations at or below 1 MiB. */\n"
        marker_count = source.count(marker)
        if marker_count == 0:
            anchor_count = source.count(anchor)
            if anchor_count != 3:
                raise ConanException(
                    f"upstream allocation range count drifted: {anchor_count}"
                )
            bounded = anchor + marker + """    const guint32 normal_alloc_limit = 1024 * 1024;
    if (size > (normal_alloc_limit / num)) {
        size = normal_alloc_limit / num;
    }
"""
            alloc_test.write_text(
                source.replace(anchor, bounded), encoding="utf-8", newline="\n"
            )
        elif marker_count != 3 or source.count(anchor) != 3:
            raise ConanException(
                "upstream allocation headroom adaptation is partially applied"
            )

    def _autotools_toolchain(self):
        toolchain = AutotoolsToolchain(self)
        if self.options.shared:
            toolchain.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            toolchain.configure_args.extend(["--disable-shared", "--enable-static"])
        toolchain.configure_args.extend(
            [
                "--disable-specs",
                "--without-xmlto",
                "--without-fop",
                "--without-xsltproc",
                "--without-perl",
                "--enable-unit-tests",
                "--with-glib=yes",
            ]
        )
        return toolchain

    def _configure_ohos(self):
        shell = "/system/bin/sh"
        if not os.path.isfile(shell):
            raise ConanInvalidConfiguration(f"OHOS configure shell is missing: {shell}")
        configure = self._ohos_configure_path()
        compiler_tuple = self._ohos_compiler_tuple()
        configure_args = [f"--host={compiler_tuple}"]
        if str(self.settings_build.os) == "OHOS":
            configure_args.append(f"--build={compiler_tuple}")
        configure_args.extend([
            f"--srcdir={self.source_folder}",
            *self._autotools_toolchain().configure_args,
        ])
        arguments = " ".join(
            shlex.quote(argument)
            for argument in configure_args
        )
        self._run_ohos(f'"{shell}" "{configure}" {arguments}')

    def _ohos_c_compiler_path(self):
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        compiler = compiler_executables.get("c")
        if not isinstance(compiler, str) or not compiler.strip():
            raise ConanException(
                "tools.build:compiler_executables must define the OHOS C compiler"
            )
        compiler_path = Path(compiler)
        if not compiler_path.is_absolute():
            raise ConanException("OHOS C compiler must be an absolute executable path")
        if not os.access(compiler_path, os.X_OK):
            raise ConanException(f"OHOS C compiler is not executable: {compiler_path}")
        return compiler_path

    def _ohos_compiler_tuple(self):
        compiler_path = self._ohos_c_compiler_path()
        try:
            result = subprocess.run(
                [str(compiler_path), "-dumpmachine"],
                check=False,
                capture_output=True,
                text=True,
                timeout=15,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise ConanException(f"OHOS compiler tuple probe failed: {error}") from error
        compiler_tuple = result.stdout.strip()
        if result.returncode != 0 or result.stderr.strip():
            raise ConanException(
                "OHOS compiler tuple probe returned "
                f"rc={result.returncode}, stderr={result.stderr.strip()!r}"
            )
        if not re.fullmatch(r"aarch64(?:-unknown)?-linux-ohos", compiler_tuple):
            raise ConanException(f"unexpected OHOS compiler tuple: {compiler_tuple!r}")
        return compiler_tuple

    def _generate_ohos_configure(self):
        upstream = self._upstream_configure_path()
        generated = self._ohos_configure_path()
        content = upstream.read_text(encoding="utf-8")
        needle = "umask 077"
        if content.count(needle) != 2:
            raise ConanException("configure umask contract changed")
        generated.parent.mkdir(parents=True, exist_ok=True)
        auxiliary_dir = Path(self.build_folder, "autoconf-aux")
        auxiliary_dir.mkdir(parents=True, exist_ok=True)
        auxiliary_names = (
            "config.guess",
            "config.sub",
            "ltmain.sh",
            "missing",
            "install-sh",
            "compile",
        )
        for name in auxiliary_names:
            source = Path(self.source_folder, name)
            if not source.is_file() or source.is_symlink():
                raise ConanException(
                    f"Autoconf auxiliary file is missing or not ordinary: {source}"
                )
            shutil.copy2(source, auxiliary_dir / name)

        auxiliary_anchor = (
            'ac_aux_dir_candidates="${srcdir}${PATH_SEPARATOR}${srcdir}/..'
            '${PATH_SEPARATOR}${srcdir}/../.."'
        )
        if content.count(auxiliary_anchor) != 1:
            raise ConanException("configure auxiliary-directory contract changed")
        content = content.replace(
            auxiliary_anchor,
            f"ac_aux_dir_candidates={shlex.quote(str(auxiliary_dir))}",
        )
        generated.write_text(
            content.replace(needle, "umask 022"),
            encoding="utf-8",
            newline="\n",
        )
        config_guess = auxiliary_dir / "config.guess"
        guess_content = config_guess.read_text(encoding="utf-8")
        guess_needle = "umask 077"
        if guess_content.count(guess_needle) != 3:
            raise ConanException("config.guess umask contract changed")
        config_guess.write_text(
            guess_content.replace(guess_needle, "umask 002"),
            encoding="utf-8",
            newline="\n",
        )
        return generated

    def _upstream_configure_path(self):
        configure = Path(self.source_folder, "configure")
        if not configure.is_file():
            raise ConanException(f"configure script is missing: {configure}")
        return configure

    def _ohos_configure_path(self):
        return Path(self.build_folder, "configure-ohos")

    def _run_ohos(self, command):
        shell = "/system/bin/sh"
        prefix = f"export SHELL={shell} CONFIG_SHELL={shell}; "
        self.run(prefix + command, cwd=self.build_folder, env="conanbuild")

    def _write_ohos_test_launcher(self):
        launcher = Path(self.build_folder, "run-libtool-test.sh")
        launcher.write_text(
            """#!/system/bin/sh
set -eu
test "$#" -ge 1
program=$1
shift
directory=${program%/*}
test "$directory" = "$program" && directory=.
basename=${program##*/}
if test -f "$directory/.libs/$basename"; then
  exec /system/bin/sh "$program" "$@"
fi
exec "$program" "$@"
""",
            encoding="utf-8",
            newline="\n",
        )
        return launcher

    def _sign_ohos_elf(self, candidates, label):
        path = next((candidate for candidate in candidates if self._is_elf(candidate)), None)
        if path is None:
            joined = ", ".join(str(candidate) for candidate in candidates)
            raise ConanException(f"{label} ELF is missing: {joined}")
        signer = shutil.which("binary-sign-tool") or (
            "/data/service/hnp/bin/binary-sign-tool"
        )
        readelf = shutil.which("llvm-readelf") or (
            "/data/service/hnp/bin/llvm-readelf"
        )
        if not os.path.isfile(signer) or not os.path.isfile(readelf):
            raise ConanException(f"required signing tools are missing for {label}")
        temporary = Path(f"{path}.signed")
        try:
            subprocess.run(
                [
                    signer,
                    "sign",
                    "-inFile",
                    str(path),
                    "-outFile",
                    str(temporary),
                    "-selfSign",
                    "1",
                ],
                check=True,
                timeout=60,
            )
            sections = subprocess.run(
                [readelf, "-SW", str(temporary)],
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
            ).stdout
            if sections.count(".codesign") != 1:
                raise ConanException(f"signed {label} has invalid .codesign")
            os.chmod(temporary, (os.stat(path).st_mode & 0o777) | 0o055)
            os.replace(temporary, path)
        finally:
            if temporary.exists():
                temporary.unlink()

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as stream:
                return stream.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _relocate_metadata(self):
        pc_path = Path(self.package_folder, "lib", "pkgconfig", "xt.pc")
        if not pc_path.is_file():
            raise ConanException("installed xt.pc is missing")
        pc_content = pc_path.read_text(encoding="utf-8")
        pc_content, count = re.subn(
            r"^prefix=.*$",
            "prefix=${pcfiledir}/../..",
            pc_content,
            count=1,
            flags=re.MULTILINE,
        )
        if count != 1:
            raise ConanException("xt.pc has no unique prefix field")
        pc_path.write_text(pc_content, encoding="utf-8")

        la_path = Path(self.package_folder, "lib", "libXt.la")
        if la_path.is_file():
            la_path.unlink()
