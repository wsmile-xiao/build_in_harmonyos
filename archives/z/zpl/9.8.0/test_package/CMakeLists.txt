cmake_minimum_required(VERSION 3.15)
project(test_zpl C)

find_package(zpl CONFIG REQUIRED)

add_executable(test_zpl test_zpl.c)
target_link_libraries(test_zpl PRIVATE zpl::zpl)
target_compile_features(test_zpl PRIVATE c_std_99)

enable_testing()
add_test(NAME test_zpl COMMAND test_zpl)
