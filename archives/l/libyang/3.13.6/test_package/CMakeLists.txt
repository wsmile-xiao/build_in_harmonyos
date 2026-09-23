cmake_minimum_required(VERSION 3.15)
project(libyang_consumer C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

find_package(libyang CONFIG REQUIRED)

enable_testing()

add_executable(test_libyang test_libyang.c)
target_compile_options(test_libyang PRIVATE -Wall -Wextra)
target_link_libraries(test_libyang PRIVATE libyang::libyang)
# Rely solely on transitive propagation from libyang::libyang (whose
# package_info requires pcre2::pcre2-8 with headers). No explicit
# find_package(pcre2): test_package only requires libyang so CMakeDeps
# emits only libyang config files; an explicit find_package(pcre2)
# hard-fails with "Could not find package configuration file provided
# by pcre2" (preflight 19:33).
add_test(NAME libyang_consumer COMMAND test_libyang)

# The packaged yanglint CLI must execute and identify itself. YANGLINT_EXE is
# passed as an absolute path by the test conanfile (PATH lookup is not
# reliable inside the ctest environment).
if(NOT YANGLINT_EXE)
    message(FATAL_ERROR "YANGLINT_EXE cache variable is required")
endif()
add_test(NAME yanglint_version COMMAND "${YANGLINT_EXE}" --version)
