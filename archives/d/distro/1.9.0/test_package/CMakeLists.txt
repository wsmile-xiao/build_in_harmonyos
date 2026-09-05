cmake_minimum_required(VERSION 3.15)
project(test_distro LANGUAGES CXX)

# distro is a pure-Python package: no C/C++ library to link.
# The test program only needs a C++ runtime and verifies the distro
# module through the conanrun environment (see test_package.cpp).
find_package(distro CONFIG REQUIRED)

add_executable(test_distro test_package.cpp)
target_link_libraries(test_distro PRIVATE distro::distro)

enable_testing()
add_test(NAME test_distro COMMAND test_distro)