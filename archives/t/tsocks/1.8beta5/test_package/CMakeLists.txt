cmake_minimum_required(VERSION 3.15)
project(test_tsocks C)

find_package(tsocks REQUIRED)

add_executable(test_tsocks test.c)
target_link_libraries(test_tsocks PRIVATE ${DL_LIBRARY} tsocks::tsocks)

enable_testing()
add_test(NAME tsocks_loads COMMAND test_tsocks)
