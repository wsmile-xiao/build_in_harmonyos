cmake_minimum_required(VERSION 3.16)
project(test_squirrel LANGUAGES CXX)

find_package(squirrel CONFIG REQUIRED)

enable_testing()
add_executable(squirrel_consumer consumer.cpp)
target_compile_features(squirrel_consumer PRIVATE cxx_std_11)
target_link_libraries(squirrel_consumer PRIVATE squirrel::squirrel)
add_test(NAME squirrel_consumer COMMAND squirrel_consumer)
