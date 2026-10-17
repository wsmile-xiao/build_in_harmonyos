cmake_minimum_required(VERSION 3.15)
project(test_collections_c C)

find_package(collections-c REQUIRED)

add_executable(test_collections_c test.c)
target_link_libraries(test_collections_c collections-c::collectc)

# 鸿蒙专项适配测试：内存池对齐 + 高频容器压力（真实 API，非空壳）
add_executable(test_collections_c_ohos test_ohos_adapt.c)
target_link_libraries(test_collections_c_ohos collections-c::collectc)

enable_testing()
add_test(NAME test_collections_c COMMAND test_collections_c)
add_test(NAME test_collections_c_ohos COMMAND test_collections_c_ohos)