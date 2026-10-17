cmake_minimum_required(VERSION 3.15)
project(test_kauth CXX)

find_package(Qt6 REQUIRED COMPONENTS Core Gui)
find_package(KF6Auth REQUIRED)

add_executable(test_kauth test.cpp)
target_link_libraries(test_kauth KF6::AuthCore)

# HarmonyOS-specific test asserting the OHOS platform adaptation path:
# with no Polkit and no D-Bus session bus on OHOS, kauth is built with
# KAUTH_BACKEND_NAME=FAKE, so the exact observable behavior (status() ==
# DeniedStatus, execute() failing with BackendError, no helper bound) is
# asserted instead of merely linking the library.
add_executable(test_kauth_ohos test_kauth_ohos.cpp)
target_link_libraries(test_kauth_ohos KF6::AuthCore Qt6::Core)

foreach(runtime_lib_dir IN LISTS CONAN_RUNTIME_LIB_DIRS)
    target_link_options(test_kauth PRIVATE "-Wl,-rpath,${runtime_lib_dir}")
    target_link_options(test_kauth_ohos PRIVATE "-Wl,-rpath,${runtime_lib_dir}")
endforeach()
target_link_options(test_kauth PRIVATE "-Wl,--disable-new-dtags")
target_link_options(test_kauth_ohos PRIVATE "-Wl,--disable-new-dtags")

enable_testing()
add_test(NAME test_kauth COMMAND test_kauth)
add_test(NAME test_kauth_ohos COMMAND test_kauth_ohos)
