cmake_minimum_required(VERSION 3.16)
project(nowplaying-cli VERSION 2.1.0.1 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_executable(nowplaying-cli
    src/main.cpp
    src/avsession_helper.cpp
    src/metadata.cpp
)

target_include_directories(nowplaying-cli PRIVATE src)

# ---------------------------------------------------------------------------
# Resolve the OHOS native SDK sysroot.
#
# Two toolchain flows are supported:
#   1) Direct cmake with the official ohos.toolchain.cmake → CMAKE_SYSROOT is
#      already set to <SDK>/ohos/native/sysroot.
#   2) Conan (CMakeToolchain generated from the ohos-aarch64 profile) → the
#      compiler is <HNP>/bin/clang (a symlink into the SDK llvm tree), and
#      CMAKE_SYSROOT is NOT defined. Derive the sysroot from the real
#      compiler path: <...>/ohos/native/llvm/bin/clang → ../../sysroot.
# ---------------------------------------------------------------------------
if(NOT CMAKE_SYSROOT)
    get_filename_component(_ohos_cxx_real "${CMAKE_CXX_COMPILER}" REALPATH)
    get_filename_component(_ohos_cxx_bin "${_ohos_cxx_real}" DIRECTORY)
    get_filename_component(_ohos_llvm_root "${_ohos_cxx_bin}" DIRECTORY)
    if(EXISTS "${_ohos_llvm_root}/sysroot")
        set(CMAKE_SYSROOT "${_ohos_llvm_root}/sysroot")
    else()
        # fallback: one more level up (SDK-native layout)
        get_filename_component(_ohos_sdk_root "${_ohos_llvm_root}" DIRECTORY)
        if(EXISTS "${_ohos_sdk_root}/sysroot")
            set(CMAKE_SYSROOT "${_ohos_sdk_root}/sysroot")
        endif()
    endif()
endif()

# OpenHarmony native AVSessionKit headers live under
# <sysroot>/usr/include/multimedia/av_session. The source uses fully-qualified
# include paths, but keep the -I for robustness across toolchains.
if(CMAKE_SYSROOT)
    target_include_directories(nowplaying-cli PRIVATE
        ${CMAKE_SYSROOT}/usr/include/multimedia/av_session
        ${CMAKE_SYSROOT}/usr/include)
    # Link against the OHOS native AVSession provider library
    # (libohavsession.so in <sysroot>/usr/lib/aarch64-linux-ohos).
    find_library(OH_AVSESSION_LIBRARY
        NAMES ohavsession
        PATHS ${CMAKE_SYSROOT}/usr/lib/aarch64-linux-ohos
        NO_DEFAULT_PATH)
    if(OH_AVSESSION_LIBRARY)
        target_link_libraries(nowplaying-cli PRIVATE ${OH_AVSESSION_LIBRARY})
    else()
        message(WARNING "libohavsession.so not found; linking by name")
        target_link_libraries(nowplaying-cli PRIVATE ohavsession)
    endif()
else()
    # No sysroot resolved (foreign toolchain) — still try by name so that a
    # host build with the SDK on the default search path can work.
    target_link_libraries(nowplaying-cli PRIVATE ohavsession)
endif()

install(TARGETS nowplaying-cli RUNTIME DESTINATION bin)