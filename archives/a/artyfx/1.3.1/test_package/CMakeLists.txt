cmake_minimum_required(VERSION 3.15)
project(test_artyfx C)

# This test uses dlopen to load the LV2 plugin .so and verify
# it exports the lv2_descriptor entry point symbol.
add_executable(test_artyfx test.c)
target_link_libraries(test_artyfx ${CMAKE_DL_LIBS})

enable_testing()
add_test(NAME test_artyfx COMMAND test_artyfx
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR})
