cmake_minimum_required(VERSION 3.15)
project(libdmx_consumer C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS ON)

# dmxext.h is not self-contained (it only pulls dmx.h); consumers must
# include Xlib.h first.  The libx11/6.4.0 dependency supplies Xlib.h,
# libxext/6.4.0.1 supplies the Xext runtime, and xorgproto/2025.1
# supplies dmxproto.h.
find_package(libdmx CONFIG REQUIRED)

# The OHOS clang wrapper injects -Wl,--code-sign into compile lines, which
# is an unused linker input when compiling .c files; keep -Werror strictness
# for real diagnostics without failing on the injection.
set(OHOS_COMPILE_FLAGS -Wall -Wextra -Werror)
if(CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS")
    list(APPEND OHOS_COMPILE_FLAGS -Wno-error=unused-command-line-argument)
endif()

add_executable(libdmx_api_surface api_surface.c)
target_compile_options(libdmx_api_surface PRIVATE ${OHOS_COMPILE_FLAGS})
target_link_libraries(libdmx_api_surface PRIVATE libdmx::libdmx)

add_executable(libdmx_version_contract version_contract.c)
target_compile_options(libdmx_version_contract PRIVATE ${OHOS_COMPILE_FLAGS})
target_link_libraries(libdmx_version_contract PRIVATE libdmx::libdmx)

add_executable(libdmx_ohos_abi_contract ohos_abi_contract.c)
target_compile_options(libdmx_ohos_abi_contract PRIVATE ${OHOS_COMPILE_FLAGS})
target_link_libraries(libdmx_ohos_abi_contract PRIVATE libdmx::libdmx)
