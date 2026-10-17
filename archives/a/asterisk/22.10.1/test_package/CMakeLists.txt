cmake_minimum_required(VERSION 3.15)
project(test_asterisk C)

enable_testing()

# Try to locate asterisk package via Conan-generated CMakeDeps.
# Application packages produce no library to link, so this is optional —
# do not make it REQUIRED; the test validates the binary via execution.
find_package(asterisk QUIET)

# Locate the asterisk binary for compile-time injection (R33: no hardcoded absolute path).
# Respects CMAKE_FIND_ROOT_PATH / prefix path, works under cross-build (ohos-aarch64).
find_program(ASTERISK_PROGRAM NAMES asterisk)

add_executable(test_asterisk test.c)

if(ASTERISK_PROGRAM)
    target_compile_definitions(test_asterisk PRIVATE ASTERISK_BIN="${ASTERISK_PROGRAM}")
    message(STATUS "asterisk binary found: ${ASTERISK_PROGRAM} -> ASTERISK_BIN defined for test")
else()
    message(STATUS "asterisk binary not found in PATH; test_asterisk will fallback to runtime PATH search")
endif()

# Application package has no import library; only link if target actually exists (e.g., future library split).
if(TARGET asterisk::asterisk)
    target_link_libraries(test_asterisk PRIVATE asterisk::asterisk)
endif()

add_test(NAME test_asterisk COMMAND test_asterisk)

# Optional direct version check via the discovered binary (only when not cross-compiling and binary is present)
if(ASTERISK_PROGRAM)
    add_test(NAME asterisk_version COMMAND ${ASTERISK_PROGRAM} -V)
endif()
