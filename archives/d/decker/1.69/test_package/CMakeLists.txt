cmake_minimum_required(VERSION 3.15)
project(test_decker C)

# decker is an application package (cpp_info.libdirs = []).
# CMakeDeps exposes the package's bindirs via the decker_BIN_DIRS CMake
# variable (generated from cpp_info.bindirs). We read it at configure time
# and bake the lilt path into the test binary as LILT_DEFAULT_BIN, so the
# test still works even if the LILT_BIN environment variable is unset.
find_package(decker REQUIRED)

if(DEFINED DECKER_BIN_DIRS)
    get_filename_component(_decker_bin_dir "${DECKER_BIN_DIRS}" ABSOLUTE)
elseif(DEFINED ENV{DECKER_BIN_DIR})
    get_filename_component(_decker_bin_dir "$ENV{DECKER_BIN_DIR}" ABSOLUTE)
else()
    set(_decker_bin_dir "${CMAKE_INSTALL_PREFIX}/bin")
endif()

add_executable(test_decker test.c)
target_compile_definitions(test_decker PRIVATE
    LILT_DEFAULT_BIN="${_decker_bin_dir}/lilt")

enable_testing()
add_test(NAME test_decker COMMAND test_decker)
