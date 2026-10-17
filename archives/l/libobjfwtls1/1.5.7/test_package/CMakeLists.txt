cmake_minimum_required(VERSION 3.15)
project(test_libobjfwtls1 LANGUAGES C)

# ObjFW uses its own Objective-C runtime (objfw-1.5), not the system GNU/Apple
# runtime. The consumer must compile with the ObjFW runtime flags.
# NOTE: set() with multiple arguments would create a CMake LIST (semicolon-
# separated) and each flag would be passed to clang as a separate input file
# ("clang-15: error: no input files"); the flags must stay in a single string.
enable_language(OBJC)

if(CMAKE_C_COMPILER_ID MATCHES "Clang")
  set(CMAKE_OBJC_FLAGS
      "${CMAKE_OBJC_FLAGS} -fobjc-exceptions -fexceptions -funwind-tables -fconstant-string-class=OFConstantString -Xclang -fno-constant-cfstrings -Xclang -fobjc-runtime=objfw-1.5 -Xclang -fblocks")
endif()

find_package(libobjfwtls1 REQUIRED)

# Objective-C consumer test: genuinely calls the ObjFWTLS public API.
add_executable(test_libobjfwtls1 test_tls.m)
target_link_libraries(test_libobjfwtls1 PRIVATE libobjfwtls1::libobjfwtls1)

# Plain C consumer test: proves libobjfwrt (ObjFW runtime) links and loads,
# and that ObjFW core classes are registered (L0c genuine .c test source).
add_executable(test_runtime test_runtime.c)
target_link_libraries(test_runtime PRIVATE libobjfwtls1::libobjfwtls1)
