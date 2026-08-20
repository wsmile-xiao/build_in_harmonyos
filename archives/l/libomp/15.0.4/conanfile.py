from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, save
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibompConan(ConanFile):
    name = "libomp"
    version = "15.0.4"
    description = "LLVM OpenMP runtime library"
    license = "Apache-2.0"
    homepage = "https://openmp.llvm.org"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # The openmp standalone tarball is missing LLVM's cmake/Modules/ExtendPath.cmake
        # which is referenced via LLVM_COMMON_CMAKE_UTILS (patched to local cmake/ dir).
        # Create it from the LLVM 15.0.4 source.
        extend_path_cmake = (
            '# Extend the path in `base_path` with the path in `current_segment`, returning\n'
            '# the result in `joined_path`. If `current_segment` is an absolute path then\n'
            '# just return it, in effect overriding `base_path`, and issue a warning.\n'
            '#\n'
            '# Note that the code returns a relative path (avoiding introducing leading\n'
            '# slashes) if `base_path` is empty.\n'
            'function(extend_path joined_path base_path current_segment)\n'
            '  if("${current_segment}" STREQUAL "")\n'
            '    set(temp_path "${base_path}")\n'
            '  elseif("${base_path}" STREQUAL "")\n'
            '    set(temp_path "${current_segment}")\n'
            '  elseif(IS_ABSOLUTE "${current_segment}")\n'
            '    message(WARNING "Since \\"${current_segment}\\" is absolute, it overrides base path: \\"${base_path}\\".")\n'
            '    set(temp_path "${current_segment}")\n'
            '  else()\n'
            '    set(temp_path "${base_path}/${current_segment}")\n'
            '  endif()\n'
            '  set(${joined_path} "${temp_path}" PARENT_SCOPE)\n'
            'endfunction()\n'
        )
        save(self, "cmake/Modules/ExtendPath.cmake", extend_path_cmake)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["OPENMP_STANDALONE_BUILD"] = "ON"
        tc.variables["LIBOMP_OMPT_SUPPORT"] = "OFF"
        tc.variables["OPENMP_ENABLE_LIBOMPTARGET"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["omp"]
