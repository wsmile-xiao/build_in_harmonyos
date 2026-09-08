cmake_minimum_required(VERSION 3.15)
project(test_boost_coroutine CXX)

find_package(Boost REQUIRED CONFIG)

add_executable(test_boost_coroutine test_boost_coroutine.cpp)
target_link_libraries(test_boost_coroutine PRIVATE Boost::coroutine Boost::context)
target_compile_features(test_boost_coroutine PRIVATE cxx_std_17)

enable_testing()
add_test(NAME boost_coroutine_test COMMAND test_boost_coroutine)
