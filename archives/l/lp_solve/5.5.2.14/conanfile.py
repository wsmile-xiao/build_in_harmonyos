import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import check_sha256, copy, get, save, unzip


class LpSolveConan(ConanFile):
    name = "lp_solve"
    version = "5.5.2.14"
    description = "Mixed-integer linear programming solver"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/lp-solve/lp_solve"
    url = ""

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        source = self.conan_data["sources"]
        cache_root = os.getenv(
            "OHPCD_SOURCE_CACHE", os.path.expanduser("~/Download")
        )
        staged = os.path.join(cache_root, "lp_solve-5.5.2.14.tar.gz")
        if os.path.isfile(staged):
            check_sha256(self, staged, source["sha256"])
            unzip(self, staged, strip_root=True)
        else:
            get(self, **source, strip_root=True)

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        toolchain.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(
            self.options.get_safe("fPIC", True)
        )
        toolchain.generate()

    def build(self):
        save(
            self,
            os.path.join(self.source_folder, "CMakeLists.txt"),
            self._cmake_lists(),
        )
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = ["lpsolve55"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include/lp_solve"]
        self.cpp_info.set_property("cmake_file_name", "lp_solve")
        self.cpp_info.set_property("cmake_target_name", "lp_solve::lp_solve")
        if self.settings.os in ("Linux", "OHOS", "FreeBSD"):
            self.cpp_info.system_libs = ["m", "dl"]

    @staticmethod
    def _cmake_lists():
        return """\
cmake_minimum_required(VERSION 3.15)
project(lp_solve VERSION 5.5.2.14 LANGUAGES C)

set(LP_SOLVE_SOURCES
    lp_MDO.c
    shared/commonlib.c
    shared/mmio.c
    shared/myblas.c
    ini.c
    fortify.c
    colamd/colamd.c
    lp_rlp.c
    lp_crash.c
    bfp/bfp_LUSOL/lp_LUSOL.c
    bfp/bfp_LUSOL/LUSOL/lusol.c
    lp_Hash.c
    lp_lib.c
    lp_wlp.c
    lp_matrix.c
    lp_mipbb.c
    lp_MPS.c
    lp_params.c
    lp_presolve.c
    lp_price.c
    lp_pricePSE.c
    lp_report.c
    lp_scale.c
    lp_simplex.c
    lp_SOS.c
    lp_utils.c
    yacc_read.c
)

add_library(lpsolve55 ${LP_SOLVE_SOURCES})
target_include_directories(lpsolve55 PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}>
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/shared>
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/bfp>
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/bfp/bfp_LUSOL>
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/bfp/bfp_LUSOL/LUSOL>
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/colamd>
    $<INSTALL_INTERFACE:include/lp_solve>
)
target_compile_definitions(lpsolve55 PRIVATE
    YY_NEVER_INTERACTIVE
    PARSER_LP
    INVERSE_ACTIVE=INVERSE_LUSOL
    RoleIsExternalInvEngine
)
if(UNIX)
    target_link_libraries(lpsolve55 PUBLIC m ${CMAKE_DL_LIBS})
endif()

add_executable(lp_solve_cli lp_solve/lp_solve.c)
set_target_properties(lp_solve_cli PROPERTIES OUTPUT_NAME lp_solve)
target_link_libraries(lp_solve_cli PRIVATE lpsolve55)
target_compile_definitions(lp_solve_cli PRIVATE
    YY_NEVER_INTERACTIVE
    PARSER_LP
    INVERSE_ACTIVE=INVERSE_LUSOL
    RoleIsExternalInvEngine
)

install(TARGETS lpsolve55 lp_solve_cli
    ARCHIVE DESTINATION lib
    LIBRARY DESTINATION lib
    RUNTIME DESTINATION bin
)
file(GLOB LP_SOLVE_PUBLIC_HEADERS "${CMAKE_CURRENT_SOURCE_DIR}/*.h")
install(FILES ${LP_SOLVE_PUBLIC_HEADERS} DESTINATION include/lp_solve)
install(DIRECTORY shared/
    DESTINATION include/lp_solve/shared
    FILES_MATCHING PATTERN "*.h"
)
install(DIRECTORY bfp/
    DESTINATION include/lp_solve/bfp
    FILES_MATCHING PATTERN "*.h"
)
install(DIRECTORY colamd/
    DESTINATION include/lp_solve/colamd
    FILES_MATCHING PATTERN "*.h"
)
"""
