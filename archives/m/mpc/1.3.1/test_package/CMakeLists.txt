cmake_minimum_required(VERSION 3.15)
project(test_mpc C)

find_package(mpc REQUIRED)
find_package(mpfr REQUIRED)
find_package(gmp REQUIRED)

add_executable(test_mpc test.c)
target_include_directories(test_mpc PRIVATE ${MPC_TEST_DEP_INCLUDE_DIRS})
target_link_libraries(test_mpc mpc::mpc mpfr::mpfr gmp::gmp)

enable_testing()
add_test(NAME test_mpc COMMAND test_mpc)
