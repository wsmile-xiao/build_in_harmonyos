cmake_minimum_required(VERSION 3.15)
project(test_stduuid CXX)

# Require C++17 (stduuid is a C++17 library; we deliberately do NOT enable
# UUID_USING_CXX20_SPAN so the bundled gsl/span headers are exercised like
# an OHOS C++17 consumer would).
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps
find_package(stduuid REQUIRED)

add_executable(test_stduuid test.cpp)
target_link_libraries(test_stduuid stduuid::stduuid)

enable_testing()
add_test(NAME test_stduuid COMMAND test_stduuid)