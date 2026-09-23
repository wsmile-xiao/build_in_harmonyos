cmake_minimum_required(VERSION 3.15)
project(test_chrono LANGUAGES CXX)

find_package(date CONFIG REQUIRED)

add_executable(test_chrono test_package.cpp)
target_compile_features(test_chrono PRIVATE cxx_std_17)
target_link_libraries(test_chrono PRIVATE date::date-tz)
