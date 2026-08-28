cmake_minimum_required(VERSION 3.15)
project(test_astlib CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find the packages via Conan-generated CMakeDeps
find_package(astlib REQUIRED)
find_package(poco REQUIRED)

add_executable(test_astlib test_astlib.cpp)
target_link_libraries(test_astlib astlib::astlib poco::poco)
# Add Poco include dirs explicitly (passed via CMakeToolchain variable)
if(POCO_INCLUDE_DIRS)
    target_include_directories(test_astlib PRIVATE ${POCO_INCLUDE_DIRS})
endif()

enable_testing()
add_test(NAME test_astlib COMMAND test_astlib)
