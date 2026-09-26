cmake_minimum_required(VERSION 3.15)
project(gssntlmssp_consumer LANGUAGES C)

set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)

add_executable(gssntlm_probe gssntlm_probe.c)

# dlopen/dlsym（musl 上 libdl 并入 libc；CMAKE_DL_LIBS 为空则不链）
target_link_libraries(gssntlm_probe PRIVATE ${CMAKE_DL_LIBS})

# GSSAPI 头与 libgssapi_krb5（name-type OID 符号 GSS_C_NT_* 与 gss_release_buffer）
target_include_directories(gssntlm_probe PRIVATE ${GSSAPI_INCLUDE_DIRS})
target_link_directories(gssntlm_probe PRIVATE ${GSSAPI_LIB_DIRS})
target_link_libraries(gssntlm_probe PRIVATE ${GSSAPI_LIBS})
