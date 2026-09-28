cmake_minimum_required(VERSION 3.15)
project(test_lcmaps C)

add_executable(test_lcmaps test.c)
target_include_directories(test_lcmaps PRIVATE ${LCMAPS_TEST_INCDIR})
target_compile_definitions(test_lcmaps
    PRIVATE LCMAPS_TEST_LIBDIR="${LCMAPS_TEST_ROOT}/lib")
# The test loads liblcmaps_without_gsi via dlopen() and does not link against it.
target_link_libraries(test_lcmaps ${CMAKE_DL_LIBS})

enable_testing()
add_test(NAME test_lcmaps COMMAND test_lcmaps)
