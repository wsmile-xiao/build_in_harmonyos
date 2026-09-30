cmake_minimum_required(VERSION 3.15)
project(test_openddl_parser CXX)

# 通过 Conan 生成的 CMakeDeps 查找本包
find_package(openddl-parser REQUIRED)

add_executable(test_openddl_parser test_openddl_parser.cpp)
target_link_libraries(test_openddl_parser openddl-parser::openddl-parser)
target_compile_features(test_openddl_parser PRIVATE cxx_std_11)

enable_testing()
add_test(NAME test_openddl_parser COMMAND test_openddl_parser)