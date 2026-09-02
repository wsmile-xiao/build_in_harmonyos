cmake_minimum_required(VERSION 3.15)
project(test_inja CXX)

find_package(inja CONFIG REQUIRED)

add_executable(test_inja test_inja.cpp)
target_link_libraries(test_inja PRIVATE pantor::inja)
set_target_properties(test_inja PROPERTIES CXX_STANDARD 17 CXX_STANDARD_REQUIRED ON)
