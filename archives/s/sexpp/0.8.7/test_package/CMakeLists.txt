cmake_minimum_required(VERSION 3.15)
project(test_sexpp CXX)

# Resolve the package through Conan-generated CMakeDeps config files
find_package(sexpp REQUIRED)

add_executable(test_sexpp test.cpp)
target_link_libraries(test_sexpp PRIVATE sexpp::sexpp)
target_compile_features(test_sexpp PRIVATE cxx_std_11)

enable_testing()
add_test(NAME test_sexpp COMMAND test_sexpp)
