# paho.mqtt.cpp 1.6.0 — 适配笔记

> 编译日期: 2026-09-10
> W3 验证日期: 2026-09-10
> 状态: built（PR #9413 open；CI/Review 待执行）

## 基本信息

| 项目 | 值 |
|------|-----|
| 软件 | paho.mqtt.cpp |
| 版本 | 1.6.0 |
| 构建系统 | CMake |
| 源码 | https://github.com/eclipse/paho.mqtt.cpp/archive/refs/tags/v1.6.0.tar.gz |
| 直接依赖 | paho.mqtt.c/1.3.14 |

## 配置

默认构建为静态库、关闭 SSL 和 samples/examples/documentation，并启用上游 Catch2
单元测试：

```text
PAHO_BUILD_STATIC=TRUE
PAHO_BUILD_SHARED=FALSE
PAHO_WITH_SSL=FALSE
PAHO_WITH_MQTT_C=FALSE
PAHO_BUILD_TESTS=TRUE
```

OHOS/HMDFS 不允许 GNU make 的 jobserver FIFO；package 配方和
`test_package/conanfile.py` 均在 `cmake.build()` 前强制
`tools.build:jobs=1`，避免 CMake 默认追加 `-j20` 后出现
`make: jobserver mkfifo: Operation not permitted`。

上游 `test/unit/*.cpp` 按 `TEST_CASE` 宏统计有 240 个测试用例，其中当前 CMake
测试目标实际编译 231 个；测试框架使用仓库已有的 `catch2/2.13.10-r0`
test-only 依赖。37 个用例依赖可达 MQTT broker，已由 `0002-test-unit-test_async_client.cpp-test-unit-test_client.cpp.patch`
标记为 `[broker]`，OHOS CTest 使用 `~[broker]` 排除；设备实测支持子集为 194/194
通过、0 失败、37 项显式排除。另有 `test_ssl_options.cpp` 中 9 个用例因默认关闭
SSL 未纳入当前 CMake 测试目标；legacy `test_async_client_v3.cpp` 使用 CppUnit，
也不属于当前 Catch2 CMake 测试目标。

`test_package/test_ohos.cpp` 是只在 `CMAKE_SYSTEM_NAME=HarmonyOS`（或 `OHOS`）
下构建的鸿蒙特有 consumer 测试。在设备上验证 `uname` 返回 `HarmonyOS`，并实际
构造 `mqtt::async_client` 检查 server URI 和 client ID；该测试不连接 broker。

上游 CMake 使用 `eclipse-paho-mqtt-c::paho-mqtt3a(-static)` target，而仓库中的
`paho.mqtt.c/1.3.14` Conan 配方提供 `paho.mqtt.c::paho.mqtt.c` package target。
`0001-CMakeLists.txt-cmake-PahoMqttCppConfig.cmake.in.patch` 在构建配置和安装后的 package config 中建立兼容
别名，避免改动上游 C++ 源码。

现有 `paho.mqtt.c/1.3.14` 包含 `include/MQTTAsync.h`，但配方未声明
`cpp_info.includedirs`，导致 CMakeDeps 生成空的 include 元数据。`conanfile.py`
通过 package-local CMake build module 读取 `paho.mqtt.c_PACKAGE_FOLDER_RELEASE`，
确认头文件存在后补回依赖 target 的 include 目录；设备 consumer test 已验证该路径。

## 验证状态

依赖发布预检（R36）在设备连接 Conan remote `ohpcd` 后执行
`conan download "paho.mqtt.c/1.3.14" --only-recipe -r=ohpcd` 和
`conan download "catch2/2.13.10-r0" --only-recipe -r=ohpcd`，两条命令均返回 0。
前者核对到 recipe revision
`090a2e13b9cda856bb4f3bf1f71ea2ee`，后者核对到
`536c52afeab4ea7925bea4d71b59ec48`；两项均在连接 remote 后提示
`already in cache`，因此这里没有把缓存命中冒充成重新下载。

W0/W3 的精确 run ID、requested SHA、计划 SHA、Conan package revision、原始日志
和 `conan-verify` 补充报告保存在任务外的 hash-bound evidence 目录中；跟踪文档
不自记录当前运行 ID，避免记录文件本身的提交改变被验证 SHA。当前证据包括设备
环境、主检出、源包 SHA、配方预检、`conan create`、consumer test、G0/G1/G2/G3/G4/
L2/L4/L5 和 repo snapshot；默认 CTest 在无 broker 时运行 194/194 个支持用例，
临时启动本地 Mosquitto 后未过滤的 231 个已编译上游用例全部通过（1470 assertions），
并且 OHOS-specific `test_package` 测试通过。
