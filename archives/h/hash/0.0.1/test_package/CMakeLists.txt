cmake_minimum_required(VERSION 3.15)
project(test_hash_consumer C)

find_package(hash CONFIG REQUIRED)

# 消费者验证: 仅用公开头文件 + libhash.a 链接运行
add_executable(test_hash_consumer test.c)
target_link_libraries(test_hash_consumer PRIVATE hash::hash)

# HarmonyOS 专项测试: 大规模压力/迭代/删除/生命周期
add_executable(hash_ohos_test ohos_test.c)
target_link_libraries(hash_ohos_test PRIVATE hash::hash)

enable_testing()
add_test(NAME hash_consumer COMMAND test_hash_consumer)
add_test(NAME hash_ohos COMMAND hash_ohos_test)
