cmake_minimum_required(VERSION 3.16)
project(test_scintilla CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find the scintilla package (provided by Conan CMakeDeps)
find_package(scintilla REQUIRED)

add_executable(test_scintilla test.cpp)

# Link against the scintilla library — this also provides include dirs
target_link_libraries(test_scintilla PRIVATE scintilla::scintilla)

# OHOS SDK paths (for hilog, native_drawing, etc.)
set(OHOS_SDK "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native")
target_include_directories(test_scintilla PRIVATE
    ${OHOS_SDK}/sysroot/usr/include
)
target_link_directories(test_scintilla PRIVATE
    ${OHOS_SDK}/sysroot/usr/lib/aarch64-linux-ohos
)
