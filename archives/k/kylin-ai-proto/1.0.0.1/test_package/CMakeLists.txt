cmake_minimum_required(VERSION 3.15)
project(test_kylin-ai-proto CXX)

# Find the package via Conan-generated CMakeDeps (cmake_file_name = KylinAiProto)
find_package(KylinAiProto REQUIRED)

add_executable(test_kylin-ai-proto test.cpp)
target_link_libraries(test_kylin-ai-proto KylinAiProto::KylinAiProto)
# KAP_PROTOCOLS_DIR / KAP_CMAKE_DIR are injected by test_package/conanfile.py
# generate() from the dependency package folder (share/kylin-ai/protocols and
# lib/cmake/KylinAiProto).
target_compile_definitions(test_kylin-ai-proto PRIVATE
    KAP_PROTOCOLS_DIR="${KAP_PROTOCOLS_DIR}"
    KAP_CMAKE_DIR="${KAP_CMAKE_DIR}")

enable_testing()
add_test(NAME test_kylin-ai-proto COMMAND test_kylin-ai-proto)
