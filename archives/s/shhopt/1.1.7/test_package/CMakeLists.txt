cmake_minimum_required(VERSION 3.15)
project(test_shhopt C)

find_package(shhopt CONFIG REQUIRED)

add_executable(test_shhopt test_shhopt.c)
target_link_libraries(test_shhopt PRIVATE shhopt::shhopt)

add_executable(test_shhopt_ohos test_shhopt_ohos.c)
target_link_libraries(test_shhopt_ohos PRIVATE shhopt::shhopt)

enable_testing()
add_test(NAME test_shhopt COMMAND test_shhopt)
add_test(NAME test_shhopt_ohos COMMAND test_shhopt_ohos)
