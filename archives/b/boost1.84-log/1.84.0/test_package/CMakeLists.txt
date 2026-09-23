cmake_minimum_required(VERSION 3.15)
project(test_boost_log CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(boost1.84-log REQUIRED)
find_package(boost REQUIRED)

enable_testing()
add_executable(test_boost_log test_boost_log.cpp)
target_link_libraries(test_boost_log PRIVATE boost1.84-log::boost_log_setup Boost::headers)
add_test(NAME boost_log_test COMMAND test_boost_log)
