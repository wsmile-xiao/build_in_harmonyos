cmake_minimum_required(VERSION 3.15)
project(implot_test_package LANGUAGES CXX)

find_package(implot CONFIG REQUIRED)

add_executable(implot_test_package test_package.cpp)
target_link_libraries(implot_test_package PRIVATE implot::implot)
target_compile_features(implot_test_package PRIVATE cxx_std_17)
# imgui propagates ace_ndk.z/EGL/GLESv3 as system libs for its OHOS backend.
# The headless test never references them; keep them out of DT_NEEDED so the
# device loader does not pull the application-only Ace/NAPI runtime chain.
target_link_options(implot_test_package PRIVATE "LINKER:--as-needed")
