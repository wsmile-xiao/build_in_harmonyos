cmake_minimum_required(VERSION 3.15)
project(test_unqlite C)

find_package(unqlite CONFIG REQUIRED)

add_executable(test_unqlite test_unqlite.c)
target_link_libraries(test_unqlite PRIVATE unqlite::unqlite)
set_property(TARGET test_unqlite PROPERTY C_STANDARD 99)

# HarmonyOS 专项测试：磁盘文件持久化语义（独立于内存库消费者用例）
add_executable(test_unqlite_ohos test_unqlite_ohos.c)
target_link_libraries(test_unqlite_ohos PRIVATE unqlite::unqlite)
set_property(TARGET test_unqlite_ohos PROPERTY C_STANDARD 99)