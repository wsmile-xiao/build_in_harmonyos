cmake_minimum_required(VERSION 3.15)
project(test_pybind11 CXX)

# Find the package via Conan-generated CMakeDeps
find_package(pybind11 CONFIG REQUIRED)

add_executable(test_pybind11 test.cpp)
target_link_libraries(test_pybind11 PRIVATE pybind11::pybind11)
target_compile_features(test_pybind11 PRIVATE cxx_std_17)

# Python.h 是 pybind11 头文件的硬依赖；include 目录由 test_package
# conanfile.py generate() 探测宿主 Python sysconfig 注入。
if(DEFINED PYTHON_INCLUDE_DIR)
  target_include_directories(test_pybind11 PRIVATE ${PYTHON_INCLUDE_DIR})
endif()

enable_testing()
add_test(NAME test_pybind11 COMMAND test_pybind11)