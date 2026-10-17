cmake_minimum_required(VERSION 3.15)
project(oflib_test_package C)

find_package(oflib REQUIRED CONFIG)

add_executable(oflib_tests oflib_tests.c)
target_link_libraries(oflib_tests PRIVATE oflib::oflib)

add_executable(oflib_ohos_platform_test ohos_platform_test.c)
target_link_libraries(oflib_ohos_platform_test PRIVATE oflib::oflib)

enable_testing()
add_test(NAME oflib_uint32 COMMAND oflib_tests uint32)
add_test(NAME oflib_uint64 COMMAND oflib_tests uint64)
add_test(NAME oflib_device_tree COMMAND oflib_tests device-tree)
add_test(NAME oflib_ohos_platform COMMAND oflib_ohos_platform_test)

string(TOUPPER "${CMAKE_BUILD_TYPE}" _oflib_test_config)
set(_oflib_package_var "oflib_PACKAGE_FOLDER_${_oflib_test_config}")
set(_oflib_test_library_path "${${_oflib_package_var}}/lib")
set_tests_properties(
    oflib_uint32
    oflib_uint64
    oflib_device_tree
    oflib_ohos_platform
    PROPERTIES ENVIRONMENT "LD_LIBRARY_PATH=${_oflib_test_library_path}"
)
