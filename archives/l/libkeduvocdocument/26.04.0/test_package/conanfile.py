#!/usr/bin/env python3
"""Conan test_package for libkeduvocdocument 26.04.0.

Verification strategy:

(a) the packaged artifacts exist (lib/libKEduVocDocument.so.5.1.0 + SONAME
    symlink chain, headers, the upstream LibKEduVocDocumentConfig.cmake);

(b) OHOS adaptation regression checks (E537 / patch 0001), read from the real
    packaged ELF bytes:
      * DT_SONAME of libKEduVocDocument.so.5.1.0 is the bare
        "libKEduVocDocument.so.5" (the OHOS CMake platform module defines no
        SONAME flag, so the recipe supplies -Wl,-soname,);
      * no packaged ELF carries an absolute Conan cache DT_NEEDED entry
        (the KF6 libraries published on ohpcd have no DT_SONAME, so without
        the IMPORTED_SONAME stamping of patch 0001 the linker would record
        machine-private paths);

(c) a real consumer program is built against the installed package and run
    (R34): it drives KEduVocDocument identifiers/lesson/entry through
    saveAs(Kvtml) and open() and compares the round trip;

(d) the runtime shim for absolute Conan-cache DT_NEEDED entries already
    present inside published KF6 binaries (kio/6.26.0 embeds
    ".../.cache/conan2/p/<hash>/p/lib/libKF6*.so") is materialized before the
    consumer program is started (akonadi 25.12.3 precedent).
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class LibkeduvocdocumentTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase/6.11.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        pkg = self.dependencies.get("libkeduvocdocument")
        if pkg and pkg.package_folder:
            # The package installs its own LibKEduVocDocumentConfig.cmake and
            # uses cmake_find_mode=none, so point CMake at it explicitly.
            lines.append(
                'list(PREPEND CMAKE_PREFIX_PATH "%s/lib/cmake")'
                % pkg.package_folder
            )
        qtbase = self.dependencies.get("qtbase")
        if qtbase and qtbase.package_folder:
            qt = qtbase.package_folder
            lines.append('list(PREPEND CMAKE_PREFIX_PATH "%s/lib/cmake")' % qt)
            lines.append('list(PREPEND CMAKE_LIBRARY_PATH "%s/lib")' % qt)
            lines.append('list(PREPEND CMAKE_INCLUDE_PATH "%s/include")' % qt)
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as handle:
            handle.write("\n".join(lines) + "\n")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    # ── helpers ──────────────────────────────────────────────────────────

    def _packaged_library(self):
        pkg = self.dependencies.get("libkeduvocdocument")
        return os.path.join(pkg.package_folder, "lib", "libKEduVocDocument.so.5.1.0")

    def _find_tool(self, name):
        candidates = []
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        for compiler in (compilers.get("c"), compilers.get("cpp")):
            if compiler:
                candidates.append(os.path.join(os.path.dirname(compiler), name))
        found = shutil.which(name)
        if found:
            candidates.append(found)
        candidates.append(os.path.join("/data/service/hnp/bin", name))
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return ""

    @staticmethod
    def _elf_entries(readelf, elf_path):
        """Return (soname, [needed...]) read from the real ELF bytes."""
        try:
            probe = subprocess.run(
                [readelf, "-d", elf_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                check=False,
            )
        except OSError:
            return "", []
        if probe.returncode != 0:
            return "", []
        soname = ""
        needed = []
        lib_marker = "Shared library: ["
        soname_marker = "Library soname: ["
        for line in probe.stdout.splitlines():
            if soname_marker in line:
                soname = line.split(soname_marker, 1)[1].split("]", 1)[0]
            elif lib_marker in line:
                needed.append(line.split(lib_marker, 1)[1].split("]", 1)[0])
        return soname, needed

    def _dependency_library_map(self):
        libraries = {}
        for dep in self.dependencies.values():
            if not dep or not dep.package_folder:
                continue
            for sub in ("lib", "bin"):
                folder = os.path.join(dep.package_folder, sub)
                if not os.path.isdir(folder):
                    continue
                for name in sorted(os.listdir(folder)):
                    path = os.path.join(folder, name)
                    if os.path.isfile(path) and ".so" in name:
                        libraries.setdefault(name, path)
        return libraries

    def _bridge_absolute_needed_paths(self, libraries):
        """E537: published KF6 binaries embed absolute Conan cache DT_NEEDED
        entries which the musl loader resolves directly (LD_LIBRARY_PATH
        cannot override them). Materialize the missing paths as compatibility
        symlinks onto this worker's packages. No-op where they exist."""
        if str(self.settings.os) not in ("OHOS", "HarmonyOS"):
            return
        readelf = self._find_tool("llvm-readelf") or self._find_tool("readelf")
        if not readelf:
            self.output.warning("readelf unavailable; absolute DT_NEEDED bridge skipped")
            return
        elf_paths = list(libraries.values())
        pkg = self.dependencies.get("libkeduvocdocument")
        if pkg and pkg.package_folder:
            for sub in ("lib", "bin"):
                folder = os.path.join(pkg.package_folder, sub)
                if os.path.isdir(folder):
                    for name in sorted(os.listdir(folder)):
                        path = os.path.join(folder, name)
                        if os.path.isfile(path):
                            elf_paths.append(path)
        created = 0
        for elf_path in elf_paths:
            _, needed_entries = self._elf_entries(readelf, elf_path)
            for needed in needed_entries:
                if not os.path.isabs(needed) or os.path.exists(needed):
                    continue
                source = libraries.get(os.path.basename(needed))
                if not source:
                    continue
                try:
                    os.makedirs(os.path.dirname(needed), exist_ok=True)
                    if os.path.lexists(needed):
                        os.unlink(needed)
                    os.symlink(source, needed)
                    created += 1
                except OSError:
                    pass
        if created:
            self.output.info(
                "E537 bridge: materialized %d absolute DT_NEEDED path(s)" % created
            )

    def _test_env(self):
        env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
                env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
                )
        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            # Prepend LAST so it ends up FIRST: the SDK libc++.so is a linker
            # script the runtime loader cannot use (kconfig/kcrash precedent).
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        env.define("QT_QPA_PLATFORM", "offscreen")
        home = os.path.join(self.build_folder, "test-home")
        tmp = os.path.join(self.build_folder, "test-tmp")
        xdg = os.path.join(self.build_folder, "xdg-runtime")
        for folder in (home, tmp, xdg):
            os.makedirs(folder, exist_ok=True)
        os.chmod(xdg, 0o700)
        env.define("HOME", home)
        env.define("TMPDIR", tmp)
        env.define("TEMP", tmp)
        env.define("TMP", tmp)
        env.define("XDG_RUNTIME_DIR", xdg)
        env.define("XDG_CACHE_HOME", os.path.join(home, ".cache"))
        env.define("XDG_CONFIG_HOME", os.path.join(home, ".config"))
        env.define("XDG_DATA_HOME", os.path.join(home, ".local", "share"))
        return env

    # ── test ─────────────────────────────────────────────────────────────

    def test(self):
        if not can_run(self):
            return

        pkg = self.dependencies.get("libkeduvocdocument")
        pkg_folder = pkg.package_folder
        library = self._packaged_library()
        config = os.path.join(
            pkg_folder, "lib", "cmake", "libkeduvocdocument",
            "LibKEduVocDocumentConfig.cmake",
        )
        header = os.path.join(
            pkg_folder, "include", "libkeduvocdocument", "keduvocdocument.h"
        )

        # (a) packaged artifacts
        if not os.path.isfile(library):
            raise ConanException("packaged library missing: %s" % library)
        if not os.path.lexists(os.path.join(pkg_folder, "lib", "libKEduVocDocument.so.5")):
            raise ConanException("SONAME symlink libKEduVocDocument.so.5 missing")
        if not os.path.isfile(config):
            raise ConanException("LibKEduVocDocumentConfig.cmake missing: %s" % config)
        if not os.path.isfile(header):
            raise ConanException("public header missing: %s" % header)
        self.output.info("packaged artifacts present (lib + config + headers)")

        # (b) OHOS adaptation regression checks
        readelf = self._find_tool("llvm-readelf") or self._find_tool("readelf")
        if not readelf:
            raise ConanException("llvm-readelf/readelf not found; cannot verify ELF")
        soname, needed = self._elf_entries(readelf, library)
        self.output.info("libKEduVocDocument.so.5.1.0 DT_SONAME = %r" % soname)
        if soname != "libKEduVocDocument.so.5":
            raise ConanException(
                "OHOS adaptation regression: DT_SONAME is %r, expected "
                "'libKEduVocDocument.so.5' (patch 0001 supplies the soname "
                "link flag because CMake has no Platform/HarmonyOS module)"
                % soname
            )
        absolute = [n for n in needed if os.path.isabs(n)]
        if absolute:
            raise ConanException(
                "OHOS adaptation regression: absolute DT_NEEDED leak in the "
                "packaged library (E537): %s" % absolute
            )
        self.output.info(
            "OHOS adaptation OK: bare DT_SONAME, %d relocatable DT_NEEDED "
            "entr%s" % (len(needed), "y" if len(needed) == 1 else "ies")
        )

        # (c) real consumer program execution
        libraries = self._dependency_library_map()
        self._bridge_absolute_needed_paths(libraries)
        binary = os.path.join(
            self.cpp.build.bindirs[0], "test_libkeduvocdocument"
        )
        if not os.path.isfile(binary):
            raise ConanException("consumer test binary not built: %s" % binary)
        with self._test_env().vars(self).apply():
            self.run('"%s"' % binary, env="conanrun")
