cmake_minimum_required(VERSION 3.15)
project(test_json_h LANGUAGES C)

find_package(json.h CONFIG REQUIRED)

add_executable(test_json_h test_package.c)
target_link_libraries(test_json_h PRIVATE json.h)
set_target_properties(test_json_h PROPERTIES
    C_STANDARD 99
    C_STANDARD_REQUIRED ON
)

enable_testing()
add_test(NAME test_json_h COMMAND test_json_h)
