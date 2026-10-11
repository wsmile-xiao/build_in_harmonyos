#!/usr/bin/env python3
"""Conan test_package for qmmp 2.3.2 on HarmonyOS PC.

Verifies the installed package from a consumer point of view:
  - the installed libqmmp/liblqmmpui libraries and headers are found and linked,
  - test.cpp exercises real public APIs (Qmmp::strVersion / configDir /
    pluginPath / findPlugins, CueParser) — R34,
  - ohos_test.cpp is the HarmonyOS-specific test: DT_SONAME of the libraries and
    every plugin, the plugin category layout, the application binary and the
    headless Qt Widgets runtime.
"""
import glob
import os
import shutil
import struct

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class QmmpTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
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
        tc.generate()

        preferred = ["qtbase-sql-dbus"] + [self.tested_reference_str.split("/")[0]]
        deps = [
            dep
            for dep in self.dependencies.values()
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

    def _runtime_env(self):
        env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
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
        return env

    def build(self):
        env = self._runtime_env()
        if self.settings.os == "OHOS":
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
            for llvm_lib in sorted(
                glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos"
                    "/native/llvm/lib"
                )
            ):
                env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
        with env.vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    @staticmethod
    def _relative_needed_entries(path):
        """Slash-containing DT_NEEDED names of an ELF64 shared object."""
        try:
            with open(path, "rb") as handle:
                data = handle.read()
        except OSError:
            return []
        if len(data) < 0x40 or data[:4] != b"\x7fELF" or data[4] != 2:
            return []
        section_offset, = struct.unpack_from("<Q", data, 0x28)
        entry_size, count, names_index = struct.unpack_from("<HHH", data, 0x3A)
        if entry_size != 64 or not count:
            return []
        sections = []
        for index in range(count):
            offset = section_offset + index * entry_size
            name, _type = struct.unpack_from("<II", data, offset)
            data_offset, size = struct.unpack_from("<QQ", data, offset + 24)
            sections.append((name, data_offset, size))
        if names_index >= len(sections):
            return []
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
            (s for s in sections if section_name(s) == b".dynamic"), None
        )
        dynstr = next(
            (s for s in sections if section_name(s) == b".dynstr"), None
        )
        if not dynamic or not dynstr:
            return []
        strings = data[dynstr[1]:dynstr[1] + dynstr[2]]
        entries = []
        for index in range(dynamic[2] // 16):
            tag, value = struct.unpack_from(
                "<qQ", data, dynamic[1] + index * 16
            )
            if tag != 1:  # DT_NEEDED
                continue
            try:
                name = strings[value:strings.index(b"\0", value)].decode()
            except (ValueError, IndexError):
                continue
            if "/" in name:
                entries.append(name)
        return entries

    def _prepare_loader_compat_links(self):
        """Several published dependency packages record build-layout relative
        DT_NEEDED names; the musl loader resolves slash-containing DT_NEEDED
        entries against the process CWD, so the missing links are created below
        the test build directory (kcalendarcore / ktextaddons precedent)."""
        lib_sources = []
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lib_sources.extend(
                    glob.glob(
                        os.path.join(dep.package_folder, "lib", "lib*.so*")
                    )
                )
                lib_sources.extend(
                    glob.glob(
                        os.path.join(dep.package_folder, "lib", "**", "*.so"),
                        recursive=True,
                    )
                )
        by_basename = {}
        for source in lib_sources:
            if not os.path.islink(source):
                by_basename.setdefault(os.path.basename(source), source)
        relatives = set()
        for source in by_basename.values():
            relatives.update(self._relative_needed_entries(source))
        if not relatives:
            return
        base_dirs = {
            self.build_folder,
            os.path.join(self.build_folder, "bin"),
            os.path.join(self.build_folder, "lib"),
            os.path.normpath(
                os.path.join(self.build_folder, os.pardir, os.pardir)
            ),
        }
        created = 0
        for base_dir in sorted(base_dirs):
            for relative in sorted(relatives):
                source = by_basename.get(os.path.basename(relative))
                if not source:
                    continue
                target = os.path.normpath(os.path.join(base_dir, relative))
                if os.path.lexists(target):
                    continue
                try:
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    os.symlink(source, target)
                    created += 1
                except OSError:
                    continue
        if created:
            self.output.info(
                "Created {} DT_NEEDED compatibility link(s)".format(created)
            )

    def test(self):
        tested = self.dependencies.get(self.tested_reference_str.split("/")[0])
        plugin_dir = os.path.join(tested.package_folder, "lib", "qmmp-2.3")
        env = self._runtime_env()
        env.define("QT_QPA_PLATFORM", "offscreen")
        test_home = os.path.join(self.build_folder, "test-home")
        xdg_runtime = os.path.join(self.build_folder, "xdg-runtime")
        os.makedirs(test_home, exist_ok=True)
        os.makedirs(xdg_runtime, exist_ok=True)
        os.chmod(xdg_runtime, 0o700)
        env.define("HOME", test_home)
        env.define("XDG_RUNTIME_DIR", xdg_runtime)
        env.define("XDG_CACHE_HOME", os.path.join(test_home, ".cache"))
        env.define("XDG_CONFIG_HOME", os.path.join(test_home, ".config"))
        env.define("XDG_DATA_HOME", os.path.join(test_home, ".local", "share"))
        # Prefix/plugin path of the tested package, consumed by the consumer and
        # the HarmonyOS-specific tests.
        env.define("QMMP_PREFIX", tested.package_folder)
        env.define("QMMP_PLUGINS", plugin_dir)
        if self.settings.os == "OHOS":
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        self._prepare_loader_compat_links()
        with env.vars(self).apply():
            cmake = CMake(self)
            cmake.test()
            bindir = self.cpp.build.bindirs[0]
            self.run(os.path.join(bindir, "test_qmmp"), env="conanrun")
            self.run(os.path.join(bindir, "test_qmmp_ohos"), env="conanrun")
