cmake_minimum_required(VERSION 3.18)
project(test_omniorb CXX)

find_package(omniorb REQUIRED)
# OMNIIDL_BIN is passed explicitly by the test_package recipe (absolute path
# into the tested package's bindir); only fall back to PATH search when the
# recipe did not set it, so configure never depends on PATH luck.
if(NOT OMNIIDL_BIN)
  find_program(OMNIIDL_BIN omniidl REQUIRED)
endif()

# Compile the Echo interface with the just-built IDL compiler, mirroring
# the upstream src/examples/echo/eg1 flow (echo.idl is upstream's own
# interface definition, copied into this directory).
set(ECHO_IDL "${CMAKE_CURRENT_SOURCE_DIR}/echo.idl")
add_custom_command(
    OUTPUT "${CMAKE_CURRENT_BINARY_DIR}/echo.hh"
           "${CMAKE_CURRENT_BINARY_DIR}/echoSK.cc"
    COMMAND "${OMNIIDL_BIN}" -bcxx "${ECHO_IDL}"
    WORKING_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}"
    DEPENDS "${ECHO_IDL}"
    COMMENT "Running omniidl on echo.idl"
    VERBATIM)

add_executable(test_echo
    "${CMAKE_CURRENT_SOURCE_DIR}/test_echo.cpp"
    "${CMAKE_CURRENT_BINARY_DIR}/echoSK.cc")
target_include_directories(test_echo PRIVATE "${CMAKE_CURRENT_BINARY_DIR}")
target_link_libraries(test_echo PRIVATE omniorb::omniorb)

# Upstream functional checks: 8 hardware-free deterministic checks against
# the packaged 4.3.4 artifacts (public C++ ORB API + bundled omniidl -V).
# OMNIIDL_BIN is passed explicitly by the test_package recipe (absolute path
# into the tested package's bindir); the binary falls back to PATH search
# when the recipe did not set it.
if(NOT DEFINED OMNIIDL_BIN)
  set(OMNIIDL_BIN "")
endif()
add_executable(test_upstream_checks
    "${CMAKE_CURRENT_SOURCE_DIR}/test_upstream_checks.cpp")
target_compile_definitions(test_upstream_checks PRIVATE OMNIIDL_BIN="${OMNIIDL_BIN}")
target_link_libraries(test_upstream_checks PRIVATE omniorb::omniorb)

enable_testing()
add_test(NAME echo_collocated COMMAND test_echo)
add_test(NAME upstream_checks COMMAND test_upstream_checks)
