cmake_minimum_required(VERSION 3.15)
project(test_qtspeech_opensource_src CXX)

find_package(Qt5 CONFIG REQUIRED)
find_package(Qt5TextToSpeech CONFIG REQUIRED)

add_executable(test_qtspeech_opensource_src test_qtspeech.cpp)
target_link_libraries(test_qtspeech_opensource_src PRIVATE Qt5::Core Qt5::TextToSpeech)

if(CMAKE_SYSTEM_NAME STREQUAL "OHOS")
    target_link_options(test_qtspeech_opensource_src PRIVATE -stdlib=libc++)
endif()
if(CMAKE_SYSTEM_NAME STREQUAL "OHOS" AND DEFINED OHOS_CXX_RUNTIME_DIR)
    target_link_libraries(test_qtspeech_opensource_src PRIVATE
        "${OHOS_CXX_RUNTIME_DIR}/libc++.so"
        "${OHOS_CXX_RUNTIME_DIR}/libc++abi.a"
        "${OHOS_CXX_RUNTIME_DIR}/libunwind.a"
    )
endif()

enable_testing()
add_test(NAME test_qtspeech_opensource_src COMMAND $<TARGET_FILE:test_qtspeech_opensource_src>)
