cmake_minimum_required(VERSION 3.16)
project(libdetourcrowd_test CXX)

find_package(libdetourcrowd REQUIRED CONFIG)

add_executable(libdetourcrowd_test test_detourcrowd.cpp)
target_link_libraries(libdetourcrowd_test PRIVATE libdetourcrowd::libdetourcrowd)

if(CMAKE_SYSTEM_NAME MATCHES "^(OHOS|HarmonyOS)$")
    add_executable(libdetourcrowd_ohos_test test_ohos.cpp)
    target_link_libraries(libdetourcrowd_ohos_test PRIVATE libdetourcrowd::libdetourcrowd)
endif()
