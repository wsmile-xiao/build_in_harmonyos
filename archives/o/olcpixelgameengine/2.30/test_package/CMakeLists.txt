cmake_minimum_required(VERSION 3.15)
project(test_olcpixelgameengine CXX)

# Find the package via Conan-generated CMakeDeps
find_package(olcpixelgameengine REQUIRED)

add_executable(test_olcpixelgameengine test.cpp)
target_link_libraries(test_olcpixelgameengine olcpixelgameengine::olcpixelgameengine)

# OHOS 无上游原生窗口后端：按上游支持的无头模式消费（OLC_PGE_HEADLESS）
target_compile_definitions(test_olcpixelgameengine PRIVATE OLC_PGE_HEADLESS OLC_PGE_APPLICATION)
set_target_properties(test_olcpixelgameengine PROPERTIES
    CXX_STANDARD 17
    CXX_STANDARD_REQUIRED ON)

enable_testing()
add_test(NAME test_olcpixelgameengine COMMAND test_olcpixelgameengine)
