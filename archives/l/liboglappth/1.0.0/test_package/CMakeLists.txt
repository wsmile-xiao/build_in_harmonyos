cmake_minimum_required(VERSION 3.15)
project(test_liboglappth CXX)

find_package(liboglappth REQUIRED CONFIG)
# The library's API uses GL types (GLfloat etc.); the gl4es dependency provides
# the GL headers and libGL that liboglappth leaves undefined at link time.
find_package(gl4es REQUIRED CONFIG)

add_executable(test_liboglappth test.cpp)
target_link_libraries(test_liboglappth PRIVATE liboglappth::liboglappth gl4es::gl4es)

add_executable(harmonyos_specific_test harmonyos_specific_test.cpp)
target_link_libraries(harmonyos_specific_test PRIVATE liboglappth::liboglappth gl4es::gl4es)
