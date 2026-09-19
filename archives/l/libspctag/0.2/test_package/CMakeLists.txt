cmake_minimum_required(VERSION 3.15)
project(test_libspctag C)

find_package(libspctag REQUIRED CONFIG)

add_executable(test_libspctag test_libspctag.c)
target_link_libraries(test_libspctag PRIVATE libspctag::spctag)

include(CTest)
if(BUILD_TESTING)
    add_test(NAME libspctag_consumer COMMAND test_libspctag)
endif()

if(CMAKE_SYSTEM_NAME MATCHES "OHOS|HarmonyOS")
    add_executable(test_libspctag_ohos test_ohos.c)
    target_link_libraries(test_libspctag_ohos PRIVATE libspctag::spctag)
    if(BUILD_TESTING)
        add_test(NAME libspctag_ohos COMMAND test_libspctag_ohos)
        set_tests_properties(libspctag_ohos PROPERTIES LABELS "HarmonyOS")
    endif()
endif()
