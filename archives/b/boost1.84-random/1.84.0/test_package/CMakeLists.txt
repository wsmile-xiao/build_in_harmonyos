cmake_minimum_required(VERSION 3.15)
project(test_boost_random CXX)

find_package(Boost REQUIRED CONFIG COMPONENTS random)

add_executable(test_boost_random test_boost_random.cpp)
target_link_libraries(test_boost_random PRIVATE Boost::random)

enable_testing()
add_test(NAME boost_random_test COMMAND test_boost_random)
