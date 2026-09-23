cmake_minimum_required(VERSION 3.15)
project(test_taocpp_operators LANGUAGES CXX)

# Find the package via Conan-generated CMakeDeps
find_package(taocpp-operators CONFIG REQUIRED)

add_executable(test_taocpp_operators test.cpp)
target_link_libraries(test_taocpp_operators PRIVATE taocpp-operators::taocpp-operators)
set_target_properties(test_taocpp_operators PROPERTIES
    CXX_STANDARD 11
    CXX_STANDARD_REQUIRED ON
    CXX_EXTENSIONS OFF
)

enable_testing()
add_test(NAME test_taocpp_operators COMMAND test_taocpp_operators)
