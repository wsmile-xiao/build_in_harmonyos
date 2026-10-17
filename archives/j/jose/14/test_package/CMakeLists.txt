cmake_minimum_required(VERSION 3.15)
project(test_jose C)

set(CMAKE_C_STANDARD 99)

# Find the package via Conan-generated CMakeDeps
find_package(jose REQUIRED)

# 公共 API 消费者测试：只使用安装进包的 <jose/b64.h>
add_executable(test_jose test.c)
target_link_libraries(test_jose jose::jose)

# 鸿蒙专项：驱动安装包里的 `jose` CLI 与打包 ELF 身份断言
add_executable(test_jose_ohos jose_ohos_test.c)
target_link_libraries(test_jose_ohos jose::jose)

enable_testing()
add_test(NAME test_jose COMMAND test_jose)
add_test(NAME test_jose_ohos COMMAND test_jose_ohos)

# 安装包专项测试要知道被安装的二进制在哪：由 test_package/conanfile.py 通过
# CMakeToolchain 传入（消费者视角下的绝对路径，不依赖 shell PATH）。
set(JOSE_BIN "" CACHE PATH "Absolute path of the installed jose CLI")
if(JOSE_BIN)
    target_compile_definitions(test_jose_ohos PRIVATE JOSE_BIN="${JOSE_BIN}")
endif()
