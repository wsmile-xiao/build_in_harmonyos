cmake_minimum_required(VERSION 3.15)
project(test_ola CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS ON)

# protobuf/3.17.3 sets cmake_find_mode=none, so CMakeDeps emits no
# protobuf config, yet ola-config.cmake calls find_dependency(protobuf).
# The conan generators folder (on CMAKE_PREFIX_PATH) holds the
# Findprotobuf.cmake stand-in written by test_package/conanfile.py —
# prepend it to CMAKE_MODULE_PATH so it wins before the CONFIG lookup.
list(INSERT CMAKE_MODULE_PATH 0 "${CMAKE_BINARY_DIR}/generators")

find_package(ola REQUIRED CONFIG)

add_executable(test_ola test_ola.cpp)
target_link_libraries(test_ola PRIVATE ola::ola)

enable_testing()
add_test(NAME test_ola COMMAND test_ola)
