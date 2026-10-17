cmake_minimum_required(VERSION 3.15)
project(libsm_consumer C)

find_package(libsm CONFIG REQUIRED)

add_executable(libsm_api_contract test.c)
target_link_libraries(libsm_api_contract PRIVATE libsm::libsm)

enable_testing()
add_test(NAME libsm_api_contract COMMAND libsm_api_contract)
