cmake_minimum_required(VERSION 3.15)
project(test_cld2 CXX)

find_package(cld2 REQUIRED)

add_executable(test_cld2 test_cld2.cpp)
target_link_libraries(test_cld2 cld2::cld2)

enable_testing()
add_test(NAME test_cld2_english COMMAND test_cld2 english)
add_test(NAME test_cld2_french COMMAND test_cld2 french)
