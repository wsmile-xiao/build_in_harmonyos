cmake_minimum_required(VERSION 3.15)
project(test_pugixml LANGUAGES CXX)

find_package(pugixml CONFIG REQUIRED)

add_executable(pugixml_consumer consumer.cpp)
target_compile_features(pugixml_consumer PRIVATE cxx_std_11)
target_link_libraries(pugixml_consumer PRIVATE pugixml::pugixml)

enable_testing()
add_test(NAME pugixml_consumer COMMAND pugixml_consumer)
