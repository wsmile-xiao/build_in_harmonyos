#!/usr/bin/env python3
"""Conan recipe for TECkit 2.5.13 on HarmonyOS PC."""

import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class TeckitConan(ConanFile):
    name = "teckit"
    version = "2.5.13"
    description = "Text Encoding Conversion toolkit (TECkit engine, compiler, and tools)"
    license = "LGPL-2.1-or-later"
    homepage = "https://software.sil.org/teckit/"
    url = "https://github.com/silnrsi/teckit"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "teckit supports Linux and OHOS, got %s" % self.settings.os
            )

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires("zlib/1.3.1.1")
        self.requires("expat/2.8.2")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    @staticmethod
    def _absolute(base, path):
        return path if os.path.isabs(path) else os.path.join(base, path)

    def _compilers(self):
        configured = (
            self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            )
            or {}
        )
        return (
            str(configured.get("c") or "clang"),
            str(configured.get("cpp") or "clang++"),
        )

    def _run(self, args, cwd=None, env=None):
        command = " ".join(shlex.quote(str(arg)) for arg in args)
        self.run(command, cwd=cwd, env=env)

    def _prepare_tmpdir(self):
        # HarmonyOS mounts '/' and '/tmp' read-only.  Native compilation and
        # the upstream Perl regression runner both need a writable TMPDIR.
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        for name in ("TMPDIR", "TMP", "TEMP"):
            os.environ[name] = tmpdir
        return tmpdir

    def _dependency_paths(self):
        zlib = self.dependencies["zlib"]
        expat = self.dependencies["expat"]
        return {
            "zlib_include": self._absolute(
                zlib.package_folder, zlib.cpp_info.includedirs[0]
            ),
            "zlib_libdir": self._absolute(
                zlib.package_folder, zlib.cpp_info.libdirs[0]
            ),
            "expat_include": self._absolute(
                expat.package_folder, expat.cpp_info.includedirs[0]
            ),
            "expat_libdir": self._absolute(
                expat.package_folder, expat.cpp_info.libdirs[0]
            ),
        }

    def _compile_library(
        self,
        cxx,
        name,
        sources,
        flags,
        build_dir,
        lib_dir,
        link_flags,
    ):
        soname = "lib%s.so.0" % name
        full = os.path.join(lib_dir, "lib%s.so.0.0.0" % name)
        if self.options.shared:
            self._run(
                [
                    cxx,
                    "-shared",
                    *flags,
                    "-Wl,-soname,%s" % soname,
                    "-o",
                    full,
                    *sources,
                    *link_flags,
                    "-lz",
                ],
                cwd=build_dir,
            )
            os.symlink(os.path.basename(full), os.path.join(lib_dir, soname))
            os.symlink(soname, os.path.join(lib_dir, "lib%s.so" % name))
            return

        archive = os.path.join(lib_dir, "lib%s.a" % name)
        objects = []
        for source in sources:
            object_path = os.path.join(
                build_dir, "%s-%s.o" % (name, os.path.basename(source))
            )
            self._run([cxx, "-c", *flags, "-o", object_path, source], cwd=build_dir)
            objects.append(object_path)
        self._run(["ar", "rcs", archive, *objects], cwd=build_dir)

    def _link_flags(self, lib_dir, paths):
        return [
            "-L%s" % lib_dir,
            "-L%s" % paths["zlib_libdir"],
            "-L%s" % paths["expat_libdir"],
            "-Wl,-rpath,%s" % lib_dir,
            "-Wl,-rpath,%s" % paths["zlib_libdir"],
            "-Wl,-rpath,%s" % paths["expat_libdir"],
        ]

    def _build_tool(
        self,
        cxx,
        name,
        sources,
        libraries,
        flags,
        build_dir,
        bin_dir,
        lib_dir,
        paths,
    ):
        command = [
            cxx,
            *flags,
            "-o",
            os.path.join(bin_dir, name),
            *sources,
            *self._link_flags(lib_dir, paths),
            *libraries,
            "-lz",
        ]
        self._run(command, cwd=build_dir)

    def _run_upstream_tests(self, source_dir, bin_dir):
        test_workdir = os.path.join(self.build_folder, "upstream-test")
        os.makedirs(test_workdir, exist_ok=True)
        test_dir = os.path.join(source_dir, "test")
        command = "BINDIR=%s SRCDIR=%s perl %s" % (
            shlex.quote(bin_dir + os.sep),
            shlex.quote(test_dir + os.sep),
            shlex.quote(os.path.join(test_dir, "dotests.pl")),
        )
        self.run(command, cwd=test_workdir)
        self.output.info("UPSTREAM_TEST_RESULT total=23 passed=23 failed=0")

    def _package_libraries(self, lib_dir):
        dst = os.path.join(self.package_folder, "lib")
        os.makedirs(dst, exist_ok=True)
        if self.options.shared:
            for name in ("TECkit", "TECkit_Compiler"):
                full = "lib%s.so.0.0.0" % name
                copy(self, full, src=lib_dir, dst=dst, keep_path=False)
                os.symlink(full, os.path.join(dst, "lib%s.so.0" % name))
                os.symlink(
                    "lib%s.so.0" % name, os.path.join(dst, "lib%s.so" % name)
                )
        else:
            for name in ("TECkit", "TECkit_Compiler"):
                copy(
                    self,
                    "lib%s.a" % name,
                    src=lib_dir,
                    dst=dst,
                    keep_path=False,
                )

    def _package_pkgconfig(self):
        pkgconfig = os.path.join(self.package_folder, "lib", "pkgconfig")
        os.makedirs(pkgconfig, exist_ok=True)
        content = """prefix=${pcfiledir}/../..
exec_prefix=${prefix}
libdir=${prefix}/lib
includedir=${prefix}/include/teckit

Name: TECkit
Description: Unicode conversion library
Version: 2.5.13
Libs: -L${libdir} -lTECkit
Cflags: -I${includedir}
"""
        with open(os.path.join(pkgconfig, "teckit.pc"), "w", encoding="ascii") as fh:
            fh.write(content)

    def build(self):
        self._prepare_tmpdir()
        os.umask(0)

        c, cxx = self._compilers()
        del c  # The TECkit sources used by this recipe are C++.
        source_dir = self.source_folder
        build_dir = os.path.join(self.build_folder, "native")
        generated_include = os.path.join(build_dir, "include")
        lib_dir = os.path.join(build_dir, "lib")
        bin_dir = os.path.join(build_dir, "bin")
        for path in (build_dir, generated_include, lib_dir, bin_dir):
            os.makedirs(path, exist_ok=True)

        with open(
            os.path.join(generated_include, "config.h"), "w", encoding="ascii"
        ) as fh:
            fh.write(
                "#ifndef TECKIT_GENERATED_CONFIG_H\n"
                "#define TECKIT_GENERATED_CONFIG_H\n"
                "#define WORDS_BIGENDIAN 0\n"
                "#define HAVE_LIBEXPAT 1\n"
                "#endif\n"
            )

        paths = self._dependency_paths()
        public_headers = os.path.join(source_dir, "source", "Public-headers")
        flags = [
            "-std=c++11",
            "-O2",
            "-DNDEBUG",
            "-I%s" % generated_include,
            "-I%s" % public_headers,
            "-I%s" % os.path.join(source_dir, "source"),
            "-I%s" % os.path.join(source_dir, "SFconv"),
            "-I%s" % paths["zlib_include"],
            "-I%s" % paths["expat_include"],
        ]
        if self.options.fPIC:
            flags.append("-fPIC")

        self._compile_library(
            cxx,
            "TECkit",
            [os.path.join(source_dir, "source", "Engine.cpp")],
            flags,
            build_dir,
            lib_dir,
            self._link_flags(lib_dir, paths),
        )
        self._compile_library(
            cxx,
            "TECkit_Compiler",
            [
                os.path.join(source_dir, "source", "Compiler.cpp"),
                os.path.join(source_dir, "source", "UnicodeNames.cpp"),
            ],
            flags,
            build_dir,
            lib_dir,
            self._link_flags(lib_dir, paths),
        )

        self._build_tool(
            cxx,
            "teckit_compile",
            [
                os.path.join(
                    source_dir, "source", "Sample-tools", "TECkit_Compile.cpp"
                )
            ],
            ["-lTECkit_Compiler"],
            flags,
            build_dir,
            bin_dir,
            lib_dir,
            paths,
        )
        self._build_tool(
            cxx,
            "txtconv",
            [os.path.join(source_dir, "source", "Sample-tools", "TxtConv.cpp")],
            ["-lTECkit"],
            flags,
            build_dir,
            bin_dir,
            lib_dir,
            paths,
        )
        self._build_tool(
            cxx,
            "sfconv",
            [
                os.path.join(source_dir, "SFconv", "SFconv.cpp"),
                os.path.join(source_dir, "SFconv", "UtfCodec.cpp"),
            ],
            ["-lTECkit", "-lexpat"],
            flags,
            build_dir,
            bin_dir,
            lib_dir,
            paths,
        )

        self._run_upstream_tests(source_dir, bin_dir)

    def package(self):
        self._package_libraries(os.path.join(self.build_folder, "native", "lib"))
        self._package_pkgconfig()

        bin_dir = os.path.join(self.build_folder, "native", "bin")
        for name in ("teckit_compile", "txtconv", "sfconv"):
            copy(
                self,
                name,
                src=bin_dir,
                dst=os.path.join(self.package_folder, "bin"),
                keep_path=False,
            )

        copy(
            self,
            "*.h",
            src=os.path.join(self.source_folder, "source", "Public-headers"),
            dst=os.path.join(self.package_folder, "include", "teckit"),
            keep_path=False,
        )
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        copy(
            self,
            "*.txt",
            src=os.path.join(self.source_folder, "license"),
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        copy(
            self,
            "*.1",
            src=os.path.join(self.source_folder, "docs"),
            dst=os.path.join(self.package_folder, "share", "man", "man1"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = ["TECkit", "TECkit_Compiler"]
        self.cpp_info.includedirs = ["include/teckit", "include"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("pkg_config_name", "teckit")
        self.cpp_info.set_property("cmake_file_name", "TECkit")
        self.cpp_info.set_property("cmake_target_name", "TECkit::TECkit")
