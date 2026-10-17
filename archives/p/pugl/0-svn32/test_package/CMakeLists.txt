cmake_minimum_required(VERSION 3.16)
project(pugl_test_package LANGUAGES C)

find_package(pugl CONFIG REQUIRED)

add_executable(test_api test_api.c)
target_link_libraries(test_api PRIVATE pugl::pugl)

add_executable(test_ohos test_ohos.c)
target_link_libraries(test_ohos PRIVATE pugl::pugl)

enable_testing()
add_test(NAME pugl_public_api COMMAND test_api)
add_test(NAME pugl_harmonyos_backend COMMAND test_ohos)
