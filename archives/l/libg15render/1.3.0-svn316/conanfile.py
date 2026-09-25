#!/usr/bin/env python3
"""Conan recipe for libg15render 1.3.0-svn316 (direct Clang build)."""

import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    save,
)
from conan.tools.layout import basic_layout


class Libg15renderConan(ConanFile):
    name = "libg15render"
    version = "1.3.0-svn316"
    package_type = "library"
    description = "Rendering library for Logitech G15 monochrome LCD displays"
    license = "GPL-2.0-or-later"
    homepage = "https://sourceforge.net/projects/g15tools/"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("libg15render supports Linux and OHOS")
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("libg15render supports OHOS armv8 only")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires(
            "freetype/2.14.3",
            transitive_headers=True,
            transitive_libs=True,
        )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        os.makedirs(self.build_folder, exist_ok=True)
        save(
            self,
            os.path.join(self.build_folder, "config.h"),
            "#define TTF_SUPPORT 1\n"
            '#define G15FONT_DIR "/usr/share/g15tools/fonts"\n'
            '#define PACKAGE "libg15render"\n'
            '#define PACKAGE_VERSION "1.3.0-svn316"\n',
        )

    def _run_command(self, arguments):
        self.run(" ".join(shlex.quote(str(argument)) for argument in arguments))

    def _compiler(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return compilers.get("c", "clang") if compilers else "clang"

    def _tool(self, name):
        compiler_dir = os.path.dirname(self._compiler())
        adjacent = os.path.join(compiler_dir, name)
        return adjacent if os.path.isfile(adjacent) else (shutil.which(name) or name)

    def _freetype_paths(self):
        dependency = self.dependencies["freetype"]
        includes = []
        for include_dir in dependency.cpp_info.includedirs:
            includes.append(
                include_dir
                if os.path.isabs(include_dir)
                else os.path.join(dependency.package_folder, include_dir)
            )
        libdirs = []
        for lib_dir in dependency.cpp_info.libdirs:
            libdirs.append(
                lib_dir
                if os.path.isabs(lib_dir)
                else os.path.join(dependency.package_folder, lib_dir)
            )
        return includes, libdirs

    def build(self):
        apply_conandata_patches(self)
        cc = self._compiler()
        source_dir = os.path.join(self.source_folder, "src")
        object_dir = os.path.join(self.build_folder, "obj")
        library_dir = os.path.join(self.build_folder, "lib")
        binary_dir = os.path.join(self.build_folder, "bin")
        os.makedirs(object_dir, exist_ok=True)
        os.makedirs(library_dir, exist_ok=True)
        os.makedirs(binary_dir, exist_ok=True)

        freetype_includes, freetype_libdirs = self._freetype_paths()
        flags = [
            "-std=gnu11",
            "-Wall",
            "-Wextra",
            "-fPIC",
            "-DTTF_SUPPORT=1",
            '-DG15FONT_DIR="/usr/share/g15tools/fonts"',
            "-I" + source_dir,
            "-I" + self.build_folder,
        ]
        flags.extend("-I" + path for path in freetype_includes)
        if str(self.settings.build_type) == "Debug":
            flags.extend(["-O0", "-g"])
        else:
            flags.extend(["-O2", "-DNDEBUG"])

        objects = []
        for source_name in ("text.c", "pixel.c", "screen.c"):
            object_path = os.path.join(object_dir, source_name + ".o")
            self._run_command(
                [cc, *flags, "-c", os.path.join(source_dir, source_name), "-o", object_path]
            )
            objects.append(object_path)

        if self.options.shared:
            library = os.path.join(library_dir, "libg15render.so.1.1.0")
            self._run_command(
                [
                    cc,
                    "-shared",
                    "-Wl,-soname,libg15render.so.1",
                    *objects,
                    *["-L" + path for path in freetype_libdirs],
                    "-lfreetype",
                    "-lm",
                    "-o",
                    library,
                ]
            )
        else:
            library = os.path.join(library_dir, "libg15render.a")
            self._run_command([self._tool("llvm-ar"), "rcs", library, *objects])
            self._run_command([self._tool("llvm-ranlib"), library])

        converter_object = os.path.join(object_dir, "g15fontconvert.c.o")
        self._run_command(
            [
                cc,
                *flags,
                "-c",
                os.path.join(source_dir, "g15fontconvert.c"),
                "-o",
                converter_object,
            ]
        )
        converter = os.path.join(binary_dir, "g15fontconvert")
        link_arguments = [cc, converter_object, library]
        link_arguments.extend("-L" + path for path in freetype_libdirs)
        link_arguments.extend(["-lfreetype", "-lm"])
        if self.options.shared:
            link_arguments.append("-Wl,-rpath,$ORIGIN/../lib")
        link_arguments.extend(["-Wl,-z,relro,-z,now", "-pie", "-o", converter])
        self._run_command(link_arguments)

        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT(status=no_tests, discovered=0, "
            "executed=0, passed=0, failed=0)"
        )

    @staticmethod
    def _link_or_copy(source, destination):
        if os.path.lexists(destination):
            os.unlink(destination)
        try:
            os.symlink(os.path.basename(source), destination)
        except OSError:
            shutil.copy2(source, destination)

    def package(self):
        copy(
            self,
            "libg15render.h",
            src=os.path.join(self.source_folder, "src"),
            dst=os.path.join(self.package_folder, "include"),
        )
        library_dir = os.path.join(self.build_folder, "lib")
        package_libdir = os.path.join(self.package_folder, "lib")
        if self.options.shared:
            copy(self, "libg15render.so.1.1.0", src=library_dir, dst=package_libdir)
            real_library = os.path.join(package_libdir, "libg15render.so.1.1.0")
            self._link_or_copy(real_library, os.path.join(package_libdir, "libg15render.so.1"))
            self._link_or_copy(real_library, os.path.join(package_libdir, "libg15render.so"))
        else:
            copy(self, "libg15render.a", src=library_dir, dst=package_libdir)

        copy(
            self,
            "g15fontconvert",
            src=os.path.join(self.build_folder, "bin"),
            dst=os.path.join(self.package_folder, "bin"),
        )
        copy(
            self,
            "*.fnt",
            src=os.path.join(self.source_folder, "fonts"),
            dst=os.path.join(self.package_folder, "share", "g15tools", "fonts", "G15"),
        )
        copy(
            self,
            "libg15render.3",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "man", "man3"),
        )
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        pkgconfig = os.path.join(package_libdir, "pkgconfig", "libg15render.pc")
        save(
            self,
            pkgconfig,
            "prefix=${pcfiledir}/../..\n"
            "exec_prefix=${prefix}\n"
            "libdir=${prefix}/lib\n"
            "includedir=${prefix}/include\n\n"
            "Name: libg15render\n"
            "Description: Logitech G15 LCD rendering library\n"
            "Version: 1.3.0-svn316\n"
            "Requires: freetype2\n"
            "Libs: -L${libdir} -lg15render -lm\n"
            "Cflags: -I${includedir} -DTTF_SUPPORT=1\n",
        )

    def package_info(self):
        self.cpp_info.libs = ["g15render"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.defines = ["TTF_SUPPORT=1"]
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.requires = ["freetype::freetype"]
        self.cpp_info.set_property("cmake_file_name", "libg15render")
        self.cpp_info.set_property(
            "cmake_target_name", "libg15render::libg15render"
        )
        self.cpp_info.set_property("pkg_config_name", "libg15render")
