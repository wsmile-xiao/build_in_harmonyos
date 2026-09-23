cmake_minimum_required(VERSION 3.15)
project(test_mpfrcx LANGUAGES C CXX)

find_package(mpfrcx REQUIRED)
find_package(mpc REQUIRED)
find_package(mpfr REQUIRED)
find_package(gmp REQUIRED)

add_executable(test_mpfrcx test.c)
target_include_directories(test_mpfrcx PRIVATE ${MPFRCX_TEST_DEP_INCLUDE_DIRS})
target_link_libraries(test_mpfrcx mpfrcx::mpfrcx mpc::mpc mpfr::mpfr gmp::gmp)

add_executable(ohos_special_test ohos_special_test.cpp)
target_include_directories(ohos_special_test PRIVATE ${MPFRCX_TEST_DEP_INCLUDE_DIRS})
target_compile_definitions(ohos_special_test PRIVATE
    MPFRCX_LIB_DIR="${MPFRCX_LIB_DIR}")
target_link_libraries(ohos_special_test mpfrcx::mpfrcx mpc::mpc mpfr::mpfr gmp::gmp)

enable_testing()
add_test(NAME test_mpfrcx COMMAND test_mpfrcx)
add_test(NAME ohos_special_test COMMAND ohos_special_test)
