cmake_minimum_required(VERSION 3.15)
project(test_boost_chrono CXX)

find_package(Boost REQUIRED CONFIG COMPONENTS chrono)

add_executable(test_boost_chrono test_boost_chrono.cpp)
target_link_libraries(test_boost_chrono PRIVATE Boost::chrono)

enable_testing()
add_test(NAME boost_chrono_test COMMAND test_boost_chrono)
