cmake_minimum_required(VERSION 3.15)
project(test_rlog LANGUAGES CXX)

find_package(rlog CONFIG REQUIRED)
add_executable(test_rlog test.cpp)
# rAssert/rError 宏使用 RLOG_COMPONENT（上游缺省值只是 "unknown" 且会产生编译告警）
target_compile_definitions(test_rlog PRIVATE RLOG_COMPONENT=consumer_test)
target_link_libraries(test_rlog PRIVATE rlog::rlog)
