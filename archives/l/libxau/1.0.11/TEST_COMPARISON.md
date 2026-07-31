- **三方库名称**：libxau
- **上游版本**：1.0.11
- **上游仓库地址**：https://gitlab.freedesktop.org/xorg/lib/libxau
- **适配路径**：路径 A（基础适配）
- **使用知识库**：openharmony-compile-agent（E002/HMDFS umask；configure shebang 替换）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | libXau 1.0.11 源码内无 `tests/` 目录，无独立单测框架 |
| 集成测试 | 1 | 上游 `Makefile.am` 声明 `check_PROGRAMS=Autest` + `TESTS=Autest`，源文件 `Autest.c`（77 行，仓库根），覆盖 `XauWriteAuth()` 写入往返 |
| 其他测试 | 0 | `make check` 不递归进 man/，man/ 内也无测试目标 |
| **合计** | **1** | 来源：上游 `Makefile.am`（check_PROGRAMS / TESTS）+ `Autest.c` |

> 实测命令：
> ```bash
> cd libXau-1.0.11
> grep -E 'check_PROG|TESTS\s*=' Makefile.am
> # check_PROGRAMS=Autest
> # TESTS=Autest
> ```

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | 上游无单测框架 |
| 集成测试 | 1 | 不变 | 复用上游 `Autest`：在 `conanfile.py::build()` 末尾 `autotools.make(target="check")` 触发编译与运行；log 显示 `PASS: Autest` |
| 鸿蒙特有测试 | 4 | 新增 | test_package 中 4 项断言：`XauFileName()`、`XauDisposeAuth(NULL)`、`sizeof(Xauth)` ABI、输出完整性；验证 OHOS aarch64 上 `.so` 链接与 API 语义 |
| **合计** | **5** | **+4** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

`Autest.c` 在 OHOS aarch64 上 `make check` 一次通过（`# TOTAL: 1` / `# PASS: 1`），无需任何源码修改，无 patch 注入。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游仅有 `Autest` 覆盖 `XauWriteAuth()` 写入路径，适配后补全了消费者侧覆盖（请在下方说明）

> 若选择「是」，须说明：
> - **补全的测试范围**：在 test_package 中新增 4 项消费者侧断言：1) `XauFileName()` 返回路径或在无 Xauthority 环境下允许 NULL（拒绝空串）；2) `XauDisposeAuth(NULL)` 不 crash（上游手册规定为安全 no-op）；3) `sizeof(Xauth) >= 32` ABI 基本健全性；4) 正常打印完成标记。故意不调用 `XauLockAuth` / `XauReadAuth`（会触及文件系统与 IPC 锁，在裸 OHOS 测试 runner 上行为不稳定）。
> - **补全原因**：上游 `Autest` 是 happy-path 写入测试，缺消费者链接与 API 冒烟覆盖。Conan `conan create` 的 L1/R34 门禁要求 test_package 必须实质调用被测包 API，并经破坏性反向验证。
> - **新增测试文件清单**：
>   1. `test_package/test.c` — 4 项断言（`assertion_count: 4`）
>   2. `test_package/CMakeLists.txt` — `find_package(libxau)` + `target_link_libraries(... libxau::libxau)`
>   3. `test_package/conanfile.py` — 消费者构建与 `ctest` 入口
>   4. `test_package/MANIFEST.yml` — 上游/适配测试声明

## 验证结果

- 编译状态：通过（`conan create` 成功产出 `libXau.so.6` + `xau.pc` + `Autest`）
- 上游测试用例通过率：1/1（100%）（log: `# TOTAL: 1` / `# PASS: 1` / `PASS: Autest`）
- 新增测试用例通过率：4/4（100%）（`XauFileName` / `XauDisposeAuth(NULL)` / `sizeof(Xauth)` / 输出完整性全部 pass）

## 补充说明

- 无上游源码补丁（`patches_applied: []`）；OHOS 适配在 `conanfile.py::build()` 内对 `configure` 做 umask/`#!/bin/sh` shebang 运行时替换
- 构建依赖：`xorgproto/2025.1`（头文件传递）
- 改动摘要：`conanfile.py::build()` 末尾新增 `autotools.make(target="check")` 触发 `Autest`；`test_package/MANIFEST.yml` 声明上游 `Autest` + 消费者 4 项断言
