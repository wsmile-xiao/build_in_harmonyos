cmake_minimum_required(VERSION 3.16)
project(test_ecm C)

find_package(ECM REQUIRED CONFIG)

include(ECMSetupVersion)
ecm_setup_version("6.19.0" VARIABLE_PREFIX ECM_TEST)

add_executable(test_ecm src/test_ecm.c)

enable_testing()
add_test(NAME ecm_loaded COMMAND test_ecm)
