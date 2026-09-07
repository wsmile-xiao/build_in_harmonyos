cmake_minimum_required(VERSION 3.13)
project(infoware_test LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(infoware REQUIRED)

add_executable(infoware_test main.cpp)
target_link_libraries(infoware_test PRIVATE infoware::infoware)

enable_testing()
add_test(NAME consumer_api_smoke COMMAND infoware_test)
