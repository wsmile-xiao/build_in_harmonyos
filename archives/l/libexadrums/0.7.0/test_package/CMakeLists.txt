cmake_minimum_required(VERSION 3.15)
project(test_libexadrums CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# OHOS libc++ 15 is stricter than the upstream toolchain about transitive
# includes: several shipped libexadrums headers (e.g. Util/ErrorHandling.h)
# use std::string / std::move / ... without including <string> / <utility> / ...
# The main recipe force-includes these for every TU; mirror that here so the
# test consumer compiles the public headers unchanged.
foreach(_h string utility memory algorithm functional iterator cstdint
        type_traits initializer_list array tuple cstddef)
    add_compile_options("-include${_h}")
endforeach()

# Find the package via Conan-generated CMakeDeps
find_package(libexadrums REQUIRED CONFIG)

add_executable(test_libexadrums test.cpp)
target_link_libraries(test_libexadrums libexadrums::libexadrums)

enable_testing()
add_test(NAME test_libexadrums COMMAND test_libexadrums)
