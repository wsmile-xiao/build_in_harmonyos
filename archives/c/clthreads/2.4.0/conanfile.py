from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class ClthreadsConan(ConanFile):
    name = "clthreads"
    version = "2.4.0"
    description = "C++ threading and inter-thread communication library"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/dmeliza/clthreads"
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
            raise ConanInvalidConfiguration("clthreads 2.4.0 only builds a shared library")

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
        self.run("make -j1 CXX={}{} check".format(cxx, cancel_arg))

    def package(self):
        self.run('make install PREFIX=/ LIBDIR=lib DESTDIR="{}"'.format(self.package_folder))

    def package_info(self):
        self.cpp_info.libs = ["clthreads"]
        self.cpp_info.system_libs = ["pthread"]
        if str(self.settings.os) == "OHOS":
            self.cpp_info.defines = ["CLTHREADS_NO_PTHREAD_CANCEL"]
        self.cpp_info.set_property("cmake_file_name", "clthreads")
        self.cpp_info.set_property("cmake_target_name", "clthreads::clthreads")
