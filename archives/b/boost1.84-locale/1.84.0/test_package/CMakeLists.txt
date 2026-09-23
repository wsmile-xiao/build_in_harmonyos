cmake_minimum_required(VERSION 3.15)
project(test_boost_locale CXX)

find_package(Boost REQUIRED CONFIG COMPONENTS locale)

add_executable(test_boost_locale test_boost_locale.cpp)
target_link_libraries(test_boost_locale PRIVATE Boost::locale)

enable_testing()
add_test(NAME boost_locale_test COMMAND test_boost_locale)
