cmake_minimum_required(VERSION 3.15)
project(test_oatpp CXX)

# Find the package via Conan-generated CMakeDeps
find_package(oatpp REQUIRED)

add_executable(test_oatpp test_oatpp.cpp)
target_link_libraries(test_oatpp oatpp::oatpp)
target_compile_features(test_oatpp PRIVATE cxx_std_17)

enable_testing()
add_test(NAME test_oatpp COMMAND test_oatpp)
