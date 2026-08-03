cmake_minimum_required(VERSION 3.15)
# OHOS SDK clang 15 ships libc++ only (no libstdc++); default OHOS conan
# profile sets compiler.libcxx=libstdc++11 which breaks CMake's CXX compiler
# try-compile. Force libc++ before project() so the try-compile passes.
set(CMAKE_CXX_FLAGS "-stdlib=libc++ -D_LIBCPP_ENABLE_EXPERIMENTAL")
project(test_openal CXX)

# Use the CMakeDeps-generated package (openal-soft) instead of the upstream
# OpenALConfig.cmake installed inside the package, so include dirs resolve to
# the Conan package layout.
find_package(openal-soft REQUIRED)

add_executable(test_openal test_openal.cpp)
target_link_libraries(test_openal PRIVATE OpenAL::OpenAL)
