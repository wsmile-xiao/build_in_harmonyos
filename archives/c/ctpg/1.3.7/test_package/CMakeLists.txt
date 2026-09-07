cmake_minimum_required(VERSION 3.15)
project(test_ctpg CXX)

# Find the package via Conan-generated CMakeDeps
find_package(ctpg REQUIRED)

add_executable(test_ctpg test_ctpg.cpp)
target_link_libraries(test_ctpg ctpg::ctpg)
target_compile_features(test_ctpg PRIVATE cxx_std_17)

enable_testing()
add_test(NAME test_ctpg COMMAND test_ctpg)