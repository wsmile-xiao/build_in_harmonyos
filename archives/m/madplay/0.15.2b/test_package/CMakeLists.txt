cmake_minimum_required(VERSION 3.15)
project(gen_fixture C)

# gen_fixture generates the deterministic silent MPEG-1 Layer III fixture
# used by the consumer test; it runs on the build machine only.
add_executable(gen_fixture gen_fixture.c)
set_target_properties(gen_fixture PROPERTIES RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)
