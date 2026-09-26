#!/usr/bin/env python3
"""Conan recipe — pcb2gcode 3.0.4 (HarmonyOS PC).

pcb2gcode is a pure command line tool: it converts PCB CAD output (Gerber
RS-274X + Excellon drill) into machine G-code.  It has no GUI of its own, the
only graphical dependency is indirect, via ``libgerbv`` (Gerber parsing,
pkg-config module ``libgerbv >= 2.1.0``).  gerbv is a GTK-2.0 application and
is neither published in the ohpcd remote nor buildable there (no GTK-2.0 and
no gdkmm-2.4 in the remote), so the gerbv source is vendored (pinned upstream
to v2.13.0) and built in a GUI-free, parsing-only configuration: the GTK GUI
application, the GDK rendering backend and the GTK imaging exporters are not
compiled, and libgerbv is linked statically into the pcb2gcode executable.

The upstream test suite is built and executed (BUILD_TESTING=ON):

* Boost.Test runs in header-only mode (patches/pcb2gcode-0002), because the
  ohpcd ``boost/1.84.0`` package ships ProgramOptions but not the compiled
  Boost.Test library;
* the ``gerberimporter`` imaging test needs the GTK/GNOME imaging stack
  (glibmm / gdkmm / librsvg), which HarmonyOS does not provide, so it is
  registered only when that stack is available (patches/pcb2gcode-0001);
* the Python integration script tests stay gated by upstream on Boost 1.83.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get, rmdir, save)
from conan.tools.gnu import PkgConfigDeps

required_conan_version = ">=2.0"


class Pcb2gcodeConan(ConanFile):
    name = "pcb2gcode"
    version = "3.0.4"
    description = ("Isolation routing and drilling G-code generator for PCBs "
                   "(Gerber/Excellon to G-code, command line tool)")
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/pcb2gcode/pcb2gcode"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("pcb", "gerber", "rs274x", "excellon", "gcode", "cnc")

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    options = {"with_geos": [True, False]}
    default_options = {"with_geos": True}

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "pcb2gcode does not support os={}".format(self.settings.os))

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Boost.ProgramOptions (compiled) + the full Boost headers
        # (Boost.Geometry is header-only and used extensively by pcb2gcode).
        self.requires("boost/1.84.0")
        if self.options.with_geos:
            self.requires("geos/3.14.1")
        # Dependencies of the vendored gerbv parsing library.
        self.requires("glib/2.84.0.2")
        self.requires("cairo/1.18.4")
        # zlib is required by boost/1.84.0 (exact 1.3.1), cairo and glib
        # (both 1.3.1.1).  zlib is ABI compatible across 1.3.x, so force the
        # newest of those to resolve the transitive conflict.
        self.requires("zlib/1.3.1.1", override=True)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"]["pcb2gcode"], strip_root=True)
        get(self, **self.conan_data["sources"]["gerbv"], strip_root=True,
            destination=os.path.join(self.source_folder, "gerbv"))
        apply_conandata_patches(self)

    # ---------------------------------------------------------------- gerbv --
    @property
    def _gerbv_prefix(self):
        # The conan toolchain forces CMAKE_INSTALL_PREFIX to the package folder,
        # which is exactly what we want: libgerbv is installed there and picked
        # up by pcb2gcode via pkg-config during the build.  The runtime part of
        # the package (the executable) is installed on top, and the gerbv
        # build-only artefacts are removed in package().
        return self.package_folder

    @property
    def _gerbv_pc_dir(self):
        return os.path.join(self._gerbv_prefix, "lib", "pkgconfig")

    def _build_gerbv(self):
        src = os.path.join(self.source_folder, "gerbv")
        bld = os.path.join(self.build_folder, "gerbv-build")
        toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        self.run(
            'cmake -G Ninja -S "{}" -B "{}" '
            '-DCMAKE_TOOLCHAIN_FILE="{}" '
            '-DCMAKE_BUILD_TYPE=Release '
            '-DGERBV_WITH_GUI=OFF '
            '-DGERBV_BUILD_SHARED=OFF '
            '-DCMAKE_POSITION_INDEPENDENT_CODE=ON'.format(src, bld, toolchain),
            env="conanbuild")
        self.run('cmake --build "{}" --target install'.format(bld),
                 env="conanbuild")

    # ------------------------------------------------------------- pcb2gcode --
    def generate(self):
        # boost/geos are consumed through CMake's find_package(... CONFIG),
        # glib/cairo through pkg-config (as the vendored gerbv does).
        CMakeDeps(self).generate()
        PkgConfigDeps(self).generate()
        tc = CMakeToolchain(self)
        if self.settings.os in ("Linux", "OHOS"):
            # CMake has no Platform/HarmonyOS; pose as Linux (E092).
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # Upstream defaults to -Werror; relax it for the OHOS clang 15 toolchain.
        tc.cache_variables["PCB2GCODE_COMPILE_WARNING_AS_ERROR"] = "OFF"
        tc.cache_variables["PCB2GCODE_USE_CCACHE"] = "OFF"
        tc.cache_variables["PCB2GCODE_WITH_GEOS"] = (
            "ON" if self.options.with_geos else "OFF")
        # Build and run the upstream test suite.
        tc.cache_variables["BUILD_TESTING"] = "ON"
        # gerbv: GTK-free, parsing-only, static library.
        tc.cache_variables["GERBV_WITH_GUI"] = "OFF"
        tc.cache_variables["GERBV_BUILD_SHARED"] = "OFF"
        tc.generate()

        env = Environment()
        env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        env.prepend_path("PKG_CONFIG_PATH", self._gerbv_pc_dir)
        env.vars(self).save_script("conan_pcb2gcode_pkg_config")

    def _geos_config(self):
        # pcb2gcode probes GEOS through the geos-config helper program.  The
        # geos-config shipped in the conan geos package hardcodes its build time
        # prefix (e.g. /usr/local) and is not relocatable, so point pcb2gcode at
        # a tiny wrapper that reports the actual conan package paths.
        dep = self.dependencies["geos"]
        wrapper = os.path.join(self.build_folder, "geos-config")
        script = (
            "#!/bin/sh\n"
            'prefix="{prefix}"\n'
            'includedir="$prefix/include"\n'
            'libdir="$prefix/lib"\n'
            'case "$1" in\n'
            '  --version) echo "{version}" ;;\n'
            '  --prefix) echo "$prefix" ;;\n'
            '  --cflags|--includes) echo "-I$includedir" ;;\n'
            '  --ldflags) echo "-L$libdir" ;;\n'
            '  --libs) echo "-L$libdir -lgeos" ;;\n'
            '  --clibs) echo "-L$libdir -lgeos_c" ;;\n'
            '  *) echo "" ;;\n'
            "esac\n"
        ).format(prefix=dep.package_folder, version=str(dep.ref.version))
        save(self, wrapper, script)
        os.chmod(wrapper, 0o755)
        return wrapper

    def build(self):
        self._build_gerbv()
        cmake = CMake(self)
        variables = {}
        if self.options.with_geos:
            geos_config = self._geos_config()
            if geos_config:
                variables["PCB2GCODE_GEOS_CONFIG"] = geos_config
        cmake.configure(variables=variables)
        cmake.build()
        # Execute the upstream unit test suite (ctest is invoked directly so
        # that the ctest-specific arguments can be passed).
        self.run("ctest --output-on-failure --no-tests=error",
                 cwd=self.build_folder, env="conanrun")

    def _sign_elf(self, path):
        # HarmonyOS PC requires code signing for executables (and dlopen'd .so),
        # otherwise running them fails with "Operation not permitted" (126).
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        self.run('{} --remove-section .codesign "{}" 2>/dev/null || true'.format(
            objcopy, path))
        self.run('{} sign -inFile "{}" -outFile "{}" -selfSign 1'.format(
            signer, path, path))

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # libgerbv was linked statically into the executable, so drop its
        # build-only artefacts (static library, public header, pkg-config file).
        rmdir(self, os.path.join(self.package_folder, "lib"))
        rmdir(self, os.path.join(self.package_folder, "include"))
        licenses = os.path.join(self.package_folder, "licenses")
        copy(self, "COPYING", src=self.source_folder, dst=licenses)
        # The vendored gerbv tree is GPL-2.0-or-later.
        copy(self, "COPYING", src=os.path.join(self.source_folder, "gerbv"),
             dst=os.path.join(licenses, "gerbv"), keep_path=False)
        if self.settings.os == "OHOS":
            bindir = os.path.join(self.package_folder, "bin")
            for name in sorted(os.listdir(bindir)):
                path = os.path.join(bindir, name)
                if os.path.isfile(path) and not os.path.islink(path):
                    self._sign_elf(path)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
