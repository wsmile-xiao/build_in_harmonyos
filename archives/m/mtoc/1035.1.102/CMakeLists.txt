cmake_minimum_required(VERSION 3.16)

project(mtoc VERSION 1035.1.102 LANGUAGES C)

include(GNUInstallDirs)
include(CheckSymbolExists)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS ON)

set(MTOC_LIBSTUFF_SOURCES
    libstuff/apple_version.c
    libstuff/fatals.c
    libstuff/diagnostics.c
    libstuff/coff_bytesex.c
    libstuff/ofile.c
    libstuff/allocate.c
    libstuff/swap_headers.c
    libstuff/get_arch_from_host.c
    libstuff/bytesex.c
    libstuff/breakout.c
    libstuff/errors.c
    libstuff/port.c
    libstuff/reloc.c
    libstuff/checkout.c
    libstuff/write64.c
    libstuff/rnd.c
    libstuff/ofile_error.c
    libstuff/print.c
    libstuff/set_arch_flag_name.c
    libstuff/get_toc_byte_sex.c
    libstuff/arch.c
    libstuff/crc32.c
    libstuff/fatal_arch.c
)

add_executable(mtoc
    efitools/mtoc.c
    ${MTOC_LIBSTUFF_SOURCES}
)

set(MTOC_SAVED_CMAKE_REQUIRED_DEFINITIONS "${CMAKE_REQUIRED_DEFINITIONS}")
list(APPEND CMAKE_REQUIRED_DEFINITIONS -D_GNU_SOURCE)
check_symbol_exists(bcmp "strings.h" HAVE_BCMP)
check_symbol_exists(bzero "strings.h" HAVE_BZERO)
check_symbol_exists(bcopy "strings.h" HAVE_BCOPY)
check_symbol_exists(index "strings.h" HAVE_INDEX)
check_symbol_exists(rindex "strings.h" HAVE_RINDEX)
set(CMAKE_REQUIRED_DEFINITIONS "${MTOC_SAVED_CMAKE_REQUIRED_DEFINITIONS}")
unset(MTOC_SAVED_CMAKE_REQUIRED_DEFINITIONS)

target_include_directories(mtoc PRIVATE
    "${CMAKE_CURRENT_SOURCE_DIR}/include"
    "${CMAKE_CURRENT_SOURCE_DIR}/include/foreign"
    "${CMAKE_CURRENT_SOURCE_DIR}/include/stuff"
    "${CMAKE_CURRENT_SOURCE_DIR}/libstuff"
)

target_compile_options(mtoc PRIVATE
    -include
    stuff/port.h
)

target_compile_definitions(mtoc PRIVATE
    _GNU_SOURCE
    __private_extern__=
    __DARWIN_UNIX03
    _DARWIN_C_SOURCE
    __LITTLE_ENDIAN__=1
    MAP_RESILIENT_CODESIGN=0
    CPU_TYPE_RISCV32=24
    __STDC_LIMIT_MACROS
    __STDC_CONSTANT_MACROS
)

foreach(MTOC_STRING_SYMBOL IN ITEMS BCMP BZERO BCOPY INDEX RINDEX)
    if(HAVE_${MTOC_STRING_SYMBOL})
        target_compile_definitions(mtoc PRIVATE HAVE_${MTOC_STRING_SYMBOL}=1)
    endif()
endforeach()

if(MTOC_TARGET_PROCESSOR)
    set(MTOC_SYSTEM_PROCESSOR "${MTOC_TARGET_PROCESSOR}")
else()
    set(MTOC_SYSTEM_PROCESSOR "${CMAKE_SYSTEM_PROCESSOR}")
endif()
string(TOLOWER "${MTOC_SYSTEM_PROCESSOR}" MTOC_SYSTEM_PROCESSOR)
if(MTOC_SYSTEM_PROCESSOR MATCHES "^(aarch64|arm64)")
    target_compile_definitions(mtoc PRIVATE
        __arm64__=1
        EMULATED_HOST_CPU_TYPE=16777228
        EMULATED_HOST_CPU_SUBTYPE=0
    )
elseif(MTOC_SYSTEM_PROCESSOR MATCHES "^(x86_64|amd64)")
    target_compile_definitions(mtoc PRIVATE
        EMULATED_HOST_CPU_TYPE=16777223
        EMULATED_HOST_CPU_SUBTYPE=3
    )
else()
    message(FATAL_ERROR "mtoc supports aarch64/arm64 and x86_64/amd64 hosts; got ${MTOC_SYSTEM_PROCESSOR}")
endif()

target_link_libraries(mtoc PRIVATE ${CMAKE_DL_LIBS})

install(TARGETS mtoc RUNTIME DESTINATION "${CMAKE_INSTALL_BINDIR}")
install(FILES man/mtoc.1 DESTINATION "${CMAKE_INSTALL_MANDIR}/man1")
