cmake_minimum_required(VERSION 3.15)
project(test_daw_json_link CXX)

find_package(daw-json-link REQUIRED)
find_package(daw-utf-range REQUIRED)
find_package(daw-header-libraries REQUIRED)

add_executable(test_daw_json_link test_daw_json_link.cpp)
target_link_libraries(test_daw_json_link PRIVATE daw::daw-json-link)
set_target_properties(test_daw_json_link PROPERTIES CXX_STANDARD 17)
