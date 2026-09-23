cmake_minimum_required(VERSION 3.15)
project(test_accountsservice C)

find_package(accountsservice CONFIG REQUIRED)

add_executable(test_accountsservice test_accountsservice.c)
target_link_libraries(test_accountsservice PRIVATE accountsservice::accountsservice)

enable_testing()
add_test(NAME test_accountsservice COMMAND test_accountsservice)
