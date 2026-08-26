cmake_minimum_required(VERSION 3.16)
project(test_sonnet CXX)

# Sonnet ships its own CMake config package (KF6Sonnet) and the recipe sets
# cmake_find_mode=none, so CMakeDeps does not generate find modules for it.
# Find the package via its installed KF6SonnetConfig.cmake and link the
# KF6::SonnetCore imported target.
find_package(KF6Sonnet REQUIRED)

add_executable(test_sonnet test_sonnet.cpp)
target_link_libraries(test_sonnet KF6::SonnetCore)

enable_testing()
add_test(NAME test_sonnet COMMAND test_sonnet)