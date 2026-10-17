cmake_minimum_required(VERSION 3.15)
project(test_libint LANGUAGES CXX)

find_package(libint REQUIRED)
find_package(Eigen3 REQUIRED)

add_executable(test_libint test_package.cpp)
target_compile_features(test_libint PRIVATE cxx_std_11)
target_link_libraries(test_libint PRIVATE libint::libint Eigen3::Eigen)

enable_testing()
add_test(NAME test_libint COMMAND test_libint)
