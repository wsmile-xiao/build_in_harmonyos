cmake_minimum_required(VERSION 3.15)
project(test_boost_prg_exec_monitor CXX)

find_package(Boost REQUIRED CONFIG COMPONENTS prg_exec_monitor)

add_executable(test_prg_exec_monitor test_prg_exec_monitor.cpp)
target_link_libraries(test_prg_exec_monitor PRIVATE Boost::prg_exec_monitor)

enable_testing()
add_test(NAME boost_prg_exec_monitor_test COMMAND test_prg_exec_monitor)
