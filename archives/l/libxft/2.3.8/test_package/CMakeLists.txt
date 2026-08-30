cmake_minimum_required(VERSION 3.15)
project(libxft_consumer C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

find_package(libxft CONFIG REQUIRED)
find_package(fontconfig CONFIG REQUIRED)

add_executable(libxft_api_surface api_surface.c)
target_compile_options(libxft_api_surface PRIVATE -Wall -Wextra -Werror)
target_link_libraries(libxft_api_surface PRIVATE libxft::libxft)

add_executable(libxft_name_contract name_contract.c)
target_compile_options(libxft_name_contract PRIVATE -Wall -Wextra -Werror)
target_link_libraries(
    libxft_name_contract
    PRIVATE
        libxft::libxft
        fontconfig::fontconfig
)

#
# The loader contract resolves libXft exclusively through dlopen, so it takes
# the public headers from the imported target without linking the library.
#
add_executable(libxft_soname_contract soname_contract.c)
target_compile_options(libxft_soname_contract PRIVATE -Wall -Wextra -Werror)
target_include_directories(
    libxft_soname_contract
    PRIVATE
        $<TARGET_PROPERTY:libxft::libxft,INTERFACE_INCLUDE_DIRECTORIES>
)
target_link_libraries(libxft_soname_contract PRIVATE fontconfig::fontconfig)

if(CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS")
    if(NOT DEFINED LIBXFT_TEST_RUNTIME_PATH OR
       NOT IS_DIRECTORY "${LIBXFT_TEST_RUNTIME_PATH}")
        message(FATAL_ERROR "LIBXFT_TEST_RUNTIME_PATH is missing")
    endif()
    foreach(test_target IN ITEMS
            libxft_api_surface
            libxft_name_contract
            libxft_soname_contract)
        target_link_options(
            ${test_target}
            PRIVATE
                "-Wl,--disable-new-dtags"
                "-Wl,-rpath,${LIBXFT_TEST_RUNTIME_PATH}"
        )
    endforeach()
endif()
