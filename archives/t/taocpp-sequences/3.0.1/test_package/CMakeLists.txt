cmake_minimum_required(VERSION 3.15)
project(test_taocpp_sequences LANGUAGES CXX)

# Find the package via Conan-generated CMakeDeps
find_package(taocpp-sequences CONFIG REQUIRED)

add_executable(test_taocpp_sequences test.cpp)
target_link_libraries(test_taocpp_sequences PRIVATE taocpp::sequences)
set_target_properties(test_taocpp_sequences PROPERTIES
    CXX_STANDARD 11
    CXX_STANDARD_REQUIRED ON
    CXX_EXTENSIONS OFF
)

enable_testing()
add_test(NAME test_taocpp_sequences COMMAND test_taocpp_sequences)
