cmake_minimum_required(VERSION 3.15)
project(test_ifcopenshell CXX)

# Find the package via Conan-generated CMakeDeps
find_package(ifcopenshell REQUIRED)

# 依赖 include 目录由 test_package/conanfile.py generate() 注入
include_directories(
    ${BOOST_INCLUDE_DIR}
    ${EIGEN_INCLUDE_DIR}
    ${LIBXML2_INCLUDE_DIR}
    ${ZLIB_INCLUDE_DIR}
    ${OPENCASCADE_INCLUDE_DIR}
)

add_executable(test_ifcopenshell test.cpp)
target_link_libraries(test_ifcopenshell ifcopenshell::ifcopenshell)
target_compile_features(test_ifcopenshell PRIVATE cxx_std_17)

enable_testing()
add_test(NAME test_ifcopenshell COMMAND test_ifcopenshell)