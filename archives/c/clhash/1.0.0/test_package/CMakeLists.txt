cmake_minimum_required(VERSION 3.15)
project(clhash_consumer_test C)

find_package(clhash CONFIG REQUIRED)

add_executable(test_clhash test_clhash.c)
target_link_libraries(test_clhash PRIVATE clhash::clhash)

add_executable(test_ohos test_ohos.c)
target_link_libraries(test_ohos PRIVATE clhash::clhash)

enable_testing()
add_test(NAME test_clhash COMMAND test_clhash)
add_test(NAME test_ohos COMMAND test_ohos)
