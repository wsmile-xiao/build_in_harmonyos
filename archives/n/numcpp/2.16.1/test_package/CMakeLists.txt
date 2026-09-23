cmake_minimum_required(VERSION 3.15)
project(test_numcpp CXX)

# Find NumCpp through the Conan-generated CMakeDeps config
# (cmake_file_name = "NumCpp", target NumCpp::NumCpp as exported upstream).
find_package(NumCpp REQUIRED)

add_executable(test_numcpp test.cpp)
target_link_libraries(test_numcpp PRIVATE NumCpp::NumCpp)

enable_testing()
add_test(NAME test_numcpp COMMAND test_numcpp)
