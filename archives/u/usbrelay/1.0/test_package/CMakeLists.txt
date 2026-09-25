cmake_minimum_required(VERSION 3.15)
project(test_usbrelay C)

find_package(usbrelay REQUIRED)

add_executable(test_usbrelay test.c)
target_link_libraries(test_usbrelay PRIVATE usbrelay::usbrelay)

enable_testing()
add_test(NAME consumer_assertions COMMAND test_usbrelay)
