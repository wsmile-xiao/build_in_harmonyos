cmake_minimum_required(VERSION 3.15)
project(test_msquic C)

find_package(msquic REQUIRED CONFIG)

add_executable(test_msquic test_msquic.c)
target_link_libraries(test_msquic PRIVATE msquic::msquic)

enable_testing()
add_test(NAME msquic_api_open COMMAND test_msquic open)
add_test(NAME msquic_registration COMMAND test_msquic registration)
