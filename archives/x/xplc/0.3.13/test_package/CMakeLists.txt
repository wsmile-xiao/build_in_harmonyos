cmake_minimum_required(VERSION 3.15)
project(test_xplc LANGUAGES CXX)

# Consumer-side check of the packaged xplc: finds it through the Conan-generated
# CMakeDeps config (which must deliver include/xplc-0.3.13, lib/xplc-0.3.13 and
# the UNSTABLE define — see archives/x/xplc/0.3.13/notes.md).
find_package(xplc CONFIG REQUIRED)

add_executable(test_xplc test.cpp)
target_link_libraries(test_xplc PRIVATE xplc::xplc)
