cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES C)

include(CTest)

# libint 由 conan CMakeDeps 生成 LibintConfig.cmake 提供（find_package(Libint)）
find_package(Libint CONFIG REQUIRED)

add_executable(test_libint test_libint.c)
target_link_libraries(test_libint PRIVATE Libint::int)
target_compile_features(test_libint PRIVATE c_std_99)

add_test(NAME libint_consumer COMMAND test_libint)
