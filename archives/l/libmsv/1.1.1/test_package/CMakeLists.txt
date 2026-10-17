cmake_minimum_required(VERSION 3.15)
project(test_libmsv C)

find_package(libmsv REQUIRED CONFIG)

add_executable(test_upstream test_upstream.c)
target_link_libraries(test_upstream PRIVATE libmsv::libmsv)

add_executable(test_ohos test_ohos.c)
target_link_libraries(test_ohos PRIVATE libmsv::libmsv)

enable_testing()
add_test(NAME upstream_msva_integration COMMAND test_upstream)
add_test(NAME ohos_api_contract COMMAND test_ohos)
