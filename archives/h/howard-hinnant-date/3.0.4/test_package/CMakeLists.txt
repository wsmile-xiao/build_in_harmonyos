cmake_minimum_required(VERSION 3.15)
project(test_howard_hinnant_date LANGUAGES CXX)

find_package(date CONFIG REQUIRED)

add_executable(test_howard_hinnant_date test_package.cpp)
target_compile_features(test_howard_hinnant_date PRIVATE cxx_std_17)
target_link_libraries(test_howard_hinnant_date PRIVATE date::date-tz)
