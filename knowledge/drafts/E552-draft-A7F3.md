# CMake shared 选项与导出目标映射

## 现象或适配场景
独立 CMake 库在 Conan 中能编译，但消费者找不到导出目标或链接到错误的库名。

## 根因
上游可能通过 interface alias 暴露目标，实际归档名、安装 config 和 `BUILD_SHARED_LIBS`
开关分别由不同变量控制；仅凭配方命名猜测会造成 shared/static 与 `cpp_info` 不一致。

## 修复步骤
将 Conan `shared` 显式映射到上游 CMake 开关；从安装目录回读 config、目标名和归档文件；
再设置 `cpp_info.libs` 与 `cmake_target_name`，并用真实消费者编译链接。

## 验证方式
在 OHOS/arm64 交叉 profile 下执行 Conan create 和 test_package 构建，消费者实际调用
pugixml 的解析/XPath API 并确认链接闭包。

## 适用范围和安全边界
适用于有标准 CMake install/export 的独立库；不能把本机成功解析 config 当作目标设备运行成功，
仍需独立真机 consumer 验证。
