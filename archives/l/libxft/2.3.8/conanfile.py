#!/usr/bin/env python3
"""Conan recipe for X.Org libXft 2.3.8.

2.3.8 is the last libXft release that ships the Autotools build (2.3.9
switched to Meson), so this recipe follows the X.Org Autotools pattern used
by libxext 1.3.7 rather than the Meson recipe of libxft 2.3.9.
"""

import os
import posixpath
import re
import shlex
import shutil
import stat
import subprocess
from pathlib import Path

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


class LibxftConan(ConanFile):
    name = "libxft"
    version = "2.3.8"
    description = "X.Org client-side FreeType font rendering library"
    license = "HPND-sell-variant"
    homepage = "https://gitlab.freedesktop.org/xorg/lib/libxft"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libx11/1.8.13", transitive_headers=True)
        self.requires("libxrender/0.9.12", transitive_headers=True)
        self.requires("fontconfig/2.18.3", transitive_headers=True)
        self.requires("freetype/2.14.3", transitive_headers=True)
        self.requires("xorgproto/2025.1", transitive_headers=True)

    def build_requirements(self):
        # Upstream configure.ac pins XORG_MACROS_VERSION(1.8); without
        # xorg-macros.pc the man page and DOCUSERDIR substitutions stay empty.
        self.tool_requires("util-macros/1.20.1")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libxft supports Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        AutotoolsDeps(self).generate()
        dependencies = PkgConfigDeps(self)
        dependencies.set_property("freetype", "pkg_config_name", "freetype2")
        dependencies.set_property("xorgproto", "pkg_config_name", "xproto")
        dependencies.generate()
        if str(self.settings.os) == "OHOS":
            self._prepare_ohos_libtool_shadow()
            self._prepare_ohos_runtime_view()
        self._autotools_toolchain().generate()
        # PkgConfigDeps writes its metadata into the generators folder, but it
        # is not added to PKG_CONFIG_PATH on its own, so upstream
        # PKG_CHECK_MODULES probes cannot see the Conan-generated packages.
        self.buildenv_info.append_path(
            "PKG_CONFIG_PATH", self.generators_folder
        )

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
        if str(self.settings.os) == "OHOS" and self.options.shared:
            self._drop_build_rpath()
            self._materialize_shared_aliases()
        self._relocate_metadata()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = ["Xft"]
        self.cpp_info.requires = [
            "libx11::libx11",
            "libxrender::libxrender",
            "fontconfig::fontconfig",
            "freetype::freetype",
            "xorgproto::xorgproto",
        ]
        self.cpp_info.set_property("cmake_file_name", "libxft")
        self.cpp_info.set_property("cmake_target_name", "libxft::libxft")
        self.cpp_info.set_property("pkg_config_name", "xft")
        pc_dir = os.path.join(self.package_folder, "lib", "pkgconfig")
        self.buildenv_info.append_path("PKG_CONFIG_PATH", pc_dir)
        self.runenv_info.append_path("PKG_CONFIG_PATH", pc_dir)

    # ── build environment ────────────────────────────────────────────────

    def _build_environment(self):
        environment = Environment()
        temporary = Path(self.build_folder, ".tmp")
        temporary.mkdir(parents=True, exist_ok=True)
        environment.define_path("TMPDIR", str(temporary))
        if str(self.settings.os) == "OHOS":
            shadow_dir = Path(self.build_folder, "libtool-shadow")
            if not shadow_dir.is_dir():
                raise ConanException(
                    f"libtool shadow directory is missing: {shadow_dir}"
                )
            view_dir = Path(self.build_folder, "runtime-libs")
            if not view_dir.is_dir():
                raise ConanException(
                    f"OHOS runtime view directory is missing: {view_dir}"
                )
            # DT_RPATH (not DT_RUNPATH) so that the search path also covers the
            # transitive NEEDED entries of the dependency closure. The rpath is
            # baked into the binaries this recipe builds, which is what makes
            # the autoconf run probes loadable.
            environment.prepend(
                "LDFLAGS",
                f"-L{shadow_dir} -L{view_dir} "
                "-Wl,--disable-new-dtags "
                f"-Wl,-rpath,{view_dir}",
                separator=" ",
            )
            # LD_LIBRARY_PATH is deliberately NOT exported on OHOS. The loader
            # here gives it precedence over an embedded DT_RPATH *and* it is
            # inherited by every child process, so the view's copies of
            # dependency libraries would also be handed to toolchain binaries:
            # on the CI workers clang's `lld` then resolves libxml2 symbols
            # against the Conan libxml2 and dies with
            #   Error relocating .../llvm/bin/lld: xmlFreeDoc: symbol not found
            # which autoconf reports as "C compiler cannot create executables".
            # The measured three-way probe showed that DT_RPATH alone is enough
            # for the run probes, so no global runtime path is needed here.
        else:
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
        library_args = (
            ("--enable-shared", "--disable-static")
            if self.options.shared
            else ("--disable-shared", "--enable-static")
        )
        toolchain.configure_args.extend(
            argument
            for argument in library_args
            if argument not in toolchain.configure_args
        )
        return toolchain

    # ── OHOS Autotools execution path ────────────────────────────────────

    def _configure_ohos(self):
        shell = self._ohos_shell_path()
        configure_args = [
            f"--srcdir={self.source_folder}",
            *self._autotools_toolchain().configure_args,
        ]
        arguments = " ".join(shlex.quote(argument) for argument in configure_args)
        try:
            self._run_ohos(
                f'"{shell}" "{self._ohos_configure_path()}" {arguments}'
            )
        except Exception as error:
            # autoconf sends the compiler/linker output of every probe to
            # config.log, so configure's own stderr alone ("C compiler cannot
            # create executables") never names the real first failure. Replay
            # it here instead of guessing from the last visible line.
            self._report_config_log()
            raise

    def _report_config_log(self):
        log_path = Path(self.build_folder, "config.log")
        if not log_path.is_file():
            self.output.error(f"configure failed and {log_path} was not created")
            return
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
        # Only unambiguous failure markers: bare "error" also appears in the
        # thousands of "-Werror=..." feature probes autoconf logs on success.
        error_probe = re.compile(
            r"(error:|cannot find -l|undefined reference|ld: |llvm-|clang"
            r"[\d.]*: |Permission denied|No such file or directory"
            r"|cannot execute)"
        )
        errors = [line for line in lines if error_probe.search(line)]
        self.output.error(
            "config.log evidence — failure markers:\n"
            + ("\n".join(errors[:25]) if errors else "(none)")
            + "\nconfig.log tail (failing command and its output):\n"
            + "\n".join(lines[-30:])
        )

    def _generate_ohos_configure(self):
        """Copy the generated ``configure`` with the HMDFS umask fixed up.

        Upstream ``configure`` runs ``umask 077`` before it creates the
        ``config.status`` scratch directory. HMDFS projects that mode into an
        owner-unwritable directory, so ``config.status`` cannot write
        ``subs1.awk`` and aborts with "could not setup config files machinery".
        ``configure`` is a generated file, so it is repaired in a build-local
        copy instead of a source patch (R6); the exported source stays
        byte-identical. Platform detection itself is fixed in the source:
        ``config.guess``/``config.sub`` carry the OHOS tuple patch.
        """
        upstream = self._upstream_configure_path()
        content = upstream.read_text(encoding="utf-8")
        needle = "umask 077"
        if content.count(needle) != 2:
            raise ConanException("configure umask contract changed")
        generated = self._ohos_configure_path()
        generated.parent.mkdir(parents=True, exist_ok=True)
        generated.write_text(
            content.replace(needle, "umask 022"),
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

    def _ohos_shell_path(self):
        shell = "/data/service/hnp/bin/bash"
        if not os.path.isfile(shell):
            raise ConanInvalidConfiguration(
                f"OHOS configure shell is missing: {shell}"
            )
        return shell

    def _run_ohos(self, command):
        shell = self._ohos_shell_path()
        prefix = f"export SHELL={shell} CONFIG_SHELL={shell}; "
        self.run(prefix + command, cwd=self.build_folder, env="conanbuild")

    # ── libtool shadow ───────────────────────────────────────────────────

    def _dependency_libdirs(self):
        libdirs = []
        for dependency in self.dependencies.host.values():
            for libdir in dependency.cpp_info.libdirs:
                directory = Path(libdir)
                if not directory.is_absolute():
                    directory = Path(dependency.package_folder, libdir)
                if directory.is_dir():
                    libdirs.append(directory)
        return libdirs

    def _prepare_ohos_libtool_shadow(self):
        """Rebind published libtool archives to a task-local view.

        The published ``.la`` files carry the ``-L`` and ``.la`` paths of the
        machine that built them, so libtool resolves ``-lX11`` or
        ``-lfreetype`` through stale metadata. The shadow copies every
        referenced artifact, rewrites ``libdir``/``dependency_libs`` into the
        build folder, and is searched before the dependency packages.
        """
        libtool_archives = {}
        for directory in self._dependency_libdirs():
            for archive in sorted(directory.glob("*.la")):
                libtool_archives.setdefault(archive.name, []).append(archive)

        shadow_dir = Path(self.build_folder, "libtool-shadow")
        shadow_dir.mkdir(parents=True, exist_ok=True)
        ambiguous = sorted(
            name for name, paths in libtool_archives.items() if len(paths) != 1
        )
        if ambiguous:
            raise ConanException(f"libtool archive basenames are ambiguous: {ambiguous}")
        archives_by_name = {
            name: paths[0] for name, paths in libtool_archives.items()
        }
        if not archives_by_name:
            raise ConanException("no libtool archives found in the dependency closure")

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
                    if not library_name:
                        continue
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
                        shutil.copyfile(source, shadow_dir / library_name)
                        artifact_sources[library_name] = source

        known_libdirs = {str(archive.parent) for archive in archives_by_name.values()}
        total_replacements = 0
        dropped_libdirs = []
        for archive_name, archive in archives_by_name.items():
            content = archive.read_text(encoding="utf-8")
            dependency_match = re.search(
                r"^dependency_libs='(.*)'$", content, flags=re.MULTILINE
            )
            if dependency_match is None:
                raise ConanException(f"{archive_name} has no dependency_libs field")

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
                    else:
                        # A -L of a directory that does not exist on this
                        # machine cannot contribute a symbol; keeping it only
                        # makes libtool search a phantom prefix.
                        dropped_libdirs.append(str(directory))
                        total_replacements += 1
                    continue
                if token.endswith(".la"):
                    dependency_name = (
                        posixpath.basename(token)
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
                raise ConanException(f"{archive_name} has no unique libdir field")
            (shadow_dir / archive_name).write_text(
                content, encoding="utf-8", newline="\n"
            )

        for shadow_archive in sorted(shadow_dir.glob("*.la")):
            content = shadow_archive.read_text(encoding="utf-8")
            dependency_match = re.search(
                r"^dependency_libs='(.*)'$", content, flags=re.MULTILINE
            )
            for token in shlex.split(dependency_match.group(1)):
                if token.endswith(".la") and not Path(token).is_file():
                    raise ConanException(
                        f"sanitized {shadow_archive.name} has a missing archive: {token}"
                    )
        self.output.info(
            f"prepared {len(archives_by_name)} libtool shadows with "
            f"{total_replacements} path replacements"
            + (f", dropped {len(dropped_libdirs)} absent libdirs" if dropped_libdirs else "")
        )

    @staticmethod
    def _is_stale_conan_cache_path(path):
        normalized = path.as_posix()
        return "/.conan2/" in normalized or "/.cache/conan2/" in normalized

    # ── OHOS runtime view ────────────────────────────────────────────────

    def _prepare_ohos_runtime_view(self):
        """Materialise and self-sign the dependency shared-library closure.

        ``AutotoolsDeps`` exports ``LIBS``, so even autoconf's very first
        ``AC_PROG_CC`` run probe links against the dependency closure. Three
        measured loader behaviours make that probe fail on this device:

        * a shared object whose ELF signature the device does not accept is
          refused with ``Permission denied`` rather than ``No such file``
          (``E135``), and a published package can carry a signature that no
          longer validates on the consumer;
        * the versioned aliases the packages ship are symlinks, which the
          loader cannot resolve under HMDFS, so the SONAME name is not
          findable in the package directory at all;
        * ``LD_LIBRARY_PATH`` *is* honoured here and takes precedence over an
          embedded ``DT_RPATH``, so pointing it at those package directories
          defeats a rpath that would otherwise work (see
          ``_build_environment`` below).

        The closure is therefore materialised as regular files in a
        task-local directory, re-signed there, and reached both by that
        ``LD_LIBRARY_PATH`` value and by an embedded ``DT_RPATH``. The
        dependency packages themselves are never modified.
        """
        view_dir = Path(self.build_folder, "runtime-libs")
        view_dir.mkdir(parents=True, exist_ok=True)
        materialised = set()
        for dependency in self.dependencies.host.values():
            for libdir in dependency.cpp_info.libdirs:
                directory = Path(libdir)
                if not directory.is_absolute():
                    directory = Path(dependency.package_folder, libdir)
                if not directory.is_dir():
                    continue
                package_root = Path(dependency.package_folder).resolve(
                    strict=True
                )
                for entry in sorted(directory.iterdir(), key=lambda p: p.name):
                    if not (entry.name.endswith(".so") or ".so." in entry.name):
                        continue
                    real = entry.resolve(strict=True) if entry.is_symlink() else entry
                    if not real.is_file():
                        raise ConanException(
                            f"dependency shared object is not a file: {entry}"
                        )
                    try:
                        real.relative_to(package_root)
                    except ValueError as error:
                        raise ConanException(
                            f"dependency shared object escapes its package: {entry}"
                        ) from error
                    destination = view_dir / entry.name
                    if destination.exists():
                        if not self._same_bytes(destination, real):
                            raise ConanException(
                                "runtime view basename collision with different "
                                f"contents: {entry.name}"
                            )
                        continue
                    shutil.copyfile(real, destination)
                    materialised.add(entry.name)
        if not materialised:
            raise ConanException("OHOS runtime library view is empty")
        # Sign every object in the view, not only the freshly copied ones: a
        # basename can be contributed by several packages and the earlier copy
        # may already carry a signature that this device rejects.
        for entry in sorted(view_dir.iterdir(), key=lambda p: p.name):
            if entry.name.endswith(".so") or ".so." in entry.name:
                self._sign_ohos_elf(entry)
        self.output.info(
            f"materialised and re-signed {len(materialised)} shared objects "
            f"in {view_dir}"
        )
        return view_dir

    def _sign_ohos_elf(self, path):
        """Drop any stale signature, self-sign, then validate the result."""
        readelf = self._ohos_tool("llvm-readelf")
        objcopy = self._ohos_tool("llvm-objcopy")
        signer = self._ohos_tool("binary-sign-tool")
        removed = subprocess.run(
            [objcopy, "--remove-section", ".codesign", str(path)],
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if removed.returncode != 0:
            raise ConanException(
                f"cannot drop .codesign from {path}: {removed.stderr.strip()}"
            )
        temporary = Path(f"{path}.signed")
        if temporary.exists():
            raise ConanException(f"stale signing output exists: {temporary}")
        try:
            signing = subprocess.run(
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
                check=False,
                capture_output=True,
                text=True,
                timeout=180,
            )
            if signing.returncode != 0:
                raise ConanException(
                    f"binary-sign-tool failed for {path}: {signing.stderr.strip()}"
                )
            os.chmod(temporary, (os.stat(path).st_mode & 0o777) | 0o755)
            os.replace(temporary, path)
        finally:
            if temporary.exists():
                os.unlink(temporary)
        final = subprocess.run(
            [readelf, "-SW", str(path)],
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        ).stdout
        if final.count(".codesign") != 1:
            raise ConanException(f"signed ELF has invalid .codesign: {path}")
        return True

    def _ohos_tool(self, name):
        tool = shutil.which(name) or f"/data/service/hnp/bin/{name}"
        if not os.path.isfile(tool):
            raise ConanInvalidConfiguration(
                f"required OHOS tool is missing: {name}"
            )
        return tool

    # ── installed metadata ───────────────────────────────────────────────

    def _drop_build_rpath(self):
        """Keep machine-local build paths out of the shipped library.

        The embedded ``DT_RPATH`` only exists so that autoconf probes can run
        during ``configure``; publishing it would encode this machine's Conan
        cache layout, which is what the other X.Org packages avoid.
        """
        patchelf = shutil.which("patchelf") or "/data/service/hnp/bin/patchelf"
        if not os.path.isfile(patchelf):
            raise ConanInvalidConfiguration(
                "OHOS packaging requires patchelf to drop the build rpath"
            )
        readelf = self._ohos_tool("llvm-readelf")
        library_dir = Path(self.package_folder, "lib")
        dropped = 0
        for entry in sorted(library_dir.glob("libXft.so*")):
            if entry.is_symlink() or not entry.is_file():
                continue
            dynamic = subprocess.run(
                [readelf, "-d", str(entry)],
                check=True,
                capture_output=True,
                text=True,
                timeout=60,
            ).stdout
            if "(RPATH)" not in dynamic and "(RUNPATH)" not in dynamic:
                continue
            view_dir = Path(self.build_folder, "runtime-libs")
            if str(view_dir) not in dynamic:
                raise ConanException(
                    f"{entry.name} carries an unexpected search path: {dynamic}"
                )
            subprocess.run(
                [patchelf, "--remove-rpath", str(entry)],
                check=True,
                capture_output=True,
                text=True,
                timeout=120,
            )
            after = subprocess.run(
                [readelf, "-d", str(entry)],
                check=True,
                capture_output=True,
                text=True,
                timeout=60,
            ).stdout
            if "(RPATH)" in after or "(RUNPATH)" in after:
                raise ConanException(
                    f"build rpath is still present in {entry.name}"
                )
            dropped += 1
        self.output.info(f"dropped the build rpath from {dropped} shared objects")

    def _materialize_shared_aliases(self):
        """Turn the versioned aliases into regular files.

        ``libtool`` installs ``libXft.so.2.3.8`` plus the ``libXft.so.2``
        (SONAME) and ``libXft.so`` (development) symlinks. The OHOS loader
        cannot resolve a shared object through a symlinked alias, so a
        consumer that points ``LD_LIBRARY_PATH`` or an rpath straight at the
        package directory fails with "Error loading shared
        library libXft.so.2" even though the file is there. The aliases are
        therefore materialised byte-for-byte; the cost is two extra copies of
        a ~106 KiB library, and the loader contract in ``test_package`` proves
        the result instead of trusting ``ls``.
        """
        library_dir = Path(self.package_folder, "lib")
        real = sorted(
            entry
            for entry in library_dir.glob("libXft.so.*.*.*")
            if not entry.is_symlink() and entry.is_file()
        )
        if len(real) != 1:
            raise ConanException(
                f"expected exactly one real libXft shared object, found {len(real)}"
            )
        source = real[0]
        soname = subprocess.run(
            [self._ohos_tool("llvm-readelf"), "-d", str(source)],
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        ).stdout
        match = re.search(r"\(SONAME\)\s+Library soname: \[([^]]+)\]", soname)
        if match is None:
            raise ConanException(f"installed libXft has no SONAME: {source}")
        aliases = [library_dir / "libXft.so", library_dir / match.group(1)]
        materialised = 0
        for alias in aliases:
            if alias == source:
                continue
            if not alias.exists() and not alias.is_symlink():
                raise ConanException(f"expected installed alias is missing: {alias}")
            if alias.is_symlink():
                if not os.path.samefile(alias, source):
                    raise ConanException(
                        f"installed libXft alias has the wrong target: {alias}"
                    )
                alias.unlink()
                shutil.copyfile(source, alias)
                # Preserve the mode: a library without the owner execute bit
                # cannot be mapped PROT_EXEC and the loader rejects it with
                # "Permission denied" even though the bytes are identical.
                shutil.copymode(source, alias)
                materialised += 1
            if alias.is_symlink() or not alias.is_file():
                raise ConanException(
                    f"libXft alias was not materialised: {alias}"
                )
            if stat.S_IMODE(alias.stat().st_mode) & stat.S_IXUSR == 0:
                raise ConanException(
                    f"materialised libXft alias is not executable: {alias}"
                )
            if not self._same_bytes(alias, source):
                raise ConanException(
                    f"materialised libXft alias differs from its source: {alias}"
                )
        if materialised == 0:
            raise ConanException("no libXft alias needed materialisation")
        self.output.info(
            f"materialised {materialised} shared-library aliases as regular files"
        )

    @staticmethod
    def _same_bytes(left, right):
        if left.stat().st_size != right.stat().st_size:
            return False
        with left.open("rb") as left_stream, right.open("rb") as right_stream:
            while True:
                left_block = left_stream.read(1024 * 1024)
                right_block = right_stream.read(1024 * 1024)
                if left_block != right_block:
                    return False
                if not left_block:
                    return True

    def _relocate_metadata(self):
        pc_path = Path(self.package_folder, "lib", "pkgconfig", "xft.pc")
        if not pc_path.is_file():
            raise ConanException("installed xft.pc is missing")
        content = pc_path.read_text(encoding="utf-8")
        content, count = re.subn(
            r"^prefix=.*$",
            "prefix=${pcfiledir}/../..",
            content,
            count=1,
            flags=re.MULTILINE,
        )
        if count != 1:
            raise ConanException("xft.pc has no unique prefix field")
        pc_path.write_text(content, encoding="utf-8")

        for archive in Path(self.package_folder, "lib").glob("*.la"):
            archive.unlink()
