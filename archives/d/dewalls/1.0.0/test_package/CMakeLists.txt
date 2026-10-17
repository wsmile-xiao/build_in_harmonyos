cmake_minimum_required(VERSION 3.16)
project(test_dewalls LANGUAGES CXX)

find_package(dewalls REQUIRED)
find_package(Qt5 5.15 REQUIRED COMPONENTS Core)

add_executable(test_dewalls test_dewalls.cpp)
target_compile_features(test_dewalls PRIVATE cxx_std_11)
target_link_libraries(test_dewalls PRIVATE dewalls::dewalls Qt5::Core)

enable_testing()
add_test(NAME test_dewalls COMMAND test_dewalls)