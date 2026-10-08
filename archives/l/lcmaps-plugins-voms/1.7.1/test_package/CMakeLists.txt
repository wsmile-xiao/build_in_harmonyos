cmake_minimum_required(VERSION 3.15)
project(test_lcmaps_plugins_voms C)

set(TEST_ROOT "" CACHE PATH "package root of the tested lcmaps-plugins-voms")

find_package(lcmaps REQUIRED CONFIG)

add_executable(test_lcmaps_plugins_voms test.c)
target_compile_definitions(test_lcmaps_plugins_voms PRIVATE
    TEST_ROOT="${TEST_ROOT}")
# Link the LCMAPS engine statically and export its symbols (-rdynamic):
# that is exactly how a LCMAPS consumer embeds the evaluation engine, and it
# puts lcmaps_log & friends into the global namespace where the plugins'
# relocations resolve at dlopen() time. The framework's .so does not export
# these internal symbols, so linking the shared variant cannot work.
target_link_libraries(test_lcmaps_plugins_voms PRIVATE
    -Wl,--whole-archive
    ${lcmaps_PACKAGE_FOLDER_RELEASE}/lib/liblcmaps_without_gsi.a
    -Wl,--no-whole-archive)
target_link_options(test_lcmaps_plugins_voms PRIVATE -rdynamic)

# End-to-end consumer test: a full LCMAPS evaluation round trip driven
# through the framework API (lcmaps_init -> policy -> ban_fqan ->
# voms_localaccount -> returned account -> lcmaps_term), see test_e2e.c.
add_executable(test_lcmaps_plugins_voms_e2e test_e2e.c)
target_compile_definitions(test_lcmaps_plugins_voms_e2e PRIVATE
    TEST_ROOT="${TEST_ROOT}")
target_include_directories(test_lcmaps_plugins_voms_e2e PRIVATE
    ${lcmaps_PACKAGE_FOLDER_RELEASE}/include)
target_link_libraries(test_lcmaps_plugins_voms_e2e PRIVATE
    -Wl,--whole-archive
    ${lcmaps_PACKAGE_FOLDER_RELEASE}/lib/liblcmaps_without_gsi.a
    -Wl,--no-whole-archive)
target_link_options(test_lcmaps_plugins_voms_e2e PRIVATE -rdynamic)
