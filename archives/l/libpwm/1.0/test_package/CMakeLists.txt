cmake_minimum_required(VERSION 3.15)
project(libpwm_consumer C)

enable_testing()

find_package(libpwm CONFIG REQUIRED)

add_executable(libpwm_consumer test_libpwm.c)
target_link_libraries(libpwm_consumer PRIVATE libpwm::libpwm)

add_test(NAME consumer_assertions COMMAND libpwm_consumer)
