cmake_minimum_required(VERSION 3.15)
project(test_libmialm C)

find_package(libmialm REQUIRED)

add_executable(libmialm_api_test libmialm_api_test.c)
target_link_libraries(libmialm_api_test PRIVATE libmialm::libmialm)

add_executable(libmialm_ohos_test libmialm_ohos_test.c)
target_link_libraries(libmialm_ohos_test PRIVATE libmialm::libmialm)

enable_testing()
add_test(NAME libmialm_api_test COMMAND libmialm_api_test)
add_test(NAME libmialm_ohos_test COMMAND libmialm_ohos_test)
