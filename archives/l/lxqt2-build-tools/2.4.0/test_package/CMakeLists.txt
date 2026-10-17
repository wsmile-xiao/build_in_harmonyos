cmake_minimum_required(VERSION 3.18)
project(test_lxqt2-build-tools C)

# R34: actually use the package — its config.cmake appends the module dirs to
# CMAKE_MODULE_PATH so downstream projects can include its helper modules.
find_package(lxqt2-build-tools REQUIRED)

# Use the lxqt_create_pkgconfig_file() helper shipped by the package to
# generate a pkg-config file in the build tree.
# Note: include WITHOUT the .cmake suffix — CMake's include() treats a name
# ending in .cmake as a plain file and does not search CMAKE_MODULE_PATH.
include(LXQtCreatePkgConfigFile)
lxqt_create_pkgconfig_file(
    PACKAGE_NAME lxqt2-test
    VERSION 2.4.0
    DESCRIPTIVE_NAME "lxqt2-test"
    DESCRIPTION "lxqt2-build-tools functional test"
    LIBS lxqt2-test
)

add_executable(check_pc check_pc.c)
target_link_libraries(check_pc PRIVATE)

enable_testing()
add_test(NAME check_pc COMMAND check_pc "${CMAKE_CURRENT_BINARY_DIR}/lxqt2-test.pc")
