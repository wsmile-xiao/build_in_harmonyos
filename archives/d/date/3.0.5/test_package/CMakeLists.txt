cmake_minimum_required(VERSION 3.15)
project(test_date LANGUAGES CXX)

find_package(date CONFIG REQUIRED)

add_executable(test_date test_package.cpp)
target_compile_features(test_date PRIVATE cxx_std_17)
target_link_libraries(test_date PRIVATE date::date-tz)
