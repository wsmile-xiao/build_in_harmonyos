cmake_minimum_required(VERSION 3.15)
project(test_package C)

find_package(evince CONFIG REQUIRED)
find_package(glib CONFIG REQUIRED)

add_executable(test_evince test_evince.c)
target_link_libraries(test_evince PRIVATE evince::evince)

enable_testing()
add_test(NAME evince_abi COMMAND test_evince)
