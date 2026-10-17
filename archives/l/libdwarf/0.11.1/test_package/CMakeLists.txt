cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES C)

find_package(libdwarf REQUIRED)

# 真实本地 ELF/DWARF fixture：以 -g 编译、不 strip，确保含 DWARF 调试段
add_executable(dwarf_fixture dwarf_fixture.c)
target_compile_options(dwarf_fixture PRIVATE -g)
# 不允许链接/剥离，保持 DWARF 段完整
set_target_properties(dwarf_fixture PROPERTIES
    LINKER_LANGUAGE C)

# test_package：真实 libdwarf 消费者，需 fixture 路径参数
add_executable(${PROJECT_NAME} test_package.c)
target_link_libraries(${PROJECT_NAME} PRIVATE libdwarf::libdwarf)
# CMake 流程交接 fixture 路径：conan test_package 无参运行时使用编译期默认路径
target_compile_definitions(${PROJECT_NAME} PRIVATE
    DWARF_FIXTURE_PATH="$<TARGET_FILE:dwarf_fixture>")

if(${libdwarf_VERSION} VERSION_LESS "0.9.1")
    target_compile_definitions(${PROJECT_NAME} PRIVATE "LIBDWARF_NESTED_INCLUDE")
endif()

# CTest：把 fixture 产物路径传给 test_package（正向）
enable_testing()
add_test(NAME test_package_with_fixture
         COMMAND ${PROJECT_NAME} $<TARGET_FILE:dwarf_fixture>)
# 负向：无 fixture 参数（强制无效环境路径）应非零退出
add_test(NAME test_package_missing_fixture
         COMMAND ${PROJECT_NAME})
set_tests_properties(test_package_missing_fixture PROPERTIES
    ENVIRONMENT "DWARF_FIXTURE_PATH=/nonexistent/libdwarf-fixture"
    WILL_FAIL TRUE)
