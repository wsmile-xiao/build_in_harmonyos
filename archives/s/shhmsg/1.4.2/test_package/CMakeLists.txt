cmake_minimum_required(VERSION 3.15)
project(test_shhmsg C)

find_package(shhmsg CONFIG REQUIRED)

add_executable(test_shhmsg test_shhmsg.c)
target_link_libraries(test_shhmsg PRIVATE shhmsg::shhmsg)

add_executable(test_shhmsg_ohos test_shhmsg_ohos.c)
target_link_libraries(test_shhmsg_ohos PRIVATE shhmsg::shhmsg)

enable_testing()
add_test(NAME test_shhmsg COMMAND test_shhmsg)
add_test(NAME test_shhmsg_ohos COMMAND test_shhmsg_ohos)
