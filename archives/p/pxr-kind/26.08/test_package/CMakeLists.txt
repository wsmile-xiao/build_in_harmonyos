cmake_minimum_required(VERSION 3.15)
project(test_pxr_kind CXX)

find_package(pxr-kind REQUIRED)

add_executable(test_pxr_kind test_pxr_kind.cpp)
target_link_libraries(test_pxr_kind pxr-kind::pxr-kind)
target_compile_features(test_pxr_kind PRIVATE cxx_std_17)

# Ship the resource plugin metadata next to the test binary; the test
# registers it via PlugRegistry to replicate the upstream python test.
configure_file(plugInfo.json ${CMAKE_CURRENT_BINARY_DIR}/plugInfo.json COPYONLY)
# PlugRegistry::RegisterPlugins requires an absolute path, so bake the
# binary dir in at compile time.
target_compile_definitions(test_pxr_kind PRIVATE
    TEST_RESOURCE_DIR="${CMAKE_CURRENT_BINARY_DIR}")

enable_testing()
add_test(NAME test_pxr_kind COMMAND test_pxr_kind)
