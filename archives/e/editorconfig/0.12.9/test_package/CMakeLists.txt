cmake_minimum_required(VERSION 3.16)
project(test_editorconfig C)

find_package(EditorConfig REQUIRED CONFIG)

add_executable(test_editorconfig test.c)
target_link_libraries(test_editorconfig PRIVATE EditorConfig::EditorConfig)

add_executable(test_editorconfig_unit unit_test.c)
target_link_libraries(test_editorconfig_unit PRIVATE EditorConfig::EditorConfig)

enable_testing()
add_test(NAME editorconfig_consumer COMMAND test_editorconfig)
add_test(NAME editorconfig_unit_version COMMAND test_editorconfig_unit version)
add_test(
    NAME editorconfig_unit_handle_version
    COMMAND test_editorconfig_unit handle_version
)
add_test(
    NAME editorconfig_unit_conf_filename
    COMMAND test_editorconfig_unit conf_filename
)
add_test(
    NAME editorconfig_unit_relative_path_error
    COMMAND test_editorconfig_unit relative_path_error
)
