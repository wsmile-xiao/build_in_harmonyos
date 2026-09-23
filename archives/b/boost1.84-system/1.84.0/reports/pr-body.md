## PR 信息
- **三方库名称**：boost1.84-system
- **上游版本**：boost 1.84.0（Boost.System 组件）
- **上游仓库地址**：https://github.com/boostorg/system
- **适配路径**：路径 A（基础适配）
- **使用知识库**：E068（Boost.Build 鸿蒙兼容性问题，b2 不可用 → 手动裁剪编译）

---

## 测试用例对比

### 上游库测试用例统计
| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 94 | 来源：libs/system/test/（Boost.System 官方 lightweight_test 框架，Jamfile.v2 的 run/system-run/compile 目标全集） |
| 集成测试 | 0 | 无独立集成测试目录 |
| 其他测试 | 0 | - |
| **合计** | **94** | Windows 专属与动态库变体用例已在 94 项遴选时排除 |

### 适配后测试用例统计
| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 94 | 不变 | 全部 94 项在 OHOS 真实编译运行（绕过 b2，clang++ 直编 + 直跑） |
| 集成测试 | 0 | 不变 | - |
| 鸿蒙特有测试 | 1 | 新增 | test_package：error_code/system_error 组件 API 冒烟（6 组断言） |
| **合计** | **95** | **+1** | |

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

## 验证结果
- 编译状态：通过
- 上游测试用例通过率：93/94（98.9%）
- 新增测试用例通过率：1/1（100%）

### 非 100% 通过率豁免说明（逐项）

**error_code_test：2 处断言失败（rc=2），平台 libc 行为差异，非适配缺陷。**

- 失败断言 1（error_code_test.cpp:202）：`ec.message().substr(0,13) == "Unknown error"` —— 对 `error_code(-1, system_category())` 的 message() 文本断言
- 失败断言 2（error_code_test.cpp:225）：`econd.message().substr(0,13) == "Unknown error"` —— 对 `error_condition(-1, generic_category())` 的 message() 文本断言

根因：boost::system 底层调用 `strerror()`，glibc 对未知 errno 返回 `"Unknown error"`，而 **OHOS musl 返回 `"No error information"`**（本地实测：`strerror(-1)` 在 OHOS 返回 `[No error information]`，`strerror(0)` 同样返回 `[No error information]`）。该断言分支在测试源码中按平台宏区分（Windows/Borland、Linux、hpux、osf、vms 各有不同预期文本），OHOS musl 未在断言矩阵中。错误码的值、类别、比较、std::error_code 互操作等全部 2546 处宏断言中的其余部分均通过。不修改上游测试（保持上游测试原样运行），如实记录平台差异。

---

## 补充说明

### 组件定位与实质适配内容

- **背景**：制品仓聚合包 `boost/1.84.0` 手动编译了 filesystem/regex/program_options/iostreams 四个库。本组件包面向只需要 Boost.System 的下游，可精确依赖 `boost1.84-system/1.84.0`，不必拉取聚合包。
- **选型 A（独立裁剪编译）而非元包引用**：Boost.System 自 1.69 起 header-only，但仍保留了唯一兼容桩翻译单元 `libs/system/src/error_code.cpp`（提供 `dummy_exported_function` 导出符号，供 legacy 消费者链接）。本配方将该 TU 编译为独立 `libboost_system.a`（绕过 b2，E068），并安装全量 boost 头文件（~244MB 源码树），包自包含、无外部 conan 依赖。
- **实质适配**：①b2 不兼容下的组件 TU 手动编译管线（clang++ 单独编译 + llvm-ar rcs）；②复用聚合包已验证的 `0001-ohos-pthread-cancel-fix.patch`（`boost/core/detail/sp_thread_sleep.hpp` 增加特性宏 `BOOST_SP_NO_PTHREAD_SETCANCELSTATE` 守卫，OHOS musl 无 `pthread_setcancelstate`，R8 合规非平台宏）；③上游测试二进制与 test_package 二进制 `-static-libstdc++` 烘入 libc++（OHOS conan buildenv 的 LD_LIBRARY_PATH 不含 `llvm/lib/aarch64-linux-ohos/c++`，动态链接 libc++ 的测试可执行文件运行时 rc=127；静态烘入后仅依赖 libc.so）。

### 上游测试运行方式

B2 在 OHOS 不可用（E068），94 项官方测试改为手动驱动：每项用与库相同的编译参数（`clang++ -std=c++17 -stdlib=libc++ -O2 -DNDEBUG -DBOOST_ALL_NO_LIB -DBOOST_SYSTEM_NO_DEPRECATED -static-libstdc++`）编译，链接 `libboost_system.a` 后直接运行，退出码 0 判 PASS。报告写入 `upstream-tests-report.txt`。

### 产物

- `libboost_system.a`（静态库，R26 检查通过：libboost_system 非 OHOS 系统库名）
- 全量 `include/boost/` 头文件
- CMake 组件：`boost_system_pkg::system` / `boost_system_pkg::headers`（cmake_file_name 用 `boost_system_pkg`，避免与聚合包的 `Boost` config 冲突）
