## PR 信息
- **三方库名称**：boost1.84-thread
- **上游版本**：boost 1.84.0（Boost.Thread 组件）
- **上游仓库地址**：https://github.com/boostorg/thread
- **适配路径**：路径 A（基础适配）
- **使用知识库**：E068（Boost.Build 鸿蒙兼容性问题，b2 不可用 → 手动裁剪编译）

---

## 测试用例对比

**通过率：上游测试 30/30（100%）；test_package 1/1（100%）**

### 上游库测试用例统计
| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 30 | 来源：libs/thread/test/ 与 example/ 运行时代表性子集（上游 469 文件含 43 个编译期失败测试 _fail 不在运行范围，遴选 21 test + 9 example 覆盖 Thread 核心功能面：线程创建/移动/join、mutex 族、condition_variable、future/promise/async、once、tss、hardware_concurrency） |
| 集成测试 | 0 | 无独立集成测试目录 |
| 其他测试 | 0 | - |
| **合计** | **30** | - |

### 适配后测试用例统计
| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 30 | 不变 | 全部 30 项在 OHOS 真实编译运行（绕过 b2，clang++ 直编 + 直跑，断言合计 189） |
| 集成测试 | 0 | 不变 | - |
| 鸿蒙特有测试 | 1 | 新增 | test_package：thread 创建/join/lambda 捕获、thread::id、hardware_concurrency、mutex+condition_variable、promise→future、sleep_for（7 组断言） |
| **合计** | **31** | **+1** | |

---

## 上游测试用例修改说明
### 是否存在对上游测试用例的修改？
- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（逐条：修改的测试文件/修改原因/修改内容）

---

## 补全测试用例说明
### 上游是否存在无测试用例，适配后补全的情况？
- [x] **否**，上游已有测试用例覆盖
- [ ] **是**，补全（补全的测试范围/补全原因/新增测试文件清单）

---

## 适配说明

Boost.Thread 单库拆分包（Debian 风格 libboost-thread1.84-dev 形态）：
- b2 在 OHOS 不兼容（E068），手动编译 libs/thread/src 5 源文件（future/tss_null/pthread/{once,once_atomic,thread}）
- **chrono 3 编译单元并入 libboost_thread.a**：thread 的 usage-requirements 要求链接 boost_chrono（this_thread::sleep_for 使用 boost::chrono::steady_clock::now()），单库拆分包自包含该依赖；与 boost1.84-chrono 包（!8481）独立并行可用
- 补丁 0001：BOOST_SP_NO_PTHREAD_SETCANCELSTATE 特性宏绕开 OHOS musl 缺失的 pthread_setcancelstate（R8 特性宏合规，非平台宏）
- 测试运行注入 LD_LIBRARY_PATH（clang++ -print-file-name 自省定位 SDK libc++_shared.so，boost/1.85.0 先例）
- 测试二进制签名：llvm-objcopy --remove-section .codesign + binary-sign-tool self-sign（E298 先例）

### 与同系列包的关系
| 包 | PR | 关系 |
|----|----|----|
| boost1.84 本体 | !8530 | 不同包名并行，本体 4 库 vs 本包单库，无文件冲突 |
| boost1.84-chrono | !8481 | chrono 编译单元已并入本包（自包含），两者独立可用 |
| boost1.84-system | !8468 | error_code 依赖同样自包含处理 |
