cmake_minimum_required(VERSION 3.15)
project(test_clearsilver C)

find_package(clearsilver REQUIRED)

add_executable(test_clearsilver test.c)
target_link_libraries(test_clearsilver PRIVATE clearsilver::clearsilver)
# Headers are in include/ClearSilver – already in Conan package include path
target_include_directories(test_clearsilver PRIVATE ${clearsilver_INCLUDE_DIRS})

enable_testing()
add_test(NAME test_clearsilver COMMAND test_clearsilver)
