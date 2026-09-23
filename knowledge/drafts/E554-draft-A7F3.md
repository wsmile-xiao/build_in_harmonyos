# Makefile-only C++ 库的 Conan CMake 安装契约

## 现象或适配场景
上游 C++ 库只有硬编码 `gcc/g++` 的 Makefile，没有标准 install 目标；直接交给 Conan 无法稳定选择 OHOS 工具链，也无法形成公共头文件和库的安装闭包。

## 根因
Makefile 假定本机 GNU 编译器，并把归档、头文件复制和安装路径留给调用者处理，缺少 Conan 所需的可观察 target、安装规则和 shared/fPIC 语义。

## 修复步骤
在配方导出的任务私有 `CMakeLists.txt` 中显式列出上游源文件，使用 Conan `CMakeToolchain` 提供编译器；把 `shared` 映射到 `BUILD_SHARED_LIBS`，为库和公共头文件添加 `install()`，再按实际归档名与导出 target 设置 `cpp_info.libs`、`cmake_file_name` 和 `cmake_target_name`。

## 验证方式
先用上游 Makefile 独立运行完整测试；随后在 OHOS/armv8 profile 下执行 Conan create，确认库和头文件安装、消费者编译链接成功，再用可运行的主机 profile 执行消费者。

## 适用范围和安全边界
适用于小型、自包含、无外部依赖的 Makefile 库。CMake/主机消费者成功只证明构建和链接契约，不能替代目标设备运行；上游测试分母仍按原始测试程序统计。
