- **三方库名称**：libdaemon
- **上游版本**：0.14
- **上游仓库地址**：https://0pointer.de/lennart/projects/libdaemon/libdaemon-0.14.tar.gz
- **适配路径**：路径 A（基础适配）
- **使用知识库**：无

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 上游无正式测试框架（has_tests: false） |
| 集成测试 | 0 | - |
| 其他测试 | 1 | 示例程序 examples/testd.c（daemon fork/pidfile/log 基础功能，command: ./testd） |
| **合计** | **1** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | - |
| 集成测试 | 0 | 不变 | - |
| 其他测试 | 1 | 不变 | testd 示例程序在 OHOS 上运行通过（daemon_fork/retval 正常退出） |
| 鸿蒙特有测试 | 1 | +1（新增） | 新增 test_package 消费者测试 test_libdaemon（实测 1/1 Passed） |
| **合计** | **2** | **+1** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [ ] **否**，未修改上游任何测试用例
- [x] **是**，存在对上游测试用例的修改（请在下方逐条说明）

> 1. **修改的测试文件**：examples/testd.c
>    - **修改原因**：OHOS 不提供 `sys/unistd.h`
>    - **修改内容**：`sys/unistd.h` → `unistd.h`（0004-examples-testd.c.patch）
>
> 另含 3 个构建脚本补丁（非测试用例）：config.guess/config.sub 添加 HarmonyOS
> 平台识别、configure 移除 `umask 077`（OHOS SELinux 不支持）。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> - **补全的测试范围**：新增 1 个 test_package 消费者测试（test_libdaemon）——
>   通过 `find_package(libdaemon)` 链接 `libdaemon::libdaemon` 并调用 `daemon_log`
>   API，验证产物可链接、头文件与 API 符号可用（实测 1/1 Passed，100%）
> - **补全原因**：上游无正式测试框架（has_tests: false），仅含示例程序
>   examples/testd.c，无可在 OHOS 隔离环境执行的断言测试
> - **新增测试文件清单**：
>   1. `archives/l/libdaemon/0.14/test_package/conanfile.py` — 定义消费者测试配方（L1 测试，conan create 自动执行）
>   2. `archives/l/libdaemon/0.14/test_package/CMakeLists.txt` — find_package + 链接 libdaemon::libdaemon，注册 CTest 用例 test_libdaemon
>   3. `archives/l/libdaemon/0.14/test_package/test.c` — 调用 daemon_log API 的冒烟测试
>   4. `archives/l/libdaemon/0.14/test_package/MANIFEST.yml` — 测试声明清单

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：1/1（100%）（testd 示例程序在 OHOS 上运行通过，daemon_fork/retval 正常退出）
- 新增测试用例通过率：1/1（100%）（test_package test_libdaemon，调用 daemon_log API 通过）

## 补充说明

- **产物**：libdaemon.a（静态，R26 默认）+ libdaemon.so.0.5.0（动态）+ 7 个头文件 + pkgconfig，仅依赖 libc
- **补丁清单**（构建适配，非测试用例）：
  - `0001-config.guess.patch`：添加 HarmonyOS/OHOS 平台识别
  - `0002-config.sub.patch`：添加 linux-ohos 目标支持
  - `0003-configure.patch`：移除 `umask 077`（OHOS SELinux 不支持）
  - `0004-examples-testd.c.patch`：修复 `sys/unistd.h` → `unistd.h`
- **已知限制**：cmakedeps 静态库 find_library 前缀问题——HarmonyOS 为 CMake 未知平台，
  `cpp_info.libs` 需写去前缀库名 `daemon`，否则查找 `liblibdaemon.a` 失败（已在 conanfile.py 注释说明）

### 验证命令

```
conan create archives/l/libdaemon/0.14 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
→ 构建成功，test_package 链接 libdaemon::libdaemon 并调用 daemon_log API
→ 1/1 Test #1: test_libdaemon ... Passed
→ 100% tests passed, 0 tests failed out of 1
```
