cmake_minimum_required(VERSION 3.15)
project(test_boost_wserialization CXX)

find_package(Boost REQUIRED CONFIG COMPONENTS wserialization)

add_executable(test_wserialization test_wserialization.cpp)
target_link_libraries(test_wserialization PRIVATE Boost::wserialization)

enable_testing()
add_test(NAME boost_wserialization_test COMMAND test_wserialization)
