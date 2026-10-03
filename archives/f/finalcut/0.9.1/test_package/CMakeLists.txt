cmake_minimum_required(VERSION 3.15)
project(test_finalcut LANGUAGES CXX)

find_package(finalcut REQUIRED)

add_executable(test_finalcut test_finalcut.cpp)
target_link_libraries(test_finalcut PRIVATE finalcut::finalcut)

enable_testing()
add_test(NAME test_finalcut COMMAND test_finalcut)

if(CMAKE_SYSTEM_NAME MATCHES "^(OHOS|HarmonyOS)$")
    add_executable(test_ohos_unicode test_ohos_unicode.cpp)
    target_link_libraries(test_ohos_unicode PRIVATE finalcut::finalcut)
    add_test(NAME test_ohos_unicode COMMAND test_ohos_unicode)
    set_tests_properties(test_ohos_unicode PROPERTIES TIMEOUT 20)
endif()
