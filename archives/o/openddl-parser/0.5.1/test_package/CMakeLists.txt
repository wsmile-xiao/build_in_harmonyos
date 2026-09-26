cmake_minimum_required(VERSION 3.15)
project(test_openddlparser CXX)

# 经 Conan CMakeDeps 消费被测包（conanfile.py package_info: cmake_file_name=openddlparser）
find_package(openddlparser REQUIRED)

add_executable(test_openddlparser consumer.cpp)
target_link_libraries(test_openddlparser openddlparser::openddlparser)
target_compile_features(test_openddlparser PRIVATE cxx_std_11)

enable_testing()
add_test(NAME test_openddlparser COMMAND test_openddlparser)
