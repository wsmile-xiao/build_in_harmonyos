# embedded_ringbuf_cpp 1.3 适配笔记

## 编译环境
- 构建系统: custom（上游无构建系统 — 纯头文件模板库；配方 build() 是真实消费者编译+运行探针，test_package 用 CMake）
- 编译日期: 2026-09-25
- 编译器: clang 15.0.4 / clang++ 15.0.4（`aarch64-unknown-linux-ohos`，libc++）
- 状态: built

## 编译步骤

1. **取源**：`conan` 按 `conandata.yml` 下载官方 tag tarball
   `https://github.com/wizard97/Embedded_RingBuf_CPP/archive/refs/tags/1.3.tar.gz`，
   sha256 = `52340d9762e48b507810458507105c79c57c4d9bff2a9faec6c48bbf65ed2290`
   （与 CCI conandata 全值逐字一致，实测复核）。
2. **打补丁**：`build()` 里 `apply_conandata_patches()` 应用
   `patches/0001-ringbufcpp-stddef-self-contained.patch`（日志见 `Apply patch (bugfix)` 行）。
3. **构建期头文件探针**（`build()` 主体，非空 stub）：
   ```text
   RUN: "/data/service/hnp/bin/clang++" -std=c++17 -I"<source_folder>" ringbuf_build_probe.cpp -o ringbuf_build_probe
   RUN: ".../ringbuf_build_probe"
   embedded_ringbuf_cpp build() probe: PASS (add/pull/numElements/isEmpty)
   ```
4. **打包**：`RingBuf*.h → include/`、`LICENSE.txt → licenses/`。
5. **消费者测试**：`conan create` 自动编译并运行 `test_package/test.cpp`
   （12 个消费者用例 / 249 条断言），输出 `CONSUMER TEST PASS`。

本地一次完整 `conan create`（profile=`$TARGET_REPO/ci/conan/profiles/ohos-aarch64`，
`-c tools.build:jobs=4`）实测 **RC=0**。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `#include <RingBufCPP.h>` 作为第一个 include 直接 `error: unknown type name 'size_t'`（4 处，rc=1） | 上游 `RingBufCPP.h` 使用 `size_t` 却只包含 `RingBufHelpers.h`，后者非 Arduino 分支只包含 `<stdint.h>`（不定义 `size_t`）；`<stddef.h>` 才定义 | `patches/0001-ringbufcpp-stddef-self-contained.patch` 补一行 `#include <stddef.h>`（纯标准头、无平台条件分支，符合 R8）；补丁对 `patch_ng strip=0`（conan 默认）自证可应用且与目标树逐字节一致 |
| 2 | 上游唯一示例 `examples_no_arduino/test.cpp` 无法编译 | 它 include 了 tag 1.3 中不存在的 `RingBuf.h`（实测 `fatal error: 'RingBuf.h' file not found`，rc=1） | 不改上游示例；**不计入**测试面，N 按四口径清点为 0 并归因（见 test_package/MANIFEST.yml 头部） |
| 3 | G1 要求 `def build(` 而上游无可构建目标 | G1 是纯文本门禁、无 package_type 例外分支 | `build()` 做真实消费者编译+运行探针（非空 stub），同时产出 `Calling build()` / `Apply patch` / `RUN:` 三个干净轮标志 |
| 4 | `add(obj, overwrite=true)` 在缓冲满时返回 `false` | 上游文档语义即如此（README：`Return false on a full buffer`；返回值表示"当时是否还有空位"），但**仍会写入** | 消费者测试按文档语义写断言（`had_room == (i<=4)`），并断言覆盖确已发生（pull 出新值）；不修改上游行为 |
| 5 | profile 的 `compiler.cppstd=17` 直接拼 `-std=` 得到 `-std=17` 非法 | 裸数字形式需要 `c++` 前缀 | 配方内按 `c++`/`gnu++` 前缀判定后再拼接 |

## 源码修改

- `patches/0001-ringbufcpp-stddef-self-contained.patch`（bugfix）：
  `RingBufCPP.h` 在 `#include "RingBufHelpers.h"` 之前补 `#include <stddef.h>`，
  使 README 记载的 `#include <RingBufCPP.h>` 用法自包含。仅此 1 处、2 行新增。
- 无 `__OHOS__` 平台条件分支（R8 合规）。

## 依赖版本

- 零依赖（header-only，`requirements()` 为空；W0 依赖实查 `conan list -r=ohpcd` 远端可用，本包无硬依赖）。
- 构建工具：profile 提供 `tools.build:compiler_executables`（`/data/service/hnp/bin/clang++`）、CMake 4.1.2。

## 测试与验证结果

```text
# 上游测试清点（N=0，四口径）
git clone --depth 1 https://github.com/wizard97/Embedded_RingBuf_CPP && cd Embedded_RingBuf_CPP
git ls-tree -r --name-only HEAD            # 8 个文件，无 tests/ 目录
grep -rInE "assert\(|TEST\(|CPPUNIT_TEST|BOOST_TEST" .   # 0 命中（源码宏数 = 0）
# 唯一含 test 的文件：
clang++ -std=c++17 -I . examples_no_arduino/test.cpp
  → fatal error: 'RingBuf.h' file not found  (rc=1)

# 消费者测试（鸿蒙特有测试行）
clang++ -std=c++17 -Wall -Wextra -I <交付头目录> test_package/test.cpp
  → TOTAL cases=12 pass=12 fail=0 assertions=249 assertion_fail=0
  → CONSUMER TEST PASS (rc=0)

# conan create（设备实测）
conan create archives/e/embedded_ringbuf_cpp/1.3 \
  -pr:h=$TARGET_REPO/ci/conan/profiles/ohos-aarch64 \
  -pr:b=$TARGET_REPO/ci/conan/profiles/ohos-aarch64 -c tools.build:jobs=4
  → RC=0；Calling build() / Apply patch / RUN: / CONSUMER TEST PASS 齐全
```

### 已知限制（如实申报，非 PASS 项）

1. **上游测试 0 个可运行入口**（N=0，N'=0）：上游无测试框架、无 `make check`/`ctest`/`meson test`，
   唯一含 test 的示例本身不可编译。替代验证 = `test_package/` 的 12 个消费者用例 + 构建期探针。
2. **无多线程并发用例**：OHOS/非 Arduino 分支 `RB_ATOMIC_START/END` 展开为普通 `{ }`，
   没有真实互斥；写并发用例会是真竞态。上游 README 明示其它平台需自行实现这两个宏。
   消费者测试只断言该宏抽象已定义且可嵌套（用例 12）。
3. **`#warning` 常驻**：非 Arduino 分支恒有 2 条 `#warning`（ISR 不安全提示），属上游设计提示；
   下游若开 `-Werror` 需自行处理。

## 交付物

| 文件 | 说明 |
|------|------|
| `include/RingBufCPP.h` | 模板库主头（含 0001 补丁，自包含） |
| `include/RingBufHelpers.h` | 原子宏/平台辅助头（上游原样） |
| `licenses/LICENSE.txt` | MIT 许可证 |
