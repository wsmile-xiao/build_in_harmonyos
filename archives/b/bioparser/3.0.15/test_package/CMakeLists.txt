cmake_minimum_required(VERSION 3.15)
project(test_bioparser CXX)

# Find the package via Conan-generated CMakeDeps
find_package(bioparser REQUIRED)

add_executable(test_bioparser test.cpp)
target_link_libraries(test_bioparser bioparser::bioparser)
target_compile_features(test_bioparser PRIVATE cxx_std_11)

enable_testing()
# CTest 用例与 test.cpp 的参数契约一致：必须传入 FASTA 文件路径
add_test(NAME test_bioparser COMMAND test_bioparser ${CMAKE_CURRENT_SOURCE_DIR}/sample.fasta)