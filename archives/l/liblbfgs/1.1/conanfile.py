import os
import textwrap

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, save
from conan.tools.scm import Version
from conan.tools.files import apply_conandata_patches, export_conandata_patches


class LibLbfgsConan(ConanFile):
    name = "liblbfgs"
    version = "1.1"
    description = "A library of Limited-memory Broyden-Fletcher-Goldfarb-Shanno (L-BFGS)"
    license = "MIT"
    homepage = "https://www.chokkan.org/software/liblbfgs/"
    url = "https://www.chokkan.org/software/liblbfgs/"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("liblbfgs 1.1 is adapted only for Linux/OHOS in this recipe")
        compiler = str(self.settings.compiler)
        compiler_version = Version(str(self.settings.compiler.version))
        if compiler == "gcc" and compiler_version < "7":
            raise ConanInvalidConfiguration("liblbfgs 1.1 requires GCC >= 7")
        if compiler == "clang" and compiler_version < "7":
            raise ConanInvalidConfiguration("liblbfgs 1.1 requires Clang >= 7")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=False)
        apply_conandata_patches(self)

    def generate(self):
        self._write_cmake_project()
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        if self.options.get_safe("fPIC") is not None:
            tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(self.options.fPIC)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if can_run(self):
            cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "liblbfgs")
        self.cpp_info.set_property("cmake_target_name", "liblbfgs::liblbfgs")
        self.cpp_info.set_property("pkg_config_name", "liblbfgs")
        self.cpp_info.libs = ["lbfgs"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]

    def _write_cmake_project(self):
        cmakelists = r"""
cmake_minimum_required(VERSION 3.15)
project(liblbfgs C)

include(CTest)

add_library(lbfgs src/lbfgs.c)
target_include_directories(lbfgs PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>)
if(NOT MSVC)
    target_link_libraries(lbfgs PUBLIC m)
endif()

add_executable(liblbfgs_sample src/main.c)
target_link_libraries(liblbfgs_sample PRIVATE lbfgs)

add_executable(test_liblbfgs_build test_liblbfgs_build.c)
target_link_libraries(test_liblbfgs_build PRIVATE lbfgs)
add_test(NAME test_liblbfgs_build COMMAND test_liblbfgs_build)

install(TARGETS lbfgs
    ARCHIVE DESTINATION lib
    LIBRARY DESTINATION lib)
install(FILES include/lbfgs.h DESTINATION include)
"""
        build_test = r"""
#include <lbfgs.h>
#include <math.h>

struct solve_state {
    int evaluations;
};

static lbfgsfloatval_t evaluate(void *instance, const lbfgsfloatval_t *x,
                                lbfgsfloatval_t *g, const int n,
                                const lbfgsfloatval_t step)
{
    struct solve_state *state = (struct solve_state *)instance;
    const lbfgsfloatval_t dx = x[0] - 1.0;
    const lbfgsfloatval_t dy = x[1] + 2.0;
    (void)n;
    (void)step;

    state->evaluations++;
    g[0] = 2.0 * dx;
    g[1] = 2.0 * dy;
    return dx * dx + dy * dy;
}

static int progress(void *instance, const lbfgsfloatval_t *x,
                    const lbfgsfloatval_t *g, const lbfgsfloatval_t fx,
                    const lbfgsfloatval_t xnorm, const lbfgsfloatval_t gnorm,
                    const lbfgsfloatval_t step, int n, int k, int ls)
{
    (void)instance;
    (void)x;
    (void)g;
    (void)fx;
    (void)xnorm;
    (void)gnorm;
    (void)step;
    (void)n;
    (void)k;
    (void)ls;
    return 0;
}

int main(void)
{
    lbfgsfloatval_t x[2] = {10.0, -7.0};
    lbfgsfloatval_t g[2] = {0.0, 0.0};
    lbfgs_parameter_t param;
    struct solve_state state = {0};
    int ret;
    lbfgsfloatval_t fx;

    lbfgs_parameter_init(&param);
    if (param.m != 6) {
        return 1;
    }
    if (fabs(param.epsilon - 1e-5) > 1e-12) {
        return 2;
    }
    if (param.max_iterations != 0) {
        return 3;
    }

    param.max_iterations = 64;
    ret = lbfgs(2, x, evaluate, progress, &state, &param);
    if (ret < 0) {
        return 4;
    }

    fx = evaluate(&state, x, g, 2, 0.0);
    if (fx > 1e-10) {
        return 5;
    }
    if (fabs(x[0] - 1.0) > 1e-5 || fabs(x[1] + 2.0) > 1e-5) {
        return 6;
    }
    if (state.evaluations == 0) {
        return 7;
    }
    return 0;
}
"""
        save(self, os.path.join(self.source_folder, "CMakeLists.txt"), textwrap.dedent(cmakelists).lstrip())
        save(self, os.path.join(self.source_folder, "test_liblbfgs_build.c"), textwrap.dedent(build_test).lstrip())
