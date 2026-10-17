cmake_minimum_required(VERSION 3.15)
project(test_libgooglepinyin LANGUAGES CXX)

find_package(libgooglepinyin REQUIRED CONFIG)

add_executable(test_libgooglepinyin test_libgooglepinyin.cpp)
target_compile_features(test_libgooglepinyin PRIVATE cxx_std_17)
target_link_libraries(test_libgooglepinyin PRIVATE libgooglepinyin::libgooglepinyin)

enable_testing()
add_test(NAME test_libgooglepinyin COMMAND test_libgooglepinyin)
