cmake_minimum_required(VERSION 3.15)
project(test_airspyhf C)

# Find the package via Conan-generated CMakeDeps
find_package(airspyhf REQUIRED)

add_executable(test_airspyhf test.c)
target_link_libraries(test_airspyhf airspyhf::airspyhf)

enable_testing()
add_test(NAME test_airspyhf COMMAND test_airspyhf)
