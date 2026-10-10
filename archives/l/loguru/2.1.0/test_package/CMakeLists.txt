cmake_minimum_required(VERSION 3.15)
project(test_package CXX)

find_package(loguru REQUIRED)
find_package(Threads REQUIRED)

add_executable(test_loguru test_loguru.cpp)
target_link_libraries(test_loguru PRIVATE loguru::loguru)
# loguru.cpp 实现编译进测试 TU：非 Windows 平台需要 pthread（线程名）与
# dl（stacktrace 的 dladdr，LOGURU_STACKTRACES 默认开启）
target_link_libraries(test_loguru PRIVATE Threads::Threads ${CMAKE_DL_LIBS})
set_property(TARGET test_loguru PROPERTY CXX_STANDARD 11)
set_property(TARGET test_loguru PROPERTY CXX_STANDARD_REQUIRED ON)
