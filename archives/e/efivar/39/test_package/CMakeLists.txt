cmake_minimum_required(VERSION 3.15)
project(efivar_test LANGUAGES C)

find_package(efivar CONFIG REQUIRED)

add_executable(test_efivar test_efivar.c)
target_link_libraries(test_efivar PRIVATE efivar::efivar)
