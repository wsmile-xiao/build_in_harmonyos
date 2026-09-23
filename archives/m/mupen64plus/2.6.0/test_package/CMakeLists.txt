cmake_minimum_required(VERSION 3.15)
project(test_mupen64plus C)

find_package(mupen64plus REQUIRED)

add_executable(test_mupen64plus test_mupen64plus.c)
target_link_libraries(test_mupen64plus PRIVATE mupen64plus::mupen64plus)

# allow running from any cwd: core writes a config file into ConfigPath
set(TEST_WORK_DIR "${CMAKE_CURRENT_BINARY_DIR}/m64p-work")
file(MAKE_DIRECTORY "${TEST_WORK_DIR}")
target_compile_definitions(test_mupen64plus PRIVATE TEST_WORK_DIR="${TEST_WORK_DIR}")
