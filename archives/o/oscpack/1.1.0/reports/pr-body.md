- **三方库名称**：oscpack
- **上游版本**：1.1.0
- **上游仓库地址**：https://github.com/rossbencina/oscpack
- **适配路径**：路径 A（基础适配）
- **使用知识库**：E092（CMake HarmonyOS 平台识别，G0 预检命中）；新增知识草稿 DRAFT-oscpack-1.1.0-lp64-long-int32-typedef（aarch64 LP64 typedef 假设导致静默状态破坏）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 91 | 来源：上游 tests/OscUnitTests.cpp（自研 assertEqual 框架） |
| 集成测试 | 2 | 来源：上游 tests/OscSendTests.cpp + tests/OscReceiveTest.cpp（UDP 回环配对） |
| 其他测试 | 3 | 来源：上游 examples/（OscDump、SimpleSend、SimpleReceive，构建验证） |
| **合计** | **96** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 91 | 不变 | OscUnitTests 实测 91 passed, 0 failed |
| 集成测试 | 2 | 不变 | OscSendTests/OscReceiveTest UDP 回环实测通过 |
| 鸿蒙特有测试 | 23 | 新增 | test_package/test_oscpack.cpp 端到端消费者测试：打包 bundle/消息→按网络字节流解析回→逐字段断言，含 LP64 类型修复校验、字节序往返（0x01020304）与错误类型访问抛 osc::Exception |
| **合计** | **116** | **+23** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> - **补全的测试范围**：为消费者视角新增 23 个断言的端到端测试（打包→解析→逐字段校验 + LP64 类型修复回归 + 异常健壮性）
> - **补全原因**：上游 OscUnitTests 属库内视角单测；按 L1e/rule12 要求补完整消费者工作流用例，同时回归本 PR 的 LP64 类型修复
> - **新增测试文件清单**：
>   1. `archives/o/oscpack/1.1.0/test_package/test_oscpack.cpp` — 端到端消费者测试（23 断言）

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：96/96（100%）—— OscUnitTests 91/91 + UDP 回环 2 项 + examples 3 项（构建并运行验证）
- 新增测试用例通过率：23/23（100%）

## 补充说明

1. **LP64 适配补丁（核心）**：上游 `osc/OscTypes.h` 用 `#if defined(__x86_64__)` 分支假设"非 x86_64 = 32 位平台"，`#else` 分支 `typedef signed long int32` 在 aarch64（LP64，long=8 字节）下 `sizeof(int32)==8`；Release 构建把构造函数 sanity assert 编译掉（-DNDEBUG），类型错乱静默破坏 OutboundPacketStream 内部状态，OscUnitTests 以 SIGSEGV 形式延迟崩溃。补丁改为 `signed int`（LP32/LP64 通用），并给同库其余 32 位专用 int 重载守卫追加 `!defined(__LP64__) && !defined(_LP64)`（否则签名重复编译报错）。修复后上游 91/91 全通过。详见 `knowledge/drafts/DRAFT-oscpack-1.1.0-lp64-long-int32-typedef.md`。
2. **CMake install 规则补丁**：上游 CMakeLists 无任何 install 规则，补丁按源码根相对布局安装库与 `osc/`、`ip/` 头文件（消费者 `#include "osc/OscTypes.h"`）。
3. **CMake 4 兼容**：上游声明 `cmake_minimum_required(2.6)`，配方以 `cache_variables` 注入 `CMAKE_POLICY_VERSION_MINIMUM=3.5`（必须走命令行 cache 变量，toolchain 文件内设置对 `cmake_minimum_required` 无效）。
4. **字节序**：OscHostEndianness.h 经 `__BYTE_ORDER__` 自动探测，aarch64 无需额外宏。
5. 已知限制：上游无版本化 SONAME，静态链接（R26 默认）不受影响；shared 构建的 SONAME 为 `liboscpack.so`。
