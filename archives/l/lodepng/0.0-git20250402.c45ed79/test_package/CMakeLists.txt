cmake_minimum_required(VERSION 3.15)
project(test_lodepng CXX)

find_package(lodepng REQUIRED)

add_executable(test_lodepng test_lodepng.cpp)
target_link_libraries(test_lodepng lodepng::lodepng)

enable_testing()
add_test(NAME test_lodepng COMMAND test_lodepng)
