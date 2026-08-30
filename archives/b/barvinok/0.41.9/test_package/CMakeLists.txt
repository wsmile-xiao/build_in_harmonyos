cmake_minimum_required(VERSION 3.15)
project(test_barvinok C)

find_package(barvinok CONFIG REQUIRED)

add_executable(test_barvinok test.c)
target_link_libraries(test_barvinok PRIVATE barvinok::barvinok)

enable_testing()
add_test(NAME test_barvinok COMMAND test_barvinok)

# On OHOS the recipe prepopulates this directory with freshly signed copies
# of the non-system shared library closure (E135); the loader only maps
# shared libraries with a valid signature there.
if(DEFINED TEST_PACKAGE_LD_LIBRARY_PATH)
  set_tests_properties(test_barvinok PROPERTIES
    ENVIRONMENT "LD_LIBRARY_PATH=${TEST_PACKAGE_LD_LIBRARY_PATH}:$ENV{LD_LIBRARY_PATH}")
endif()
