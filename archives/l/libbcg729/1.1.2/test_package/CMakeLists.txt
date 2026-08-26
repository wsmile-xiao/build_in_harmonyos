cmake_minimum_required(VERSION 3.15)
project(test_libbcg729 C)

find_package(libbcg729 REQUIRED)

add_executable(test_libbcg729 test.c)
target_link_libraries(test_libbcg729 libbcg729::bcg729)

enable_testing()
add_test(NAME test_libbcg729 COMMAND test_libbcg729)
