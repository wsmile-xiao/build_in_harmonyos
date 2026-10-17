cmake_minimum_required(VERSION 3.12)
# C 语言用于编译 gdbus-codegen 生成的 glue .c 源文件（P2 消费者编译测试）
project(test_package CXX C)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# CMakeDeps 按包名生成 config（组件 cmake_file_name 不单独产出 config 文件），
# target 名沿用组件声明：KylinAiEngine::KylinAiEngine / KylinAiProto::KylinAiProto
find_package(libkylin-ai-system-private REQUIRED CONFIG)

# --- 消费者冒烟 1：header-only API 编译链接 ---
add_executable(test_ai_engine test_ai_engine.cpp)
target_link_libraries(test_ai_engine PRIVATE KylinAiEngine::KylinAiEngine)

# --- 消费者冒烟 2（审查 P2）：实际调用 kylin_ai_generate_gdbus_proto_code 宏 ---
# 从包安装目录引入宏；KYLAI_GDBUS_CODEGEN / KYLAI_GDBUS_PROTOCOL_DIR /
# KYLAI_PROTO_CMAKE_DIR 由 test_package generate() 注入（与
# libkysdk-coreai-speech 消费者同模式）
include(${KYLAI_PROTO_CMAKE_DIR}/KylinAiProtoFunctions.cmake)
kylin_ai_generate_gdbus_proto_code(GENERATED_GLUE_FILES corespeechservice)

add_executable(test_proto_gen test_proto_gen.cpp ${GENERATED_GLUE_FILES})
# gio/gio.h 与 glib 库由 generate() 注入的依赖目录提供（绕开 pkg-config 解析）
target_include_directories(test_proto_gen PRIVATE ${KYLAI_GLIB_INCLUDE_DIRS})
target_link_directories(test_proto_gen PRIVATE ${KYLAI_GLIB_LIB_DIRS})
# glib 为静态库（.a），需完整传递链接链：glib 主库 + gmodule + gobject，
# 及其依赖 ffi（gobject 闭包）、intl（gettext）、pcre2-8、z（glib 压缩）。
# libintl/libffi 用绝对路径（generate() 定位 glib 包内 .a），避免 -lintl/
# -lffi 库名被 OHOS 工具链系统同名库抢占（CI 上 g_libintl_* 未定义）
target_link_libraries(test_proto_gen PRIVATE
    gio-2.0 gmodule-2.0 gobject-2.0 glib-2.0
    ${KYLAI_FFI_LIB} ${KYLAI_INTL_LIB} pcre2-8 z)

enable_testing()
# 构建阶段（构建 uid）经 cmake.test() 执行 ctest，真实运行两个冒烟二进制；
# test() 阶段 app uid 无法 exec 构建树产物，由 python 探针做读取断言
add_test(NAME ai_engine_smoke COMMAND test_ai_engine)
add_test(NAME proto_gen_smoke COMMAND test_proto_gen)
