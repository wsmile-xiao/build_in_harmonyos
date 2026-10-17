cmake_minimum_required(VERSION 3.15)
project(test_boost_context CXX)

find_package(Boost REQUIRED CONFIG COMPONENTS context)

add_executable(test_context test_context.cpp)
target_link_libraries(test_context PRIVATE Boost::context)

enable_testing()
add_test(NAME boost_context_test COMMAND test_context)
