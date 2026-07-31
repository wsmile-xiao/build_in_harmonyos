# test_package/CMakeLists.txt — egl 1.0.5 Conan L1 test
cmake_minimum_required(VERSION 3.15)
project(test_egl C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find the EGL package via Conan-generated CMakeDeps.
find_package(EGL REQUIRED)

add_executable(test_egl test.cpp)
target_link_libraries(test_egl EGL::EGL)
