cmake_minimum_required(VERSION 3.16)
project(evmc_consumer_case LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Resolve the packaged EVMC through the config package Conan's CMakeDeps
# generates from the recipe's package_info(), i.e. exactly the
# find_package()/imported-target route a downstream client uses.
find_package(evmc CONFIG REQUIRED)

# Upstream builds examples/example_vm/ as a SHARED library that a host dlopen()s
# at run time, but it is not part of what evmc installs (the install() rules
# cover only include/evmc and the lib/ archives). Rebuild it here from the
# pinned upstream sources so the consumer's loader leg has a real VM to load
# instead of a stub.
#
# This include() pulls the upstream example_vm target definitions, not the
# upstream root project: examples/example_vm/CMakeLists.txt only uses
# add_library()/target_*() and does not call any of the upstream helper macros
# (evmc_add_vm() etc.), so no upstream cmake/ module needs to be loaded here.
if(NOT EVMC_UPSTREAM_SOURCE_DIR)
    message(FATAL_ERROR "EVMC_UPSTREAM_SOURCE_DIR is not set by the test_package recipe")
endif()
add_subdirectory(
    "${EVMC_UPSTREAM_SOURCE_DIR}/examples/example_vm"
    "${CMAKE_CURRENT_BINARY_DIR}/upstream_example_vm"
)

add_executable(evmc_consumer_case evmc_consumer_case.cpp)
target_link_libraries(
    evmc_consumer_case
    PRIVATE
    evmc::evmc
    evmc::evmc_cpp
    evmc::loader
    evmc::instructions
    evmc::mocked_host
)

# The consumer opens libexample-vm.so by path at run time; make sure it exists
# before the consumer runs.
add_dependencies(evmc_consumer_case example-vm)
