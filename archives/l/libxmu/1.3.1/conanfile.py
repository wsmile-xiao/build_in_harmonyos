#!/usr/bin/env python3
"""Conan recipe for libXmu 1.3.1 (X.Org X11 miscellaneous utility library).

Produces two shared libraries:
  - libXmu.so  (depends on libXt, libXext, libX11)
  - libXmuu.so (depends on libX11, subset of libXmu without Xt)
"""
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


class LibxmuConan(ConanFile):
    name = "libxmu"
    version = "1.3.1"
    description = "X.Org X11 miscellaneous utility library (libXmu + libXmuu)"
    license = "MIT"
    homepage = "https://gitlab.freedesktop.org/xorg/lib/libxmu"
    url = "https://xorg.freedesktop.org/releases/individual/lib/"

    package_type = "library"

    # R32: settings.os must accept both Linux and OHOS
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    # shared=True so the Conan graph matches the already-published binaries of
    # libxext/6.4.0 (shared=True) and libxt/1.3.1. libXmu ships as .so on OHOS.
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Upstream configure.ac: PKG_CHECK_MODULES(XMU, [xt >= 1.1 xext x11 xextproto])
        #                      PKG_CHECK_MODULES(XMUU, x11)
        self.requires("libxt/1.3.1")
        self.requires("libxext/6.4.0.1")
        # Pin libx11/1.8.13 across the whole graph. libx11/1.8.13 keeps
        # libX11.la in package() (_patch_libtool_libdir), whereas
        # libx11/6.4.0's package() does rm("*.la") — and libxt's
        # _prepare_ohos_libtool_shadow() hard-requires libX11.la.
        # force=True propagates the pin to transitive nodes; when the
        # CI worker lacks a compatible libx11/1.8.13 binary, Conan falls
        # back to --build=missing and rebuilds 1.8.13 from source.
        self.requires("libx11/1.8.13", force=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()
        if str(self.settings.os) == "OHOS":
            self._prepare_ohos_libtool_shadow()
        tc = AutotoolsToolchain(self)
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        environment = self._build_environment()
        with environment.vars(self).apply():
            if str(self.settings.os) == "OHOS":
                self._generate_ohos_configure()
                self._configure_ohos()
                self._run_ohos("make -j1")
            else:
                autotools = Autotools(self)
                autotools.configure()
                autotools.make(args=["-j1"])

    def package(self):
        environment = self._build_environment()
        with environment.vars(self).apply():
            if str(self.settings.os) == "OHOS":
                # autotools installs to $(prefix)/lib; point prefix at the
                # Conan package folder so .so/.la land in lib/, not usr/local/lib.
                prefix = shlex.quote(self.package_folder)
                self._run_ohos(f"make -j1 install DESTDIR= prefix={prefix}")
            else:
                Autotools(self).install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        # Headers install to include/X11/Xmu/*.h; consumers #include <X11/Xmu/...>.
        # libXmu: full utility library (links Xt, Xext, X11)
        self.cpp_info.components["xmu"].libs = ["Xmu"]
        self.cpp_info.components["xmu"].requires = ["libxt::libxt", "libxext::libxext", "libx11::libx11"]
        # libXmuu: Xt-independent subset (links X11 only)
        self.cpp_info.components["xmuu"].libs = ["Xmuu"]
        self.cpp_info.components["xmuu"].requires = ["libx11::libx11"]
        # CMakeDeps needs explicit component->target mapping so that
        # find_package(libxmu) exposes libxmu::Xmu and libxmu::Xmuu.
        self.cpp_info.set_property("cmake_file_name", "libxmu")
        for component, cmake_target in (("xmu", "Xmu"), ("xmuu", "Xmuu")):
            self.cpp_info.components[component].set_property(
                "cmake_target_name", f"libxmu::{cmake_target}"
            )
            self.cpp_info.components[component].set_property(
                "pkg_config_name", f"lib{cmake_target.lower()}"
            )

    # ──────────────────────────────────────────────────────────────────
    # Build environment
    # ──────────────────────────────────────────────────────────────────

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

    # ──────────────────────────────────────────────────────────────────
    # OHOS libtool shadow
    # ──────────────────────────────────────────────────────────────────

    def _prepare_ohos_libtool_shadow(self):
        """Collect every ``*.la`` from direct host dependencies into a
        single ``libtool-shadow`` directory and rewrite their
        ``dependency_libs``/``libdir`` fields so libtool links against
        the shadow copies instead of the stale Conan cache paths.

        libx11/6.4.0's package() removes ``libX11.la`` (rm("*.la")), so
        when the CI graph resolves to libx11/6.4.0 the shadow cannot be
        built and libxt's own _prepare_ohos_libtool_shadow() fails with
        ``expected one installed libX11.la, found 0``. To keep local and
        CI behaviour identical we synthesise a minimal ``libX11.la``
        from the shared object when the upstream archive is missing.
        """
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

        # Ensure every dependency has a libX11.la — synthesize one from
        # the shared object if the package removed it.
        self._ensure_libx11_la(libtool_archives)

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
                    ):
                        if not shadow_libdir_added:
                            repaired_tokens.append(f"-L{shadow_dir}")
                            shadow_libdir_added = True
                        total_replacements += 1
                    elif directory.is_dir():
                        repaired_tokens.append(token)
                    elif os.name == "nt" and token.startswith("-L/"):
                        repaired_tokens.append(token)
                    elif self._is_system_libdir(directory):
                        # /usr/local/lib, /usr/lib, /lib — present on the
                        # dev machine but not on the CI worker. Drop the
                        # -L flag; the shadow -L added above covers linking.
                        total_replacements += 1
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

    def _ensure_libx11_la(self, libtool_archives):
        """Synthesize a minimal ``libX11.la`` from the shared object when
        the upstream package removed it (libx11/6.4.0 does
        ``rm("*.la")`` in package()). This keeps libxt's
        _prepare_ohos_libtool_shadow() from failing with
        ``expected one installed libX11.la, found 0``.
        """
        if "libX11.la" in libtool_archives:
            return
        libx11_dep = None
        for dep in self.dependencies.host.values():
            if dep.ref.name == "libx11":
                libx11_dep = dep
                break
        if libx11_dep is None:
            return
        # Find the lib directory containing libX11.so*
        for libdir in libx11_dep.cpp_info.libdirs:
            directory = Path(libdir)
            if not directory.is_absolute():
                directory = Path(libx11_dep.package_folder, libdir)
            if not directory.is_dir():
                continue
            # Look for the shared object (libX11.so or libX11.so.6)
            so_files = sorted(directory.glob("libX11.so*"))
            if not so_files:
                continue
            # Resolve symlinks to get the real file
            real_so = so_files[0].resolve()
            soname = real_so.name
            # Generate a minimal .la file
            la_content = f"""# libX11.la - synthesized by libxmu/1.3.1
# Generated because libx11/6.4.0's package() removes .la files (rm("*.la")),
# but libxt's _prepare_ohos_libtool_shadow() requires libX11.la.
# This is a minimal libtool archive sufficient for libtool linking.

# The name that we can dlopen(3).
dlname='{soname}'

# Names of this library.
library_names='{soname} libX11.so.6 libX11.so'

# The name of the static archive.
old_library=''

# Linker flags that cannot go in dependency_libs.
inherited_linker_flags=''

# Libraries that this one depends on.
dependency_libs=' -lpthread '

# Names of additional weak libraries provided by this library.
weak_library_names=''

# Version information for libX11.
current=10
age=4
revision=0

# Is this an already installed library?
installed=yes

# Should we warn about portability when linking against -modules?
shouldnotlink=no

# Files to dlopen/dlpreopen
dlopen=''
dlpreopen=''

# Directory that this library needs to be installed in:
libdir='{directory}'
"""
            la_path = directory / "libX11.la"
            la_path.write_text(la_content, encoding="utf-8", newline="\n")
            libtool_archives.setdefault("libX11.la", []).append(la_path)
            self.output.info(f"synthesized {la_path}")
            return

    @staticmethod
    def _is_stale_conan_cache_path(path):
        """A Conan cache path (either ``.conan2`` or ``.cache/conan2``)
        that no longer exists is stale and should be rewritten to the
        shadow directory."""
        if path.exists():
            return False
        path_str = str(path)
        return ".conan2" in path_str or ".cache/conan2" in path_str

    @staticmethod
    def _is_system_libdir(path):
        """True for standard system library directories like
        ``/usr/local/lib`` that exist on the dev machine but not on the
        CI worker. The shadow ``-L`` covers linking, so these tokens can
        be dropped silently."""
        if path.exists():
            return False
        resolved = str(path)
        system_libdirs = (
            "/usr/local/lib",
            "/usr/local/lib64",
            "/usr/lib",
            "/usr/lib64",
            "/lib",
            "/lib64",
        )
        return resolved in system_libdirs

    # ──────────────────────────────────────────────────────────────────
    # OHOS configure / build helpers (mirrors libxt 1.3.1)
    # ──────────────────────────────────────────────────────────────────

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

    def _upstream_configure_path(self):
        configure = Path(self.source_folder, "configure")
        if not configure.is_file():
            raise ConanException(f"configure script is missing: {configure}")
        return configure

    def _ohos_configure_path(self):
        return Path(self.build_folder, "configure-ohos")

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
            "depcomp",
            "tap-driver.sh",
            "test-driver",
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
        ])
        arguments = " ".join(
            shlex.quote(argument)
            for argument in configure_args
        )
        self._run_ohos(f'"{shell}" "{configure}" {arguments}')

    def _run_ohos(self, command):
        shell = "/system/bin/sh"
        prefix = f"export SHELL={shell} CONFIG_SHELL={shell}; "
        self.run(prefix + command, cwd=self.build_folder, env="conanbuild")
