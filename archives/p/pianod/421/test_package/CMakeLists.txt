cmake_minimum_required(VERSION 3.15)
project(pianod_consumer_test CXX)

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_executable(test_pianod test_pianod.cpp)

# Absolute path of the packaged web-client dir, handed over by the test_package
# CMakeToolchain. The recipe installs with --prefix=/ (so conan's DESTDIR install
# lands in <pkg>/bin), hence the compiled-in DEFAULT_WWWDIR is not usable and the
# daemon must be started with an explicit -c <dir>.
if(DEFINED PIANOD_WWWDIR AND NOT PIANOD_WWWDIR STREQUAL "")
    target_compile_definitions(test_pianod PRIVATE PIANOD_WWWDIR="${PIANOD_WWWDIR}")
else()
    target_compile_definitions(test_pianod PRIVATE PIANOD_WWWDIR="")
endif()

enable_testing()
add_test(NAME pianod_consumer COMMAND test_pianod)
