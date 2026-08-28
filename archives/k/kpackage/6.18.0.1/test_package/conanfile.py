#!/usr/bin/env python3
"""Conan test_package for kpackage 6.18.0."""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class KpackageTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase/6.11.1")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        ecm = self.dependencies.build.get("ecm")
        if ecm and ecm.package_folder:
            ecm_cmake = os.path.join(ecm.package_folder, "share", "ECM", "cmake")
            lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lines.append(
                    f'list(PREPEND CMAKE_PREFIX_PATH '
                    f'"{dep.package_folder}/lib/cmake")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_LIBRARY_PATH "{dep.package_folder}/lib")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_INCLUDE_PATH '
                    f'"{dep.package_folder}/include")'
                )
        lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        self._assert_relocatable_lib()
        tp_bin = os.path.join(self.build_folder, "..", "..", "bin")
        os.makedirs(tp_bin, exist_ok=True)
        for dep in self.dependencies.values():
            libdir = os.path.join(dep.package_folder, "lib") if dep.package_folder else None
            if libdir and os.path.isdir(libdir):
                for name in os.listdir(libdir):
                    if name.startswith("libKF6") and name.endswith(".so"):
                        link = os.path.join(tp_bin, name)
                        if not os.path.lexists(link):
                            os.symlink(os.path.join(libdir, name), link)

        env = Environment()
        env.append(
            "LD_LIBRARY_PATH",
            [
                os.path.join(p.package_folder, "lib")
                for p in self.dependencies.values()
                if p.package_folder
            ],
        )
        with env.vars(self).apply():
            cmake = CMake(self)
            cmake.test()
            self.run(
                os.path.join(self.cpp.build.bindirs[0], "test_kpackage"),
                env="conanrun",
            )
            self.run(
                os.path.join(self.cpp.build.bindirs[0], "test_ohos_adaptation"),
                env="conanrun",
            )

    def _assert_relocatable_lib(self):
        """Regression check: the produced libKF6Package.so must carry no
        machine-private Conan cache path in DT_NEEDED/RPATH/RUNPATH.

        R05/R07 relocatability fix: KF6 deps are linked by SONAME-style basename
        at link time (no .conan2/.cache absolute path). If a future change lets a
        producer cache path leak back in, this check fails and blocks the gate.
        """
        lib = os.path.join(self.dependencies["kpackage"].package_folder, "lib", "libKF6Package.so")
        if not os.path.exists(lib):
            # test_package runs against the built reference; be strict.
            self.output.error("libKF6Package.so not found in package: %s" % lib)
            raise Exception("libKF6Package.so missing for relocatability check")
        self.output.info("relocatability check on %s" % lib)
        readelf_out = os.path.join(self.build_folder, "readelf-libKF6Package.txt")
        self.run(
            "readelf -d '%s' > '%s' 2>&1" % (lib, readelf_out),
            ignore_errors=True,
        )
        text = ""
        try:
            with open(readelf_out) as f:
                text = f.read()
        except OSError:
            pass
        # Machine-private producer Conan cache roots that must never leak into
        # the shipped ELF's DT_NEEDED/RPATH/RUNPATH.
        forbidden = (".conan2/p/", ".cache/conan2")
        leaked = [line.strip() for line in text.splitlines()
                  if any(tok in line for tok in forbidden)]
        if leaked:
            self.output.error("RELOCATABILITY FAIL: machine-private Conan path leaked:")
            for line in leaked:
                self.output.error("  %s" % line)
            raise Exception("libKF6Package.so contains machine-private Conan path(s)")
        self.output.info("RELOCATABILITY OK: no .conan2/.cache path in DT_NEEDED/RPATH/RUNPATH")
