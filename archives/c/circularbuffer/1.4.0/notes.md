# circularbuffer 1.4.0 适配笔记

## 编译环境
- 构建系统: none（header-only 模板库，无构建系统）
- 编译日期: 2026-09-23
- 编译器: clang/clang++ (OHOS SDK, clang 15.0.4)
- 状态: built

## 编译步骤

header-only 库无编译产物；Conan 配方仅打包头文件：

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

- source(): 从官方源下载 tar.gz（显式 filename 修正 codeload 无扩展名 URL）
- package(): 复制 *.h/*.hpp/*.tpp 到 include/、LICENSE 到 licenses/
- test_package: CMake C++ 消费者程序，1/1 测试通过

## 上游测试枚举台账（双口径）

### 枚举范围

官方 tag 1.4.0 源码（SHA-256 e01a837d...fc0a）全部文件按规则枚举：

| 入口 | 类型 | 是否独立上游用例 | 分类理由 | 是否运行 | 结果/原因 |
|------|------|------------------|----------|---------|-----------|
| CircularBuffer.hpp | 框架头（库 API） | 否 | 库主体，非测试 | - | - |
| CircularBuffer.h | 兼容包装头 | 否 | 仅 include 转发 | - | - |
| CircularBuffer.tpp | 模板实现 | 否 | 库主体，非测试 | - | - |
| examples/Basic/Basic.ino | Arduino 示例 | 否 | 依赖 Arduino 运行时（Serial/pinMode/analogRead），非独立测试用例 | 尝试编译 | 首错：`use of undeclared identifier 'Serial'`，Arduino 运行时缺失，不可独立运行 |
| examples/Arrays/Arrays.ino | Arduino 示例 | 否 | 同上（Serial/analogRead） | 尝试编译 | 同 Basic，Arduino 运行时缺失 |
| examples/EventLogging/EventLogging.ino | Arduino 示例 | 否 | 同上（Serial/pinMode） | 尝试编译 | 同 Basic |
| examples/Function/Function.ino | Arduino 示例 | 否 | 同上 | 尝试编译 | 同 Basic |
| examples/Interrupts/Interrupts.ino | Arduino 示例 | 否 | 依赖 attachInterrupt/digitalPinToInterrupt | 尝试编译 | 同 Basic |
| examples/Object/Object.ino + Record.h | Arduino 示例 | 否 | 同上 | 尝试编译 | 同 Basic |
| examples/Queue/Queue.ino | Arduino 示例 | 否 | 同上 | 尝试编译 | 同 Basic |
| examples/RetroCompatibility/RetroCompatibility.ino | Arduino 示例 | 否 | 定义 CIRCULAR_BUFFER_DEBUG 触发 `#include <Print.h>`（Arduino 框架头） | 尝试编译 | 首错：`fatal error: 'Print.h' file not found` |
| examples/Stack/Stack.ino | Arduino 示例 | 否 | 同 Basic | 尝试编译 | 同 Basic |
| examples/Struct/Struct.ino | Arduino 示例 | 否 | 同上 | 尝试编译 | 同 Basic |
| examples/Test/Test.ino | Arduino 示例 | 否 | 定义 CIRCULAR_BUFFER_DEBUG 触发 Print.h；其余用例同为 Arduino 运行时依赖 | 尝试编译 | 首错：`'Print.h' file not found` |
| .github/workflows/main.yml | 上游 CI | 否 | 仅 arduino/compile-sketches 编译示例（avr/samd/mbed 板），无断言运行 | - | Arduino 生态板级验证，非本平台可执行 |
| .travis.yml | 上游 CI（旧） | 否 | arduino --verify 编译示例 | - | 同上 |

### 双口径统计

- source_declared_total（独立上游用例数）：**0**
  （上游无测试框架、无 TEST_CASE/ctest/make check 目标；11 个 .ino 为 Arduino 示例，按规则不计为独立上游用例，但已在台账明确列出）
- configured_executable_total（当前 OHOS 配置实例化用例数）：**0**
  （header-only 库无构建系统，无测试目标注册）
- executed_passed_total：**0/0**
- 未运行/未实例化：11 个 .ino 示例（原因：依赖 Arduino 运行时框架——Serial/pinMode/analogRead/attachInterrupt/Print.h 等，OHOS 工具链无此运行时；已实测首错）
- 全量通过率：**0/0（空集，无独立上游用例）**，另列当前配置可执行集合通过率 0/0

### 模板逻辑可编译性验证（非上游用例，作为库可用性补充）

隔离 Arduino 依赖后，模板逻辑本身在 OHOS 工具链编译通过：

```bash
clang++ -std=c++17 -I. -x c++ -c - <<'EOF'   # push/copyToArray/size 逻辑
EOF
# 退出码 0，产物 cb_check.o 3088 字节
```

完整消费者验证见 test_package（conan create 内 1/1 通过）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan create source() 报 BadZipFile | codeload URL（/refs/tags/1.4.0）无文件扩展名，get() 无法推断压缩格式 | source() 显式传 `filename="circularbuffer-1.4.0.tar.gz"` |
| 2 | package() 后 "No files in this package!" | copy() 相对 dst 未被解析到 package_folder | src/dst 全部改用绝对路径（参考 broker/autobahn-cpp 配方） |
| 3 | 任务头 URL dgraph-io/CircularBuffer 404 | 该仓库在 GitHub 上不存在（API 权威确认） | 改用作者官方源 rlogiacco/CircularBuffer tag 1.4.0，SHA-256 已核验 |
| 4 | /tmp 只读 | 平台 /tmp 挂载只读 | 编译/输出改 $TMPDIR（$HOME/tmp） |

## 依赖版本

无第三方依赖（仅标准 C/C++ 头文件 stdint.h/stddef.h）。

## 验证结果

```bash
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64
# 1/1 test_package 消费者测试 Passed（push/shift/pop/unshift/first/last/size/available/isEmpty/isFull/clear/copyToArray/operator[]，FIFO/LIFO 语义，uint8/int 两型）
```

## 注意事项

- header-only 模板库：无 build()，无 commands.json（R38 不适用，无可执行产物）
- CircularBuffer.tpp 必须随 .hpp 一起安装（#include <CircularBuffer.tpp>）
- 上游 CI 仅验证 Arduino 板级编译，本平台以 test_package 消费者测试作为实际验证
---

**编译结束**: 2026-09-23 04:12
**最终状态**: built
