cmake_minimum_required(VERSION 3.15)
project(tinyxml_consumer LANGUAGES CXX)

find_package(tinyxml CONFIG REQUIRED)

add_executable(tinyxml_consumer consumer.cpp)
target_compile_features(tinyxml_consumer PRIVATE cxx_std_11)
target_link_libraries(tinyxml_consumer PRIVATE tinyxml::tinyxml)

enable_testing()
add_test(NAME tinyxml_consumer COMMAND tinyxml_consumer)
