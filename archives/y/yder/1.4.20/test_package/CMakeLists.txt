cmake_minimum_required(VERSION 3.10)
project(test_yder C)

find_package(Yder REQUIRED)

add_executable(test_yder test_yder.c)
target_link_libraries(test_yder PRIVATE Yder::Yder)
