cmake_minimum_required(VERSION 3.15)

# 消费者用例：以"库的使用者"身份链接 vali 的安装产物。
# vali 是纯 C 库，消费者侧不需要 C++ 编译器。
project(vali_consumer_test C)

# Conan CMakeDeps 会按 recipe 里声明的
#   cpp_info.set_property("cmake_file_name", "vali")
#   cpp_info.set_property("cmake_target_name", "vali::vali")
# 生成 vali-config.cmake / vali-config-version.cmake，因此用 CONFIG 模式查找即可。
find_package(vali CONFIG REQUIRED)

# vali.h 的公共 API 用了 struct json_object *（前向声明），消费者要真正构造和读取
# 报文参数就需要 json-c。它是 vali 的公共依赖，由 conan 传递提供。
# 注意用的是规范路径 <json-c/json.h>，而不是发行版才有的顶层兼容头
# <json_object.h> —— 后者在只按上游 CMakeLists 安装的 json-c 包里并不存在。
find_package(json-c CONFIG REQUIRED)

add_executable(test_vali test_vali.c)

target_link_libraries(test_vali PRIVATE vali::vali json-c::json-c)

# ★ 制品仓的 json-c/0.18 包没有导出头目录：它的 recipe 只声明了
#   cpp_info.libs / cmake_file_name / pkg_config_name，实测 CMakeDeps 生成的
#   `json-c_INCLUDE_DIRS_RELEASE` 为空，而头实际装在 <pkg>/include/json-c/ 下。
#   所以光 find_package(json-c) 拿不到 -I。这里用 conanfile.py 的 generate()
#   注入的绝对路径（<pkg>/include）补上 —— 用例写的是带目录前缀的规范路径
#   `<json-c/json.h>`，所以需要的是 include/ 这一层。
if(NOT JSON_C_INCLUDE_DIR)
    message(FATAL_ERROR "JSON_C_INCLUDE_DIR was not injected by the test_package recipe")
endif()
target_include_directories(test_vali PRIVATE "${JSON_C_INCLUDE_DIR}")

# 在 OHOS clang 下保持干净：本例程只用 POSIX 接口（socketpair/fork/waitpid）
set_target_properties(test_vali PROPERTIES
    C_STANDARD 11
    C_STANDARD_REQUIRED ON)
