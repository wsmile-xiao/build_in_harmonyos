cmake_minimum_required(VERSION 3.15)
project(test_chunkio C)

# Consumer view: only the packaged headers + archives are visible here.
find_package(chunkio REQUIRED)

add_executable(test_chunkio test_chunkio.c)
target_link_libraries(test_chunkio chunkio::chunkio)

# Deterministic location so test_package/conanfile.py can self.run() the
# binary directly (L0d requires a real self.run(), not cmake.test()).
set_target_properties(test_chunkio PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin")
