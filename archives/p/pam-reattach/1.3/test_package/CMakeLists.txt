cmake_minimum_required(VERSION 3.15)
project(test_pam_reattach C)

find_package(reattach REQUIRED)

add_executable(test_pam_reattach src/main.c)
target_link_libraries(test_pam_reattach reattach::reattach)

enable_testing()
add_test(NAME test_pam_reattach COMMAND test_pam_reattach)
