#!/usr/bin/env python3
"""Conan recipe for X.Org libXft 2.3.9."""

import os
import re
import shutil
import stat
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LibxftConan(ConanFile):
    name = "libxft"
    version = "2.3.9"
    description = "X.Org client-side FreeType font rendering library"
    license = "HPND-sell-variant"
    homepage = "https://gitlab.freedesktop.org/xorg/lib/libxft"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libxft supports Linux and OHOS, not {self.settings.os}"
            )

    def requirements(self):
        self.requires("libx11/1.8.13", transitive_headers=True)
        self.requires("libxrender/0.9.12", transitive_headers=True)
        self.requires("fontconfig/2.18.3", transitive_headers=True)
        self.requires("freetype/2.14.3", transitive_headers=True)
        self.requires("xorgproto/2025.1", transitive_headers=True)

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        patches = Path(self.recipe_folder, "patches")
        if patches.is_dir():
            copy(
                self,
                "*.patch",
                src=str(patches),
                dst=os.path.join(self.export_sources_folder, "patches"),
                keep_path=True,
            )

    def source(self):
        source = dict(self.conan_data["sources"])
        local_archive = os.getenv("LIBXFT_SOURCE_ARCHIVE")
        if local_archive:
            archive_path = Path(local_archive).resolve()
            if not archive_path.is_file():
                raise ConanException(
                    f"LIBXFT_SOURCE_ARCHIVE is not a regular file: {archive_path}"
                )
            source["url"] = archive_path.as_uri()
            source["filename"] = archive_path.name
        get(self, **source, strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        dependencies = PkgConfigDeps(self)
        dependencies.set_property("freetype", "pkg_config_name", "freetype2")
        dependencies.set_property("xorgproto", "pkg_config_name", "xproto")
        dependencies.generate()

        toolchain = MesonToolchain(self)
        if str(self.settings.os) == "OHOS":
            compiler_executables = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            )
            compiler = compiler_executables.get("c")
            if not compiler:
                raise ConanInvalidConfiguration(
                    "OHOS Meson builds require an explicit C compiler"
                )
            compiler_path = Path(compiler)
            if not compiler_path.is_absolute():
                raise ConanInvalidConfiguration(
                    "the OHOS C compiler path must be absolute"
                )
            try:
                compiler_path = compiler_path.resolve(strict=True)
            except OSError as error:
                raise ConanInvalidConfiguration(
                    f"cannot resolve the OHOS C compiler: {compiler_path}"
                ) from error
            archiver = compiler_path.with_name("llvm-ar")
            if not archiver.is_file():
                raise ConanInvalidConfiguration(
                    f"the OHOS LLVM archiver is missing: {archiver}"
                )
            toolchain.binaries["ar"] = str(archiver)
        toolchain.project_options["lib_man_suffix"] = "3"
        toolchain.generate()

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()
        meson.test()

    def package(self):
        Meson(self).install()
        if str(self.settings.os) == "OHOS" and self.options.shared:
            self._materialize_shared_aliases()
        self._relocate_pkgconfig()
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

    def _relocate_pkgconfig(self):
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
        pc_path.write_text(content, encoding="utf-8", newline="\n")

    def _materialize_shared_aliases(self):
        library_dir = Path(self.package_folder, "lib")
        source = library_dir / "libXft.so.2.3.9"
        aliases = (library_dir / "libXft.so.2", library_dir / "libXft.so")
        if source.is_symlink() or not source.is_file():
            raise ConanException(f"installed libXft source is invalid: {source}")

        for alias in aliases:
            if alias.is_symlink():
                if not os.path.samefile(alias, source):
                    raise ConanException(
                        f"installed libXft alias has the wrong target: {alias}"
                    )
            elif not alias.is_file() or not self._same_bytes(alias, source):
                raise ConanException(
                    f"installed libXft alias has unexpected contents: {alias}"
                )

        source_mode = stat.S_IMODE(source.stat().st_mode)
        for alias in aliases:
            if alias.is_symlink():
                alias.unlink()
                shutil.copy2(source, alias)
            alias_mode = stat.S_IMODE(alias.stat().st_mode)
            if (
                alias.is_symlink()
                or not alias.is_file()
                or not self._same_bytes(alias, source)
                or not self._materialized_mode_compatible(
                    source_mode, alias_mode
                )
            ):
                raise ConanException(
                    f"libXft regular alias materialization failed: {alias}"
                )

    @staticmethod
    def _materialized_mode_compatible(source_mode, materialized_mode):
        # HMDFS can force group-write on a newly copied regular alias. Preserve
        # the executable/read baseline while rejecting unsafe permission gain.
        baseline = (
            stat.S_IRWXU
            | stat.S_IRGRP
            | stat.S_IXGRP
            | stat.S_IROTH
            | stat.S_IXOTH
        )
        unsafe = stat.S_IWOTH | stat.S_ISUID | stat.S_ISGID | stat.S_ISVTX
        return (
            materialized_mode & baseline == source_mode & baseline
            and not materialized_mode & unsafe
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
