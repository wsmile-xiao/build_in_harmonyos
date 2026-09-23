cmake_minimum_required(VERSION 3.15)
project(test_boost_thread CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Boost REQUIRED CONFIG COMPONENTS thread)

add_executable(test_boost_thread test_boost_thread.cpp)
target_link_libraries(test_boost_thread PRIVATE Boost::thread)
target_link_libraries(test_boost_thread PRIVATE pthread)

enable_testing()
add_test(NAME boost_thread_test COMMAND test_boost_thread)
