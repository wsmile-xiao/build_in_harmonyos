cmake_minimum_required(VERSION 3.22)
project(test_mts_esp LANGUAGES CXX)

find_package(mts-esp REQUIRED CONFIG)

add_library(mts_provider SHARED mock_provider.cpp)
set_target_properties(mts_provider PROPERTIES OUTPUT_NAME MTS)

add_executable(test_mts_esp test_mts_esp.cpp)
target_compile_features(test_mts_esp PRIVATE cxx_std_11)
target_link_libraries(test_mts_esp PRIVATE mts-esp::mts-esp)
add_dependencies(test_mts_esp mts_provider)

enable_testing()
foreach(test_name IN ITEMS
        client_registration
        default_frequency
        retuning_identity
        frequency_to_note
        default_scale
        note_filter
        sysex_single_note
        master_offline_safety)
    add_test(NAME ${test_name} COMMAND test_mts_esp ${test_name})
endforeach()

add_test(
    NAME ohos_dynamic_provider
    COMMAND ${CMAKE_COMMAND} -E env
        "LD_LIBRARY_PATH=$<TARGET_FILE_DIR:mts_provider>"
        $<TARGET_FILE:test_mts_esp> ohos_dynamic_provider
)
