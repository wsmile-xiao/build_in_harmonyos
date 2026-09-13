cmake_minimum_required(VERSION 3.15)
project(test_dcadec C)

find_package(dcadec CONFIG REQUIRED)

add_executable(test_dcadec test.c)
target_compile_features(test_dcadec PRIVATE c_std_99)
target_link_libraries(test_dcadec PRIVATE dcadec::dcadec)

enable_testing()
add_test(NAME test_dcadec COMMAND test_dcadec)
