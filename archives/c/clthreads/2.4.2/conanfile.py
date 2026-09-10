import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class ClthreadsConan(ConanFile):
    name = "clthreads"
    version = "2.4.2"
    description = "C++ threading and inter-thread communication library"
    license = "GPL-2.0-or-later"
    homepage = "https://kokkinizita.linuxaudio.org/linuxaudio/downloads/index.html"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("clthreads supports Linux and OHOS only")
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("clthreads supports OHOS armv8 only")
        if not self.options.shared:
            raise ConanInvalidConfiguration("clthreads 2.4.2 only builds a shared library")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cxx = compilers.get("cpp", "clang++") if compilers else "clang++"
        cancel_arg = " CLTHREADS_NO_PTHREAD_CANCEL=1" if str(self.settings.os) == "OHOS" else ""
        self.run("make -C source -j1 CXX={}{} check".format(cxx, cancel_arg))

    def package(self):
        src = os.path.join(self.build_folder, "source")
        copy(self, "clthreads.h", src, os.path.join(self.package_folder, "include"))
        lib = os.path.join(self.package_folder, "lib")
        min_name = "libclthreads.so.{}".format(self.version)
        copy(self, min_name, src, lib)
        base = os.path.join(lib, min_name)
        # The OHOS device home filesystem rejects symlinks and its build
        # environment can resolve a non-executable `install`, so the recipe
        # stages the soname chain itself with real file copies.
        maj_name = "libclthreads.so.{}".format(str(self.version).split(".")[0])
        for name in (maj_name, "libclthreads.so"):
            shutil.copyfile(base, os.path.join(lib, name))

    def package_info(self):
        self.cpp_info.libs = ["clthreads"]
        self.cpp_info.system_libs = ["pthread"]
        if str(self.settings.os) == "OHOS":
            self.cpp_info.defines = ["CLTHREADS_NO_PTHREAD_CANCEL"]
        self.cpp_info.set_property("cmake_file_name", "clthreads")
        self.cpp_info.set_property("cmake_target_name", "clthreads::clthreads")
