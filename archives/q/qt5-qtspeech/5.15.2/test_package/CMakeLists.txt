cmake_minimum_required(VERSION 3.15)
project(test_qt5_qtspeech CXX)

# qt5-qtbase exposes its modules through the aggregate Qt5Config.cmake
# (Qt5::Core targets). qt5-qtspeech adds the Qt5::TextToSpeech target via
# its own cmake config (cmake_file_name=Qt5TextToSpeech).
find_package(Qt5 CONFIG REQUIRED)
find_package(Qt5TextToSpeech CONFIG REQUIRED)

add_executable(test_qt5_qtspeech test.cpp)
target_link_libraries(test_qt5_qtspeech PRIVATE Qt5::TextToSpeech Qt5::Core)
target_compile_features(test_qt5_qtspeech PRIVATE cxx_std_11)
if(CMAKE_SYSTEM_NAME STREQUAL "OHOS")
    target_link_options(test_qt5_qtspeech PRIVATE -stdlib=libc++)
endif()
if(CMAKE_SYSTEM_NAME STREQUAL "OHOS" AND DEFINED OHOS_CXX_RUNTIME_DIR)
    target_link_libraries(test_qt5_qtspeech PRIVATE
        "${OHOS_CXX_RUNTIME_DIR}/libc++.so"
        "${OHOS_CXX_RUNTIME_DIR}/libc++abi.a"
        "${OHOS_CXX_RUNTIME_DIR}/libunwind.a"
    )
endif()
enable_testing()
add_test(NAME test_qt5_qtspeech COMMAND $<TARGET_FILE:test_qt5_qtspeech>)
