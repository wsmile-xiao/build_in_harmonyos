#!/usr/bin/env python3
"""Conan recipe for pavucontrol-qt 2.4.0 — Qt6 PulseAudio volume control GUI.

pavucontrol-qt is the LXQt port of pavucontrol, a PulseAudio volume control
application. It provides a Qt6-based GUI for managing audio devices, streams,
and cards via the PulseAudio client API.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import PkgConfigDeps
from conan.tools.env import Environment


class PavucontrolQtConan(ConanFile):
    name = "pavucontrol-qt"
    version = "2.4.0"
    description = "Qt6-based PulseAudio volume control (LXQt port of pavucontrol)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/lxqt/pavucontrol-qt"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        self.requires("qttools/6.11.1")
        self.requires("lxqt2-build-tools/2.4.0")
        self.requires("glib/2.88.0")
        self.requires("pulseaudio/17.0.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # lxqt2-build-tools ships its own config.cmake (cmake_find_mode="none"),
        # so CMakeDeps won't generate one. Set CMAKE_PREFIX_PATH so CMake's
        # find_package(lxqt2-build-tools) can locate it.
        lxqt_bt = self.dependencies["lxqt2-build-tools"].package_folder
        qtbase = self.dependencies["qtbase"].package_folder
        qttools = self.dependencies["qttools"].package_folder
        tc.cache_variables["CMAKE_PREFIX_PATH"] = f"{lxqt_bt};{qtbase};{qttools}"
        tc.generate()

        # PkgConfigDeps generates .pc files for glib and pulseaudio components.
        # FindGLIB.cmake (from lxqt2-build-tools) uses pkg_check_modules to find
        # glib-2.0, and the CMakeLists.txt uses pkg_check_modules for libpulse.
        pgd = PkgConfigDeps(self)
        pgd.generate()

        # pulseaudio ships its own .pc files (libpulse.pc, libpulse-mainloop-glib.pc)
        # in lib/pkgconfig/. PkgConfigDeps doesn't generate wrappers for components
        # without pkg_config_name property, so add the path to PKG_CONFIG_PATH.
        # Also, meson-installed .pc files have prefix=/ (DESTDIR issue), so we
        # create wrapper .pc files with correct paths in the generators folder.
        pulseaudio_pkg = self.dependencies["pulseaudio"].package_folder
        env = Environment()
        env.prepend_path("PKG_CONFIG_PATH", os.path.join(pulseaudio_pkg, "lib", "pkgconfig"))

        # Write corrected wrapper .pc files to the generators folder
        # (already in PKG_CONFIG_PATH via PkgConfigDeps)
        gen_dir = self.generators_folder
        # glib's bundled proxy-libintl provides the g_libintl_* symbols that
        # libglib-2.0.a references. Link it by absolute path in the wrapper so
        # the symbols resolve even when an unrelated libintl (e.g. a system
        # GNU gettext installed on the build worker) is found first by the
        # linker for -lintl. Reproduced on CI: ambient -L pointing at a
        # gettext prefix made -lintl resolve to GNU libintl, which lacks the
        # g_libintl_* exports, and the final link failed with undefined
        # symbols.
        glib_pkg = self.dependencies["glib"].package_folder
        libintl_path = ""
        for cand in ("libintl.a", "libintl.so.9", "libintl.so"):
            cand_path = os.path.join(glib_pkg, "lib", cand)
            if os.path.exists(cand_path):
                libintl_path = cand_path
                break
        for pc_name, lib_name, requires in [
            ("libpulse", "pulse", ""),
            ("libpulse-mainloop-glib", "pulse-mainloop-glib", "libpulse glib-2.0"),
        ]:
            extra_libs = f" {libintl_path}" if (libintl_path and requires) else ""
            pc_content = (
                f"prefix={pulseaudio_pkg}\n"
                f"exec_prefix=${{prefix}}\n"
                f"libdir=${{prefix}}/lib\n"
                f"includedir=${{prefix}}/include\n\n"
                f"Name: {pc_name}\n"
                f"Description: PulseAudio {pc_name} (Conan wrapper)\n"
                f"Version: 17.0.1\n"
                f"Libs: -L\"${{libdir}}\" -L\"${{libdir}}/pulseaudio\" -l{lib_name} -pthread{extra_libs}\n"
                f"Cflags: -I\"${{includedir}}\" -D_REENTRANT\n"
            )
            if requires:
                pc_content += f"Requires: {requires}\n"
            pc_path = os.path.join(gen_dir, f"{pc_name}.pc")
            with open(pc_path, "w") as f:
                f.write(pc_content)

        # Hermetic build (R33): scrub ambient flag variables inherited from the
        # worker shell. CI workers may export LDFLAGS/LIBRARY_PATH pointing at
        # prebuilt prefixes (e.g. a GNU gettext whose libintl lacks the
        # g_libintl_* symbols); CMake feeds LDFLAGS into CMAKE_EXE_LINKER_FLAGS
        # ahead of the pkg-config -L dirs, so -lintl gets shadowed and the link
        # breaks. All flags come from the Conan toolchain; ambient ones are
        # noise at best and link-breakers at worst.
        for var in ("LDFLAGS", "CPPFLAGS", "LIBRARY_PATH",
                    "CPATH", "C_INCLUDE_PATH", "CPLUS_INCLUDE_PATH"):
            env.define(var, "")

        # Qt6 tools (lrelease, lupdate) from qttools need Qt6 shared libraries
        # from qtbase at runtime. Add all dependency lib dirs to LD_LIBRARY_PATH.
        for dep in self.dependencies.values():
            pkg_folder = dep.package_folder
            if not pkg_folder:
                continue
            for libdir in dep.cpp_info.libdirs:
                full_path = os.path.join(pkg_folder, libdir)
                if os.path.isdir(full_path):
                    env.prepend_path("LD_LIBRARY_PATH", full_path)

        env.vars(self).save_script("pavucontrol_qt_env")

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        # Application package: don't generate CMake config that would
        # require consumers to find all transitive dependencies.
        self.cpp_info.set_property("cmake_find_mode", "none")
