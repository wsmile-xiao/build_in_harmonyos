cmake_minimum_required(VERSION 3.15)
project(test_lunarlog CXX)

# Find the package via Conan-generated CMakeDeps (cmake_file_name=LunarLog)
find_package(LunarLog REQUIRED)

add_executable(test_lunarlog test.cpp)
target_link_libraries(test_lunarlog PRIVATE LunarLog::LunarLog)

enable_testing()
add_test(NAME test_lunarlog COMMAND test_lunarlog)
