cmake_minimum_required(VERSION 3.16)
project(test_kdecoration3 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(KDecoration3 REQUIRED)

add_executable(test_kdecoration3 test.cpp)
target_link_libraries(test_kdecoration3 PRIVATE KDecoration3::KDecoration)

enable_testing()
add_test(NAME test_kdecoration3 COMMAND test_kdecoration3)

# This test covers the HarmonyOS-only loader/ABI path introduced by the
# package adaptation. Keep it out of native host builds so its platform
# assertions cannot be accidentally reported as a generic consumer test.
if(KDECORATION3_OHOS OR CMAKE_SYSTEM_NAME MATCHES "^(OHOS|HarmonyOS)$")
    add_executable(test_kdecoration3_ohos test_ohos.cpp)
    target_link_libraries(
        test_kdecoration3_ohos
        PRIVATE KDecoration3::KDecoration ${CMAKE_DL_LIBS}
    )
    add_test(NAME test_kdecoration3_ohos COMMAND test_kdecoration3_ohos)
endif()
