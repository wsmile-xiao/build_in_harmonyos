cmake_minimum_required(VERSION 3.15)
project(test_trompeloeil CXX)

find_package(trompeloeil CONFIG REQUIRED)
find_package(Catch2 3 CONFIG REQUIRED)

add_executable(test_trompeloeil test_trompeloeil.cpp)
target_compile_features(test_trompeloeil PRIVATE cxx_std_14)
target_link_libraries(test_trompeloeil PRIVATE trompeloeil::trompeloeil Catch2::Catch2WithMain)

enable_testing()
add_test(NAME test_trompeloeil COMMAND test_trompeloeil)
