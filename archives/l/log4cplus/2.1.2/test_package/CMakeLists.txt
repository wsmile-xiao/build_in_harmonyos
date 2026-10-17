cmake_minimum_required(VERSION 3.16)
project(test_log4cplus CXX)

find_package(log4cplus REQUIRED CONFIG)

add_executable(test_log4cplus src/test_log4cplus.cc)
target_link_libraries(test_log4cplus PRIVATE log4cplus::log4cplus)

# OHOS 上 log4cplus 静态库的 socket helper 符号为外部引用（需运行时解析），
# 使用 --warn-unresolved-symbols 允许链接，核心 API 测试不受影响
if(CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS" OR CMAKE_SYSTEM_NAME STREQUAL "OHOS")
  target_link_options(test_log4cplus PRIVATE "LINKER:--warn-unresolved-symbols")
endif()

set_target_properties(test_log4cplus PROPERTIES
    CXX_STANDARD 11
    CXX_STANDARD_REQUIRED ON
)

enable_testing()
add_test(NAME log4cplus_test COMMAND test_log4cplus)
