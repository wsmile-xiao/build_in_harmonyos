#!/usr/bin/env python3
"""Conan test_package for ki18n 6.26.0.1.

R34: exercises the real KF6I18n C++ API (link + call + assert).
R53: proves the QML module org.kde.ki18n ships in the package
     (``lib/qml/org/kde/ki18n/{qmldir,*.so,*.qmltypes}``), that the QML plugin
     DT_NEEDED carries no relative/absolute path, and that ``import
     org.kde.ki18n`` really loads through a fresh offscreen QQmlEngine (the
     KI18n singleton resolves, the KLocalizedContext i18n() context object
     works, and a real KLocalizedContext is instantiated).
"""
import os
import struct

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


def _elf_needed(path):
    """Return the DT_NEEDED names of an ELF64 file, or None if it is not ELF."""
    with open(path, "rb") as handle:
        data = handle.read()
    if len(data) < 64 or data[:4] != b"\x7fELF":
        return None
    if data[4] != 2:  # ELFCLASS64
        return None
    endian = "<" if data[5] == 1 else ">"
    (e_shoff,) = struct.unpack_from(endian + "Q", data, 0x28)
    e_shentsize, e_shnum, e_shstrndx = struct.unpack_from(endian + "HHH", data, 0x3A)
    if e_shoff == 0 or e_shnum == 0:
        return []

    def section(index):
        off = e_shoff + index * e_shentsize
        return struct.unpack_from(endian + "IIQQQQIIQQ", data, off)

    sections = [section(i) for i in range(e_shnum)]
    strtab_off = sections[e_shstrndx][4]

    def name_of(entry):
        start = strtab_off + entry[0]
        end = data.index(b"\x00", start)
        return data[start:end].decode("utf-8", "replace")

    dynamic = next((s for s in sections if name_of(s) == ".dynamic"), None)
    dynstr = next((s for s in sections if name_of(s) == ".dynstr"), None)
    if dynamic is None or dynstr is None:
        return []

    needed = []
    dyn_off, dyn_size = dynamic[4], dynamic[5]
    str_off = dynstr[4]
    for off in range(dyn_off, dyn_off + dyn_size, 16):
        tag, val = struct.unpack_from(endian + "qQ", data, off)
        if tag == 0:
            break
        if tag == 1:  # DT_NEEDED
            start = str_off + val
            end = data.index(b"\x00", start)
            needed.append(data[start:end].decode("utf-8", "replace"))
    return needed


def _is_bad_needed(name):
    return name.startswith("/") or name.startswith("../")


class Ki18nTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase/6.11.1")
        self.requires("qtdeclarative/6.11.1")
        # KF6::I18n links against libintl from gettext.
        self.requires("gettext/0.22.5.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

        deps = CMakeDeps(self)
        # The published gettext CMake config declares a bogus 'asprintf'
        # library on OHOS and would shadow CMake's own FindGettext module when
        # KF6I18nMacros.cmake runs find_package(Gettext). ki18n consumers only
        # need the Gettext *tools* (msgfmt), which FindGettext resolves, so
        # suppress the Conan gettext config entirely.
        deps.set_property("gettext", "cmake_find_mode", "none")
        deps.generate()

        lines = ['set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)']
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lines.append(
                    f'list(PREPEND CMAKE_PREFIX_PATH "{dep.package_folder}/lib/cmake")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_LIBRARY_PATH "{dep.package_folder}/lib")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_INCLUDE_PATH "{dep.package_folder}/include")'
                )
        lines.append(
            'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")'
        )
        lines.append(
            'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")'
        )
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _lib_dirs(self):
        return [
            os.path.join(p.package_folder, "lib")
            for p in self.dependencies.values()
            if p.package_folder
        ]

    def _qml_import_paths(self):
        paths = []
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                for rel in ("lib/qml", "share/qml", "qml"):
                    candidate = os.path.join(dep.package_folder, rel)
                    if os.path.isdir(candidate):
                        paths.append(candidate)
        return paths

    def test(self):
        pkg = self.dependencies["ki18n"].package_folder

        # ---- R53: the QML module tree must be shipped ----
        module_dir = os.path.join(pkg, "lib", "qml", "org", "kde", "ki18n")
        qmldir = os.path.join(module_dir, "qmldir")
        assert os.path.isfile(qmldir), f"missing QML module qmldir: {qmldir}"
        with open(qmldir, encoding="utf-8") as handle:
            qmldir_text = handle.read()
        assert (
            "module org.kde.ki18n" in qmldir_text
        ), f"qmldir does not declare 'module org.kde.ki18n':\n{qmldir_text}"

        entries = sorted(os.listdir(module_dir))
        plugins = [n for n in entries if n.endswith(".so")]
        qmltypes = [n for n in entries if n.endswith(".qmltypes")]
        assert plugins, f"no QML plugin .so in {module_dir}: {entries}"
        assert qmltypes, f"no .qmltypes in {module_dir}: {entries}"
        self.output.info(f"QML module dir {module_dir}: {entries}")

        # ---- R53: plugin DT_NEEDED must not contain relative/absolute paths ----
        for name in plugins:
            plugin = os.path.join(module_dir, name)
            needed = _elf_needed(plugin)
            assert needed is not None, f"{plugin} is not an ELF64 file"
            self.output.info(f"{name} DT_NEEDED={needed}")
            bad = [n for n in needed if _is_bad_needed(n)]
            assert not bad, f"{name} DT_NEEDED contains relative/absolute path(s): {bad}"

        # The core library must be a properly SONAMEd first-class library too.
        core_lib = os.path.join(pkg, "lib", "libKF6I18n.so")
        assert os.path.isfile(core_lib), f"missing core library: {core_lib}"
        core_needed = _elf_needed(core_lib)
        assert core_needed is not None, f"{core_lib} is not an ELF64 file"
        bad = [n for n in core_needed if _is_bad_needed(n)]
        assert not bad, f"libKF6I18n.so DT_NEEDED contains relative/absolute path(s): {bad}"

        # ---- run the compiled consumer (R34 C++ API + R53 QML engine) ----
        lib_dirs = self._lib_dirs()
        plugin_dirs = [
            os.path.join(p.package_folder, "plugins")
            for p in self.dependencies.values()
            if p.package_folder
        ]
        qml_paths = self._qml_import_paths()

        def joined(values, current=""):
            parts = [v for v in values if v]
            if current:
                parts.append(current)
            return os.pathsep.join(parts)

        env = Environment()
        env.define(
            "LD_LIBRARY_PATH",
            joined(lib_dirs, os.environ.get("LD_LIBRARY_PATH", "")),
        )
        env.define("QT_PLUGIN_PATH", joined(plugin_dirs))
        env.define("QML2_IMPORT_PATH", joined(qml_paths))
        env.define("QML_IMPORT_PATH", joined(qml_paths))
        env.define("QT_QPA_PLATFORM", "offscreen")
        env.define("KI18N_QML_IMPORT_PATH", joined(qml_paths))

        self.output.info("test LD_LIBRARY_PATH=%s" % joined(lib_dirs))
        self.output.info("test QML_IMPORT_PATH=%s" % joined(qml_paths))

        binary = os.path.join(self.cpp.build.bindirs[0], "test_ki18n")
        with env.vars(self).apply():
            self.run('"%s"' % binary)
