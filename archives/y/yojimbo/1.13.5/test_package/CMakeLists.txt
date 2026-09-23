cmake_minimum_required(VERSION 3.16)
project(test_yojimbo CXX)

find_package(Yojimbo CONFIG REQUIRED)

add_executable(test_yojimbo test_package.cpp)
target_link_libraries(test_yojimbo PRIVATE Yojimbo::yojimbo)
target_compile_features(test_yojimbo PRIVATE cxx_std_11)

enable_testing()
add_test(NAME test_yojimbo COMMAND test_yojimbo)
