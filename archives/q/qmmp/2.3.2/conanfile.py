#!/usr/bin/env python3
"""Conan recipe for qmmp 2.3.2 on HarmonyOS PC (aarch64-linux-ohos).

qmmp is a Qt6 based audio player. The build produces the libqmmp/liblqmmpui
libraries, the qmmp application and the plugin set (input decoders, output,
effect, general, playlist format, command line option, file dialog, transport
and UI plugins).

Deviations from a default desktop build are limited to build-system
portability (see patches/): the upstream CMakeLists executes the Qt Linguist
lrelease tool at configure time, which cannot be executed on the OHOS
packaging profile.

Dependencies: qtbase-sql-dbus/6.11.1 (Qt Core/Gui/Widgets/Network/Sql/DBus),
qt6linguisttools/6.11.1 (Qt6::lrelease), qtmultimedia/6.11.1 (Qt Multimedia
output plugin) plus the decoder/tag libraries published on ohpcd (taglib,
enca, libmad, mpg123, flac, ogg, vorbis, opus, opusfile, wavpack, libsndfile,
wildmidi, libarchive, libcdio, libcdio-paranoia, soxr, libcurl, libsidplayfp,
libshout).
"""
import glob
import os
import shutil
import struct

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.gnu import PkgConfigDeps
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)


class QmmpConan(ConanFile):
    name = "qmmp"
    version = "2.3.2"
    description = "Qt6 based audio player with a wide range of input/output format plugins"
    license = "GPL-2.0-or-later"
    homepage = "https://qmmp.ylsoftware.com/"
    url = "https://qmmp.ylsoftware.com/"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Qt6::Sql/Qt6::DBus are optional upstream components but the plain
        # qtbase package is built with FEATURE_sql/dbus=OFF, so the published
        # qtbase-sql-dbus variant is used as the Qt provider (ktextaddons 2.0.2
        # / akonadi 25.12.3 precedent).
        self.requires("qtbase-sql-dbus/6.11.1")
        self.requires("qt6linguisttools/6.11.1")
        self.requires("qtmultimedia/6.11.1")
        # Tagging / charset detection used by most input plugins.
        self.requires("taglib/1.13.1")
        self.requires("enca/1.19")
        # Input decoders.
        self.requires("libmad/0.15.1b")
        self.requires("mpg123/1.33.5")
        self.requires("flac/1.4.3")
        self.requires("opus/1.5.2.1")
        self.requires("opusfile/0.12")
        self.requires("wavpack/5.9.0")
        self.requires("libsndfile/1.2.2")
        self.requires("wildmidi/0.5.0")
        self.requires("libarchive/3.8.7")
        self.requires("libcdio/2.3.0")
        self.requires("libcdio-paranoia/10.2-2.0.2")
        # Vorbis decoding: the standalone vorbis package provides vorbis.pc /
        # vorbisfile.pc without pulling libogg/1.3.6 (the flac and opusfile
        # binaries are built against libogg/1.3.5).
        self.requires("vorbis/1.3.7")
        # Effect / transport / output plugins.
        self.requires("soxr/0.1.3")
        self.requires("libcurl/8.5.0")
        # Single provider per shared low-level library: the published decoder
        # binaries record a mix of exact and minor-mode pins, so one version has
        # to satisfy all of them (opusfile/0.12 pins libogg/1.3.5 and
        # openssl/3.5.6 exactly, flac/libvorbis/libshout accept any 1.3.x/3.5.x,
        # libarchive/libcurl want zlib/1.3.1.1 and taglib 1.3.1).
        self.requires("libogg/1.3.5", override=True)
        self.requires("openssl/3.5.6", override=True)
        self.requires("zlib/1.3.1.1", override=True)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_CXX_STANDARD"] = "17"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        tc.variables["CMAKE_POLICY_DEFAULT_CMP0071"] = "NEW"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.variables["USE_SKINNED"] = "ON"
        tc.variables["USE_ENCA"] = "ON"
        tc.variables["USE_DIR_ASSOC"] = "OFF"

        # Qt modules published as separate packages live in their own prefixes;
        # Qt6Config.cmake resolves their components through
        # QT_ADDITIONAL_PACKAGES_PREFIX_PATH (ktextaddons 2.0.2 precedent).
        additional_qt = [
            dep.package_folder
            for dep in self.dependencies.values()
            if dep.package_folder
            and dep.ref.name.startswith("qt")
            and dep.ref.name not in ("qtbase", "qtbase-sql-dbus", "qtkeychain")
        ]
        if additional_qt:
            tc.variables["QT_ADDITIONAL_PACKAGES_PREFIX_PATH"] = ";".join(
                additional_qt
            )

        self._write_cmake_paths()
        tc.generate()

        # Several dependency packages ship pkg-config files whose prefix is
        # baked to the build machine's build folder, so generate correct ones
        # for the current package folders (the plugin probes below only look at
        # PKG_CONFIG_PATH).
        PkgConfigDeps(self).generate()
        self._write_pkg_config_shims()

    def _write_cmake_paths(self):
        """Most dependencies install pkg-config files only (the plugin probes
        use pkg_check_modules/pkg_search_module) and the Qt/KF style CMake
        configs are found through CMAKE_PREFIX_PATH; wire both up manually
        (Qt6Config.cmake reads QT_ADDITIONAL_PACKAGES_PREFIX_PATH)."""
        preferred = ["qtbase-sql-dbus", "qt6linguisttools"]
        deps = [
            dep
            for dep in list(self.dependencies.values())
            + list(self.dependencies.build.values())
            if dep is not None and dep.ref.name not in preferred
        ]
        ordered = deps + [
            self.dependencies.get(name)
            for name in preferred
            if name in self.dependencies
        ]
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        seen = set()
        for dep in ordered:
            if dep is None or not dep.package_folder:
                continue
            folder = dep.package_folder
            if folder in seen:
                continue
            seen.add(folder)
            lines.extend(
                [
                    f'list(PREPEND CMAKE_PREFIX_PATH "{folder}/lib/cmake")',
                    f'list(PREPEND CMAKE_PREFIX_PATH "{folder}")',
                    f'list(PREPEND CMAKE_LIBRARY_PATH "{folder}/lib")',
                    f'list(PREPEND CMAKE_INCLUDE_PATH "{folder}/include")',
                ]
            )
        lines.extend(
            [
                'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
                'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")',
            ]
        )
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as handle:
            handle.write("\n".join(lines) + "\n")

    def build(self):
        if self.settings.os == "OHOS":
            apply_conandata_patches(self)
        cmake = CMake(self)
        with self._build_env().vars(self).apply():
            cmake.configure()
            cmake.build()

    def _runtime_env(self):
        env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
                env.prepend_path(
                    "PATH", os.path.join(dep.package_folder, "bin")
                )
                env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
                )
                env.prepend_path(
                    "QT_PLUGIN_PATH",
                    os.path.join(dep.package_folder, "lib", "plugins"),
                )
        qtsql = self.dependencies.get("qtbase-sql-dbus")
        if qtsql and qtsql.package_folder:
            env.define(
                "QT_QPA_PLATFORM_PLUGIN_PATH",
                os.path.join(qtsql.package_folder, "plugins", "platforms"),
            )
        for rel in ("bin", "lib"):
            env.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.build_folder, rel)
            )
        return env

    def _build_env(self):
        env = self._runtime_env()
        pkg_paths = []
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                for rel in ("lib/pkgconfig", "share/pkgconfig"):
                    folder = os.path.join(dep.package_folder, rel)
                    if os.path.isdir(folder):
                        pkg_paths.append(folder)
        for folder in reversed(pkg_paths):
            env.prepend_path("PKG_CONFIG_PATH", folder)
        # Prepended last: the generated/shimmed pkg-config files must win over
        # the packages' own (possibly stale-prefix) ones.
        env.prepend_path(
            "PKG_CONFIG_PATH",
            os.path.join(self.generators_folder, "pkgconfig-shims"),
        )
        env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        if self.settings.os == "OHOS":
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
            for llvm_lib in sorted(
                glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos"
                    "/native/llvm/lib"
                )
            ):
                env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
        return env

    def _write_pkg_config_shims(self):
        """Copy the dependency pkg-config files into the generators folder with
        a corrected prefix. Several published packages ship .pc files whose
        prefix is baked to the build machine's build folder (no longer present)
        or to /usr/local, which makes the plugin probes create imported targets
        with non-existent include directories."""
        target_dir = os.path.join(self.generators_folder, "pkgconfig-shims")
        os.makedirs(target_dir, exist_ok=True)
        for dep in list(self.dependencies.values()) + list(
            self.dependencies.build.values()
        ):
            if dep is None or not dep.package_folder:
                continue
            for rel in ("lib/pkgconfig", "share/pkgconfig"):
                folder = os.path.join(dep.package_folder, rel)
                if not os.path.isdir(folder):
                    continue
                for name in sorted(os.listdir(folder)):
                    if not name.endswith(".pc"):
                        continue
                    destination = os.path.join(target_dir, name)
                    if os.path.exists(destination):
                        continue
                    with open(
                        os.path.join(folder, name),
                        encoding="utf-8",
                        errors="ignore",
                    ) as handle:
                        content = handle.read()
                    with open(destination, "w") as handle:
                        handle.write(
                            self._fix_pkg_config_prefix(
                                content, dep.package_folder
                            )
                        )

    @staticmethod
    def _fix_pkg_config_prefix(content, package_folder):
        """Rewrite the path variables of a pkg-config file so they point into
        the current package folder (published files may carry a build-machine
        prefix, an empty prefix or a bare "/include" style path)."""
        replacements = {
            "prefix": package_folder,
            "exec_prefix": package_folder,
            "libdir": os.path.join(package_folder, "lib"),
            "includedir": os.path.join(package_folder, "include"),
            "bindir": os.path.join(package_folder, "bin"),
            "datadir": os.path.join(package_folder, "share"),
            "pkgdatadir": os.path.join(package_folder, "share"),
        }
        lines = []
        for line in content.splitlines():
            name, separator, value = line.partition("=")
            name = name.strip()
            if separator and name in replacements:
                expanded = value.strip()
                for source, target in (
                    ("${exec_prefix}", package_folder),
                    ("${prefix}", package_folder),
                ):
                    expanded = expanded.replace(source, target)
                if not expanded.startswith(package_folder):
                    line = name + "=" + replacements[name]
            lines.append(line)
        return "\n".join(lines) + "\n"

    def package(self):
        cmake = CMake(self)
        with self._runtime_env().vars(self).apply():
            cmake.install()
        if self.settings.os == "OHOS":
            self._rewrite_absolute_needed(self.package_folder)

    def _rewrite_absolute_needed(self, root):
        """Rewrite absolute DT_NEEDED paths to plain file names.

        Linking against dependency libraries which carry no DT_SONAME makes the
        linker record the full path it opened (several published packages, e.g.
        libvorbisfile/libsoxr/libQt6Multimedia, have no SONAME), which pins the
        modules to a build machine path and breaks loading anywhere else. The
        string table entries are shortened in place, so the packaged modules
        resolve their dependencies through the normal soname search."""
        if not os.path.isdir(root):
            return
        rewritten = 0
        for current, _dirs, files in os.walk(root):
            for name in sorted(files):
                path = os.path.join(current, name)
                if os.path.islink(path) or not self._is_elf(path):
                    continue
                rewritten += self._rewrite_needed_in_file(path)
        if rewritten:
            self.output.info(
                "Rewrote {} absolute DT_NEEDED entr(ies) to plain names".format(
                    rewritten
                )
            )

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    @staticmethod
    def _rewrite_needed_in_file(path):
        """Shorten every slash-containing DT_NEEDED name of an ELF64 file."""
        try:
            with open(path, "rb+") as handle:
                data = bytearray(handle.read())
                if len(data) < 0x40 or data[:4] != b"\x7fELF" or data[4] != 2:
                    return 0
                section_offset, = struct.unpack_from("<Q", data, 0x28)
                entry_size, count, names_index = struct.unpack_from(
                    "<HHH", data, 0x3A
                )
                if entry_size != 64 or not count:
                    return 0
                sections = []
                for index in range(count):
                    offset = section_offset + index * entry_size
                    name, _type = struct.unpack_from("<II", data, offset)
                    data_offset, size = struct.unpack_from(
                        "<QQ", data, offset + 24
                    )
                    sections.append((name, data_offset, size))
                if names_index >= len(sections):
                    return 0
                names = sections[names_index]
                section_names = data[names[1]:names[1] + names[2]]

                def section_name(section):
                    try:
                        return section_names[
                            section[0]:section_names.index(b"\0", section[0])
                        ]
                    except (ValueError, IndexError):
                        return b""

                dynamic = next(
                    (s for s in sections if section_name(s) == b".dynamic"),
                    None,
                )
                dynstr = next(
                    (s for s in sections if section_name(s) == b".dynstr"), None
                )
                if not dynamic or not dynstr:
                    return 0
                strings_offset, strings_size = dynstr[1], dynstr[2]
                changed = 0
                for index in range(dynamic[2] // 16):
                    tag, value = struct.unpack_from(
                        "<qQ", data, dynamic[1] + index * 16
                    )
                    if tag != 1:  # DT_NEEDED
                        continue
                    start = strings_offset + value
                    end = data.find(b"\0", start)
                    if end < 0:
                        continue
                    name = bytes(data[start:end])
                    if b"/" not in name:
                        continue
                    basename = name.rsplit(b"/", 1)[1]
                    if not basename:
                        continue
                    data[start:start + len(basename)] = basename
                    for position in range(len(basename), len(name)):
                        data[start + position] = 0
                    changed += 1
                if changed:
                    handle.seek(0)
                    handle.write(data)
                return changed
        except OSError:
            return 0
