#!/usr/bin/env python3
"""Conan recipe for libSNL 0.2.1.svn.18 - Simple Nurbs Library.

libSNL is a small C++ NURBS library (curves, surfaces, control point nets,
knot vectors, transformations, triangle meshes, linear solving).

OHOS notes
----------
* Upstream ships a plain hand written ``src/makefile`` (C++98 era, no
  configure/CMake).  The recipe compiles the same source list directly with the
  OHOS clang++ so no make variables or autotools bootstrap are involved.
* Upstream's own test program ``src/snlTest.cpp`` is compiled and executed on
  the device; it prints ``All tests have passed :-)`` when every internal check
  succeeds, which the recipe requires as upstream evidence.
* Nothing is patched: the library has no dependencies beyond libstdc++/libc++.
"""
import glob
import os
import shlex
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"

# snlTest.cpp carries main(); it is the upstream test program, not part of the
# library.  Everything else under src/ is compiled into libSNL.
_LIB_SOURCE_EXCLUDES = ("snlTest.cpp",)


class LibsnlConan(ConanFile):
    name = "libsnl"
    version = "0.2.1.svn.18"
    description = ("Simple Nurbs Library: NURBS curves and surfaces, control "
                   "point nets, knot vectors and transformations in C++")
    license = "GPL-2.0-or-later"
    homepage = "http://libsnl.sourceforge.net/"
    url = ""

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libsnl OHOS adaptation is validated on Linux/OHOS, not "
                + str(self.settings.os))

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler(self, name, fallback):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        return executables.get(name) or fallback

    def _sources(self):
        sources = []
        for path in sorted(glob.glob(os.path.join(self.source_folder, "src", "*.cpp"))):
            if os.path.basename(path) in _LIB_SOURCE_EXCLUDES:
                continue
            sources.append(path)
        if not sources:
            raise ConanException("libSNL sources are missing")
        return sources

    def _std_flag(self):
        """The 2004 sources build as C++98; keep that when it is accepted."""
        return "-std=gnu++98"

    def build(self):
        apply_conandata_patches(self)
        compiler = self._compiler("cpp", "clang++")
        flags = [self._std_flag(), "-O2", "-Wall", "-fPIC"]
        objects = []
        object_dir = os.path.join(self.build_folder, "obj")
        os.makedirs(object_dir, exist_ok=True)
        for source in self._sources():
            obj = os.path.join(object_dir, os.path.basename(source)[:-4] + ".o")
            self.run("{} {} -c -o {} {}".format(
                shlex.quote(compiler), " ".join(flags), shlex.quote(obj),
                shlex.quote(source)))
            objects.append(obj)
        lib_dir = os.path.join(self.build_folder, "lib")
        os.makedirs(lib_dir, exist_ok=True)
        if self.options.shared:
            target = os.path.join(lib_dir, "libSNL.so.0.2")
            self.run("{} {} -shared -o {} {}".format(
                shlex.quote(compiler), " ".join(flags), shlex.quote(target),
                " ".join(shlex.quote(o) for o in objects)))
            os.symlink("libSNL.so.0.2", os.path.join(lib_dir, "libSNL.so"))
        else:
            archive = self._compiler("ar", "llvm-ar")
            self.run("{} rc {} {}".format(
                shlex.quote(archive), shlex.quote(os.path.join(lib_dir, "libSNL.a")),
                " ".join(shlex.quote(o) for o in objects)))
            self.run("{} {}".format(
                self._compiler("ranlib", "llvm-ranlib"),
                shlex.quote(os.path.join(lib_dir, "libSNL.a"))))
        self._run_upstream_tests(compiler, flags, objects)

    def _run_upstream_tests(self, compiler, flags, objects):
        """Compile and run upstream's snlTest, requiring its own verdict."""
        if str(self.settings.os) != "OHOS":
            return
        test_source = os.path.join(self.source_folder, "src", "snlTest.cpp")
        if not os.path.isfile(test_source):
            raise ConanException("upstream snlTest.cpp is missing")
        binary = os.path.join(self.build_folder, "snlTest")
        if self.options.shared:
            link_inputs = [os.path.join(self.build_folder, "lib", "libSNL.so.0.2")]
        else:
            link_inputs = objects
        self.run("{} {} -o {} {} {}".format(
            shlex.quote(compiler), " ".join(flags), shlex.quote(binary),
            shlex.quote(test_source),
            " ".join(shlex.quote(item) for item in link_inputs)))
        process = subprocess.run(
            [binary], cwd=self.build_folder,
            env=dict(os.environ, LD_LIBRARY_PATH=os.path.join(self.build_folder, "lib")),
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=600)
        output = process.stdout.decode("utf-8", "replace")
        with open(os.path.join(self.build_folder, "upstream-snltest.log"),
                  "w", encoding="utf-8", newline="\n") as handle:
            handle.write(output)
        tail = [line for line in output.splitlines() if "passed" in line.lower()]
        self.output.info("upstream snlTest: " + " | ".join(tail[-2:]))
        if process.returncode != 0 or "All tests have passed" not in output:
            raise ConanException(
                "upstream snlTest failed; see upstream-snltest.log:\n"
                + output[-2000:])

    def package(self):
        lib_dir = os.path.join(self.package_folder, "lib")
        copy(self, "libSNL.so*", src=os.path.join(self.build_folder, "lib"),
             dst=lib_dir, keep_path=False)
        copy(self, "libSNL.a", src=os.path.join(self.build_folder, "lib"),
             dst=lib_dir, keep_path=False)
        copy(self, "*.h", src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "include"), keep_path=False)
        copy(self, "license.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["SNL"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "libSNL")
        self.cpp_info.set_property("cmake_target_name", "libSNL::libSNL")
