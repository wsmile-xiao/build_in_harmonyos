cmake_minimum_required(VERSION 3.15)
project(ladspa_sdk_test LANGUAGES C)

find_package(ladspa-sdk CONFIG REQUIRED)
enable_testing()

# test_minplugin: a minimal but fully valid LADSPA plugin built by the consumer
# against the installed ladspa.h. It exports ladspa_descriptor() so a host can
# dlopen() it — exactly the consumer ABI contract the SDK guarantees.
add_library(test_minplugin MODULE test_minplugin.c)
target_link_libraries(test_minplugin PRIVATE ladspa-sdk::ladspa-sdk ${CMAKE_DL_LIBS})
set_target_properties(test_minplugin PROPERTIES
    PREFIX ""
    OUTPUT_NAME "test_minplugin"
    C_VISIBILITY_PRESET hidden
    VISIBILITY_INLINES_HIDDEN ON)

# test_consumer: the actual test driver. It dlopen()s the consumer-built
# plugin AND the installed example amp.so, then asserts descriptor fields.
add_executable(test_consumer test_consumer.c)
target_link_libraries(test_consumer PRIVATE ladspa-sdk::ladspa-sdk ${CMAKE_DL_LIBS})

add_test(NAME ladspa_sdk_abi COMMAND test_consumer
    "$<TARGET_FILE:test_minplugin>"
    "$<TARGET_FILE_DIR:test_minplugin>/test_minplugin"
    "${CMAKE_CURRENT_LIST_DIR}")
