#!/usr/bin/env python3
"""Conan recipe for GLib 2.88.3.1 (Meson)."""

import filecmp
import os
import posixpath
import re
import shlex
import shutil
import stat
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import (
    apply_conandata_patches,
    check_sha256,
    copy,
    export_conandata_patches,
    get,
    rmdir,
    unzip,
)
from conan.tools.layout import basic_layout
from conan.tools.gnu import PkgConfigDeps
from conan.tools.meson import Meson, MesonToolchain


class Glib2Conan(ConanFile):
    name = "glib"
    version = "2.88.3.1"
    description = "GNOME core utility, object, I/O, module, and thread libraries"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/glib"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    _shared_library_targets = (
        ("glib", "glib-2.0", "libglib-2.0"),
        ("gobject", "gobject-2.0", "libgobject-2.0"),
        ("gmodule", "gmodule-2.0", "libgmodule-2.0"),
        ("gio", "gio-2.0", "libgio-2.0"),
        ("gthread", "gthread-2.0", "libgthread-2.0"),
        ("girepository", "girepository-2.0", "libgirepository-2.0"),
    )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("pcre2/10.47")
        self.requires("libffi/3.5.2")
        self.requires("zlib/1.3.2")
        self.requires("proxy-libintl/0.5")

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(
                "GLib's target adaptation is validated only for AArch64"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        source = self.conan_data["sources"]
        configured_archive = self.conf.get(
            "user.glib:source_archive", default=None
        )
        if not configured_archive:
            get(self, **source, strip_root=True)
            return

        configured_archive = os.path.abspath(os.fspath(configured_archive))
        if not os.path.isfile(configured_archive):
            raise ConanInvalidConfiguration(
                "user.glib:source_archive does not name a regular file"
            )
        check_sha256(self, configured_archive, source["sha256"])
        local_archive = os.path.join(self.source_folder, "glib-2.88.3.tar.xz")
        if os.path.normcase(configured_archive) != os.path.normcase(local_archive):
            shutil.copy2(configured_archive, local_archive)
        check_sha256(self, local_archive, source["sha256"])
        unzip(self, local_archive, destination=self.source_folder, strip_root=True)

    @staticmethod
    def _require_absolute_tool(value, label, target_posix=False):
        if not isinstance(value, (str, os.PathLike)):
            raise ConanInvalidConfiguration(
                f"tools.build:compiler_executables[{label!r}] must be a path"
            )
        path = os.fspath(value)
        if target_posix:
            if not posixpath.isabs(path):
                raise ConanInvalidConfiguration(
                    f"tools.build:compiler_executables[{label!r}] must be an "
                    "absolute POSIX target path"
                )
            return posixpath.normpath(path)
        if not os.path.isabs(path) or not os.path.isfile(path):
            raise ConanInvalidConfiguration(
                f"tools.build:compiler_executables[{label!r}] must name an "
                "absolute regular file"
            )
        if not os.access(path, os.X_OK):
            raise ConanInvalidConfiguration(
                f"tools.build:compiler_executables[{label!r}] is not executable"
            )
        return os.path.normpath(path)

    @classmethod
    def _resolve_llvm_tools(cls, executables, target_os=None):
        if not isinstance(executables, dict):
            raise ConanInvalidConfiguration(
                "tools.build:compiler_executables must be a dictionary"
            )
        target_posix = str(target_os) == "OHOS"
        compiler = cls._require_absolute_tool(
            executables.get("c"), "c", target_posix=target_posix
        )
        compiler_name = posixpath.basename(compiler) if target_posix else os.path.basename(compiler)
        match = re.fullmatch(r"clang(?:-([0-9]+))?", compiler_name)
        if match is None:
            raise ConanInvalidConfiguration(
                "the configured C compiler must be clang or clang-<version>"
            )
        suffix = f"-{match.group(1)}" if match.group(1) else ""
        compiler_dir = posixpath.dirname(compiler) if target_posix else os.path.dirname(compiler)
        resolved = {}
        for name in ("ar", "ranlib", "nm", "objcopy", "strip"):
            configured = executables.get(name)
            if configured:
                resolved[name] = cls._require_absolute_tool(
                    configured, name, target_posix=target_posix
                )
                continue
            candidates = [
                (posixpath.join(compiler_dir, f"llvm-{name}{suffix}"),
                 posixpath.join(compiler_dir, f"llvm-{name}"))
                if target_posix else
                (os.path.join(compiler_dir, f"llvm-{name}{suffix}"),
                 os.path.join(compiler_dir, f"llvm-{name}")),
            ]
            candidates = candidates[0]
            if target_posix:
                resolved[name] = candidates[0]
                continue
            for candidate in dict.fromkeys(candidates):
                if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                    resolved[name] = os.path.normpath(candidate)
                    break
            if name not in resolved:
                raise ConanInvalidConfiguration(
                    f"cannot resolve llvm-{name} beside the configured C compiler"
                )
        return resolved

    def generate(self):
        pkg_config = PkgConfigDeps(self)
        pkg_config.set_property(
            "proxy-libintl", "pkg_config_name", "proxy-libintl"
        )
        pkg_config.generate()

        toolchain = MesonToolchain(self)
        if str(self.settings.os) in ("Linux", "OHOS"):
            executables = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
            tools = self._resolve_llvm_tools(executables, target_os=self.settings.os)
            toolchain.ar = tools["ar"]
            toolchain.strip = tools["strip"]
            toolchain.binaries["ranlib"] = tools["ranlib"]
            toolchain.binaries["nm"] = tools["nm"]
            toolchain.binaries["objcopy"] = tools["objcopy"]
        toolchain.project_options["default_library"] = (
            "shared" if self.options.shared else "static"
        )
        toolchain.project_options["wrap_mode"] = "nofallback"
        toolchain.project_options["netlink_monitor"] = "disabled"
        toolchain.project_options["libmount"] = "disabled"
        toolchain.project_options["selinux"] = "disabled"
        toolchain.project_options["nls"] = "disabled"
        toolchain.project_options["introspection"] = "disabled"
        toolchain.project_options["man-pages"] = "disabled"
        toolchain.project_options["documentation"] = "false"
        toolchain.project_options["gtk_doc"] = "false"
        toolchain.project_options["sysprof"] = "disabled"
        toolchain.project_options["oss_fuzz"] = "disabled"
        toolchain.project_options["tests"] = "true"
        toolchain.project_options["installed_tests"] = "true"
        toolchain.generate()

    def _build_runtime_directories(self):
        directories = []
        # Meson executes freshly linked GLib tools before install.  Use exact
        # build-tree paths so their shared libraries are visible to the target
        # loader even when build RPATH handling is unavailable.
        for subdirectory in (
            "glib",
            "gobject",
            "gmodule",
            "gio",
            "gthread",
            "girepository",
        ):
            directories.append(os.path.join(self.build_folder, subdirectory))
        for dependency in self.dependencies.host.values():
            if not dependency.package_folder:
                continue
            for libdir in dependency.cpp_info.libdirs:
                if not os.path.isabs(libdir):
                    libdir = os.path.join(dependency.package_folder, libdir)
                if os.path.isdir(libdir):
                    directories.append(libdir)
        return directories

    def _run_meson_with_build_runtime(self, arguments, environment=None):
        command = ["meson", *arguments]
        runtime_path = ":".join(self._build_runtime_directories())
        if not runtime_path:
            raise ConanInvalidConfiguration("GLib build runtime path is empty")
        assignments = [
            f"LD_LIBRARY_PATH={shlex.quote(runtime_path)}"
            "${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
        ]
        for name, value in sorted((environment or {}).items()):
            assignments.append(f"{name}={shlex.quote(value)}")
        self.run(
            " ".join(assignments)
            + " "
            + " ".join(shlex.quote(argument) for argument in command),
            env="conanbuild",
        )

    def _materialize_shared_library_aliases(
        self, directory, stems, preserve_soname_inode=False
    ):
        def _alias_mode_ok(alias, source_mode):
            # E046: HMDFS 等受限文件系统可能使 chmod/copymode 无效。此时只要求
            # 别名保持普通文件、字节一致且 owner 可执行，模式差异记录为平台限制；
            # chmod 生效的环境（CI/真实设备）仍按严格模式相等校验。
            actual = stat.S_IMODE(
                os.stat(alias, follow_symlinks=False).st_mode
            )
            if actual == source_mode:
                return True
            try:
                os.chmod(alias, source_mode)
            except OSError:
                pass
            actual = stat.S_IMODE(
                os.stat(alias, follow_symlinks=False).st_mode
            )
            if actual == source_mode:
                return True
            if actual & stat.S_IXUSR:
                self.output.info(
                    f"E046 platform limitation: chmod ineffective for {alias!r} "
                    f"(mode {oct(actual)} != {oct(source_mode)}); alias kept "
                    "byte-identical and owner-executable"
                )
                return True
            return False
        for stem in stems:
            pattern = re.compile(
                rf"^{re.escape(stem)}[.]so[.](?P<version>[0-9]+(?:[.][0-9]+)+)$"
            )
            sources = []
            if os.path.isdir(directory):
                for name in os.listdir(directory):
                    path = os.path.join(directory, name)
                    if (
                        pattern.fullmatch(name)
                        and os.path.isfile(path)
                        and not os.path.islink(path)
                    ):
                        sources.append(path)
            if len(sources) != 1:
                raise ConanInvalidConfiguration(
                    f"expected one versioned shared object for {stem!r} in "
                    f"{directory!r}, found {len(sources)}"
                )

            source = sources[0]
            source_stat = os.stat(source, follow_symlinks=False)
            source_mode = stat.S_IMODE(source_stat.st_mode)
            source_identity = (source_stat.st_dev, source_stat.st_ino)
            if os.name == "posix" and not source_mode & stat.S_IXUSR:
                raise ConanInvalidConfiguration(
                    f"versioned shared object is not owner-executable: {source!r}"
                )
            version = pattern.fullmatch(os.path.basename(source)).group("version")
            aliases = (f"{stem}.so.{version.split('.', 1)[0]}", f"{stem}.so")
            alias_states = []
            for alias_name in aliases:
                alias = os.path.join(directory, alias_name)
                if os.path.lexists(alias):
                    if os.path.islink(alias):
                        try:
                            same_source = os.path.samefile(alias, source)
                        except OSError:
                            same_source = False
                        if not same_source:
                            raise ConanInvalidConfiguration(
                                f"shared-library alias {alias!r} does not match "
                                f"{source!r}"
                            )
                        alias_states.append((alias_name, alias, "link"))
                    elif (
                        os.path.isfile(alias)
                        and filecmp.cmp(alias, source, shallow=False)
                        and stat.S_IMODE(
                            os.stat(alias, follow_symlinks=False).st_mode
                        )
                        == source_mode
                    ):
                        alias_states.append((alias_name, alias, "regular"))
                    else:
                        raise ConanInvalidConfiguration(
                            f"shared-library alias {alias!r} does not match "
                            f"{source!r}"
                        )
                else:
                    alias_states.append((alias_name, alias, "missing"))

            if preserve_soname_inode:
                soname_name, soname_alias, soname_state = alias_states[0]
                if soname_state == "link":
                    os.unlink(soname_alias)
                    os.replace(source, soname_alias)
                elif soname_state == "missing":
                    os.replace(source, soname_alias)
                elif os.path.samefile(soname_alias, source):
                    os.unlink(source)
                else:
                    raise ConanInvalidConfiguration(
                        f"runtime SONAME alias does not preserve the versioned "
                        f"shared object's identity: {soname_alias!r}"
                    )
                soname_stat = os.stat(soname_alias, follow_symlinks=False)
                if (
                    os.path.lexists(source)
                    or not os.path.isfile(soname_alias)
                    or os.path.islink(soname_alias)
                    or (soname_stat.st_dev, soname_stat.st_ino) != source_identity
                    or stat.S_IMODE(soname_stat.st_mode) != source_mode
                ):
                    raise ConanInvalidConfiguration(
                        f"failed to preserve shared-library identity at runtime "
                        f"SONAME {soname_alias!r}"
                    )
                self.output.info(
                    f"promoted versioned shared object to regular runtime "
                    f"SONAME {soname_name}"
                )

                alias_name, alias, state = alias_states[1]
                if state == "link":
                    os.unlink(alias)
                if state != "regular":
                    shutil.copyfile(soname_alias, alias)
                    shutil.copymode(soname_alias, alias, follow_symlinks=False)
                if (
                    not os.path.isfile(alias)
                    or os.path.islink(alias)
                    or not filecmp.cmp(alias, soname_alias, shallow=False)
                    or not _alias_mode_ok(alias, source_mode)
                ):
                    raise ConanInvalidConfiguration(
                        f"failed to materialize link-time shared-library alias "
                        f"{alias!r}"
                    )
                continue

            for alias_name, alias, state in alias_states:
                if state == "regular":
                    continue
                if state == "link":
                    os.unlink(alias)
                shutil.copyfile(source, alias)
                shutil.copymode(source, alias, follow_symlinks=False)
                if (
                    not os.path.isfile(alias)
                    or os.path.islink(alias)
                    or not filecmp.cmp(alias, source, shallow=False)
                    or not _alias_mode_ok(alias, source_mode)
                ):
                    raise ConanInvalidConfiguration(
                        f"failed to materialize shared-library alias {alias!r}"
                    )
                self.output.info(
                    f"materialized regular shared-library alias {alias_name}"
                )

    def _prepare_shared_build_aliases(self):
        for subdirectory, target, stem in self._shared_library_targets:
            self._run_meson_with_build_runtime(
                [
                    "compile",
                    "-C",
                    self.build_folder,
                    "-j1",
                    f"{target}:shared_library",
                ]
            )
            self._materialize_shared_library_aliases(
                os.path.join(self.build_folder, subdirectory), [stem]
            )

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as stream:
                return stream.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _resolve_ohos_signing_tools(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = self._require_absolute_tool(
            executables.get("c"), "c", target_posix=True
        )
        compiler_dir = posixpath.dirname(compiler)
        tools = {
            "readelf": posixpath.join(compiler_dir, "llvm-readelf"),
            "objcopy": posixpath.join(compiler_dir, "llvm-objcopy"),
            "signer": posixpath.join(compiler_dir, "binary-sign-tool"),
        }
        missing = [
            name
            for name, path in tools.items()
            if not os.path.isfile(path) or not os.access(path, os.X_OK)
        ]
        if missing:
            if not can_run(self):
                self.output.info(
                    "PACKAGE_CODESIGN=NOT_RUN reason=cross_building; "
                    f"missing_tools={','.join(missing)}"
                )
                return None
            raise ConanInvalidConfiguration(
                "native OHOS package signing tools are missing: "
                + ", ".join(missing)
            )
        return tools

    @staticmethod
    def _run_signing_tool(arguments, label):
        completed = subprocess.run(
            arguments,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if completed.returncode != 0:
            raise ConanInvalidConfiguration(
                f"{label} failed with exit code {completed.returncode}"
            )
        return completed.stdout

    def _sign_final_ohos_elf(self, path, tools):
        if not os.path.isfile(path) or os.path.islink(path) or not self._is_elf(path):
            raise ConanInvalidConfiguration(
                f"required final OHOS ELF is missing, linked, or invalid: {path!r}"
            )
        original_mode = stat.S_IMODE(os.stat(path, follow_symlinks=False).st_mode)
        temporary = f"{path}.signing-{os.getpid()}"
        signed = f"{path}.signed-{os.getpid()}"
        if os.path.lexists(temporary) or os.path.lexists(signed):
            raise ConanInvalidConfiguration(
                f"OHOS ELF signing temporary already exists for {path!r}"
            )
        try:
            shutil.copy2(path, temporary)
            sections = self._run_signing_tool(
                [tools["readelf"], "-S", temporary], "pre-sign readelf"
            ).decode("utf-8", errors="strict")
            if ".codesign" in sections:
                self._run_signing_tool(
                    [tools["objcopy"], "--remove-section", ".codesign", temporary],
                    "codesign removal",
                )
            self._run_signing_tool(
                [
                    tools["signer"],
                    "sign",
                    "-inFile",
                    temporary,
                    "-outFile",
                    signed,
                    "-selfSign",
                    "1",
                ],
                "OHOS ELF signer",
            )
            if not os.path.isfile(signed) or os.path.islink(signed):
                raise ConanInvalidConfiguration(
                    f"OHOS ELF signer did not create a regular output: {path!r}"
                )
            signed_sections = self._run_signing_tool(
                [tools["readelf"], "-S", signed], "post-sign readelf"
            ).decode("utf-8", errors="strict")
            if signed_sections.count(".codesign") != 1:
                raise ConanInvalidConfiguration(
                    f"signed OHOS ELF must contain exactly one .codesign: {path!r}"
                )
            if filecmp.cmp(temporary, signed, shallow=False):
                raise ConanInvalidConfiguration(
                    f"OHOS ELF signer did not change the unsigned input: {path!r}"
                )
            os.chmod(signed, original_mode | 0o755)
            os.replace(signed, path)
        finally:
            for candidate in (temporary, signed):
                if os.path.lexists(candidate):
                    os.unlink(candidate)

    def _sign_final_ohos_package(self):
        if str(self.settings.os) != "OHOS":
            return
        tools = self._resolve_ohos_signing_tools()
        if tools is None:
            return

        library_dir = os.path.join(self.package_folder, "lib")
        link_aliases = {}
        for _subdirectory, _target, stem in self._shared_library_targets:
            pattern = re.compile(rf"^{re.escape(stem)}[.]so[.][0-9]+$")
            sonames = [
                os.path.join(library_dir, name)
                for name in os.listdir(library_dir)
                if pattern.fullmatch(name)
                and os.path.isfile(os.path.join(library_dir, name))
                and not os.path.islink(os.path.join(library_dir, name))
            ]
            if len(sonames) != 1:
                raise ConanInvalidConfiguration(
                    f"expected one final runtime SONAME for {stem!r}, "
                    f"found {len(sonames)}"
                )
            alias = os.path.join(library_dir, f"{stem}.so")
            if not os.path.isfile(alias) or os.path.islink(alias):
                raise ConanInvalidConfiguration(
                    f"final link-time alias is missing or linked: {alias!r}"
                )
            link_aliases[alias] = sonames[0]

        signed_paths = []
        for directory, subdirectories, filenames in os.walk(self.package_folder):
            subdirectories.sort()
            for filename in sorted(filenames):
                path = os.path.join(directory, filename)
                if path in link_aliases or os.path.islink(path) or not self._is_elf(path):
                    continue
                self._sign_final_ohos_elf(path, tools)
                signed_paths.append(path)

        for alias, soname in sorted(link_aliases.items()):
            if soname not in signed_paths:
                raise ConanInvalidConfiguration(
                    f"runtime SONAME was not signed: {soname!r}"
                )
            shutil.copyfile(soname, alias)
            shutil.copymode(soname, alias, follow_symlinks=False)
            if (
                not os.path.isfile(alias)
                or os.path.islink(alias)
                or not filecmp.cmp(alias, soname, shallow=False)
                or not stat.S_IMODE(
                    os.stat(alias, follow_symlinks=False).st_mode
                )
                & stat.S_IXUSR
            ):
                raise ConanInvalidConfiguration(
                    f"signed link-time alias validation failed: {alias!r}"
                )
        self.output.info(f"PACKAGE_CODESIGN=PASS signed_elfs={len(signed_paths)}")

    def build(self):
        if str(self.settings.os) == "OHOS":
            executables = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
            tools = self._resolve_llvm_tools(executables, target_os=self.settings.os)
            for name, path in tools.items():
                if not os.path.isfile(path) or not os.access(path, os.X_OK):
                    raise ConanInvalidConfiguration(
                        f"target compiler tool {name!r} is not executable: {path}"
                    )
        apply_conandata_patches(self)
        Meson(self).configure()
        if str(self.settings.os) in ("Linux", "OHOS") and self.options.shared:
            self._prepare_shared_build_aliases()
        self._run_meson_with_build_runtime(
            ["compile", "-C", self.build_folder, "-j1"]
        )

        if not can_run(self):
            self.output.info(
                "NOT_RUN GLIB_TARGET_UPSTREAM=unresolved reason=cross_building; "
                "configured Meson inventory and target execution are required"
            )
            return

        self._run_meson_with_build_runtime(
            ["compile", "-C", self.build_folder, "-j1", "tmpsample.xml"]
        )
        self._run_meson_with_build_runtime(
            [
                "test",
                "-C",
                self.build_folder,
                "--no-rebuild",
                "--setup=default",
                "--num-processes",
                "1",
                "--timeout-multiplier=16",
                "--print-errorlogs",
            ],
            environment={"TZ": "UTC0"},
        )

    def package(self):
        self._run_meson_with_build_runtime(
            [
                "install",
                "-C",
                self.build_folder,
                "--destdir",
                self.package_folder,
            ]
        )
        if str(self.settings.os) in ("Linux", "OHOS") and self.options.shared:
            self._materialize_shared_library_aliases(
                os.path.join(self.package_folder, "lib"),
                [entry[2] for entry in self._shared_library_targets],
                preserve_soname_inode=True,
            )
        rmdir(self, os.path.join(self.package_folder, "libexec", "installed-tests"))
        rmdir(self, os.path.join(self.package_folder, "share", "installed-tests"))
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        self._sign_final_ohos_package()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "glib2")
        self.cpp_info.set_property("cmake_target_name", "glib2::glib2")
        if self.options.shared and str(self.settings.os) in ("Linux", "OHOS"):
            self.runenv_info.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib")
            )

        glib = self.cpp_info.components["glib"]
        glib.libs = ["glib-2.0"]
        glib.includedirs = ["include/glib-2.0", "lib/glib-2.0/include"]
        glib.requires = ["pcre2::pcre2-8", "proxy-libintl::proxy-libintl"]
        glib.system_libs = ["m", "pthread"]
        glib.set_property("pkg_config_name", "glib-2.0")
        glib.set_property("cmake_target_name", "glib2::glib")

        gobject = self.cpp_info.components["gobject"]
        gobject.libs = ["gobject-2.0"]
        gobject.includedirs = glib.includedirs
        gobject.requires = ["glib", "libffi::libffi"]
        gobject.set_property("pkg_config_name", "gobject-2.0")
        gobject.set_property("cmake_target_name", "glib2::gobject")

        gmodule = self.cpp_info.components["gmodule"]
        gmodule.libs = ["gmodule-2.0"]
        gmodule.includedirs = glib.includedirs
        gmodule.requires = ["glib"]
        gmodule.system_libs = ["dl"]
        gmodule.set_property("pkg_config_name", "gmodule-2.0")
        gmodule.set_property("cmake_target_name", "glib2::gmodule")

        gthread = self.cpp_info.components["gthread"]
        gthread.libs = ["gthread-2.0"]
        gthread.includedirs = glib.includedirs
        gthread.requires = ["glib"]
        gthread.system_libs = ["pthread"]
        gthread.set_property("pkg_config_name", "gthread-2.0")
        gthread.set_property("cmake_target_name", "glib2::gthread")

        gio = self.cpp_info.components["gio"]
        gio.libs = ["gio-2.0"]
        gio.includedirs = glib.includedirs
        gio.requires = ["gobject", "gmodule", "glib", "zlib::zlib"]
        gio.system_libs = ["dl", "rt"]
        gio.set_property("pkg_config_name", "gio-2.0")
        gio.set_property("cmake_target_name", "glib2::gio")
        gio.set_property(
            "pkg_config_custom_content",
            {"gdbus_codegen": "${bindir}/gdbus-codegen"},
        )

        girepository = self.cpp_info.components["girepository"]
        girepository.libs = ["girepository-2.0"]
        girepository.includedirs = glib.includedirs
        girepository.requires = [
            "glib",
            "gobject",
            "gmodule",
            "gio",
            "libffi::libffi",
        ]
        girepository.set_property("pkg_config_name", "girepository-2.0")
        girepository.set_property("cmake_target_name", "glib2::girepository")

        self.cpp_info.requires = [
            "gio",
            "girepository",
            "gobject",
            "gmodule",
            "gthread",
            "glib",
        ]
