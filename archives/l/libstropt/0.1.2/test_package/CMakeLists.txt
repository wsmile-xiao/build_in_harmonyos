cmake_minimum_required(VERSION 3.15)
project(test_libstropt C)

find_package(stropt CONFIG REQUIRED)

add_executable(test_libstropt test_libstropt.c)
target_link_libraries(test_libstropt PRIVATE stropt::stropt)

add_executable(test_libstropt_ohos test_libstropt_ohos.c)
target_link_libraries(test_libstropt_ohos PRIVATE stropt::stropt)

enable_testing()
add_test(NAME test_libstropt COMMAND test_libstropt)
add_test(NAME test_libstropt_ohos COMMAND test_libstropt_ohos)
