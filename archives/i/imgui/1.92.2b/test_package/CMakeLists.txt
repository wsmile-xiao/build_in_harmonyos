cmake_minimum_required(VERSION 3.15)
project(test_imgui LANGUAGES CXX)

find_package(imgui REQUIRED CONFIG)

if(CMAKE_SYSTEM_NAME MATCHES "OHOS|HarmonyOS")
    add_executable(test_imgui_core test_imgui.cpp test_imgui_generic.cpp)
    target_link_libraries(test_imgui_core PRIVATE imgui::imgui)
    target_link_options(test_imgui_core PRIVATE "-Wl,--as-needed")
    target_compile_features(test_imgui_core PRIVATE cxx_std_11)

    add_executable(test_imgui_ohos_backend test_imgui.cpp test_imgui_ohos.cpp)
    target_link_libraries(test_imgui_ohos_backend PRIVATE imgui::imgui)
    target_compile_features(test_imgui_ohos_backend PRIVATE cxx_std_11)
else()
    add_executable(test_imgui test_imgui.cpp test_imgui_generic.cpp)
    target_link_libraries(test_imgui PRIVATE imgui::imgui)
    target_compile_features(test_imgui PRIVATE cxx_std_11)
endif()
