import os
import stat

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.files import apply_conandata_patches, collect_libs, export_conandata_patches, get
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class Adios2Conan(ConanFile):
    name = "adios2"
    version = "2.12.1"
    description = "Next generation of ADIOS developed in the Exascale Computing Program"
    license = "Apache-2.0"
    homepage = "https://adios2.readthedocs.io"
    url = "https://github.com/ornladios/ADIOS2"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        check_min_cppstd(self, 17)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = str(self.settings.arch)
            tc.cache_variables["FFS_FLOAT_FORMAT_TEST"] = "0"
            tc.cache_variables["FFS_FLOAT_FORMAT_TEST__TRYRUN_OUTPUT"] = "Format_IEEE_754_littleendian"
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.variables["BUILD_TESTING"] = False
        tc.variables["ADIOS2_BUILD_EXAMPLES"] = False
        tc.variables["ADIOS2_LIBADIOS_MODE"] = True
        tc.variables["ADIOS2_USE_EXTERNAL_DEPENDENCIES"] = False
        for option in (
            "AWSSDK", "BigWhoop", "Blosc2", "BZip2", "CUDA", "Campaign",
            "Catalyst", "CURL", "DAOS", "DataMan", "DataSpaces", "Fortran",
            "HDF5", "HDF5_VOL", "IME", "KVCACHE", "Kokkos", "LIBPRESSIO",
            "MGARD", "MHS", "MPI", "OpenSSL", "PNG", "PRODM", "Python",
            "SST", "SZ", "SZ3", "Sodium", "UCX", "XRootD", "ZFP", "ZeroMQ",
        ):
            tc.variables[f"ADIOS2_USE_{option}"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        os.makedirs(os.path.join(self.package_folder, "bin"), exist_ok=True)
        if self.settings.os == "OHOS":
            script = os.path.join(self.build_folder, "cmake", "install", "post", "generate-adios2-config.sh")
            with open(script, "w", encoding="utf-8", newline="\n") as handle:
                handle.write("#!/bin/sh\nexit 0\n")
        cmake = CMake(self)
        cmake.install()
        if self.settings.os == "OHOS":
            config = os.path.join(self.package_folder, "bin", "adios2-config")
            libraries = " ".join(f"-l{library}" for library in collect_libs(self))
            content = f'''#!/bin/sh
prefix="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
case "${{1:-}}" in
    --prefix) printf '%s\\n' "$prefix" ;;
    --version) printf '%s\\n' "{self.version}" ;;
    --cflags|--cxxflags) printf '%s\\n' "-I$prefix/include" ;;
    --libs) printf '%s\\n' "-L$prefix/lib {libraries} -lpthread -ldl" ;;
    *) printf '%s\\n' "Usage: adios2-config --prefix|--version|--cflags|--cxxflags|--libs" ;;
esac
'''
            with open(config, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
            os.chmod(config, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "adios2")
        self.cpp_info.set_property("cmake_target_name", "adios2::adios2")
        self.cpp_info.libs = collect_libs(self)
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread", "dl"]
