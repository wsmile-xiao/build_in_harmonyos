cmake_minimum_required(VERSION 3.16)
project(test_luksmeta C)

find_package(luksmeta CONFIG REQUIRED)

add_executable(test_api test_api.c)
target_link_libraries(test_api PRIVATE luksmeta::luksmeta)

add_executable(test_ohos test_ohos.c)
target_link_libraries(test_ohos PRIVATE luksmeta::luksmeta)

set_target_properties(test_api test_ohos PROPERTIES
    C_STANDARD 99
    C_STANDARD_REQUIRED ON
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin"
)
