cmake_minimum_required(VERSION 3.15)
project(test_itlib CXX)

find_package(itlib CONFIG REQUIRED)

add_executable(test_itlib test_itlib.cpp)
target_link_libraries(test_itlib PRIVATE itlib::itlib)
set_target_properties(test_itlib PROPERTIES CXX_STANDARD 17)

enable_testing()
add_test(NAME test_itlib COMMAND test_itlib)