cmake_minimum_required(VERSION 3.16)
project(test_i18n-demo LANGUAGES CXX)

find_package(i18n-demo CONFIG REQUIRED)

add_executable(test_i18n-demo src/test_i18n.cpp)
target_link_libraries(test_i18n-demo PRIVATE i18n-demo::i18n-demo)
