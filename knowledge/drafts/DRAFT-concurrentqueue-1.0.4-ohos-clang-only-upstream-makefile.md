# DRAFT-concurrentqueue-1.0.4-ohos-clang-only-upstream-makefile — OHOS clang-only 环境下游 Makefile 硬编码 g++ 的透明 shim 验证模式

> **Contributor**: pc3-36 | **Status**: DRAFT | **Updated**: 2026-08-29
> **Severity**: medium | **Category**: ohos / toolchain / makefile / header-only-conan
> **Audience**: 上游使用纯 Makefile recipe 硬编码 `g++`（忽略 `$(CXX)`）的 C/C++ 库，以及 header-only 库的 Conan 2.x 配方作者

## 问题（Problem）

在 OHOS clang-only 环境（本机 clang 15.0.4，`aarch64-unknown-linux-ohos`，无 `g++`/`gcc`）中，运行 upstream 自带的构建/测试 Makefile 时直接失败：

```
make bin/unittests
g++ -c -std=c++11 ... ../c_api/blockingconcurrentqueue.cpp ../c_api/concurrentqueue.cpp
make: g++: No such file or directory
make: *** [makefile:37: bin/unittests] Error 127
```

- 上游 `build/makefile` 与 `tests/unittests/makefile` 的 **recipe 层直接写死 `g++`**（`g++ -c ...` / `g++ -std=c++11 ...`），并未使用 `$(CXX)` 变量；因此 `make CXX=clang++` 覆盖无效（实测无效）。
- 环境无 GCC，仅提供 OHOS LLVM/Clang 工具链，`clang++` 是唯一的 C++ 编译器。

## 根因（Root Cause）

1. 上游 Makefile 的 recipe 将编译器名硬编码（unix 开发者隐含假设 `g++` 恒在 PATH），make 的 `CXX` 内建变量未被 recipe 引用，参数覆盖与 `export CXX` 均不生效。
2. 与知识库既有条目的差异：E053 / E095 覆盖 **autotools/自定义 configure 层**的编译器硬编码（`cc1plus`、`c++`/`g++` 写进 configure），解决路径是 `CXX=clang++` 传参或 sed 替换；本案例是**纯 Makefile recipe 层**（非 configure、非 autotools），且 recipe 完全忽略 `$(CXX)`，传参路线不可用。
3. header-only 特性的二次根因（独立于编译器 shim）：上游 CMake INTERFACE library 把头文件安装到 `include/concurrentqueue/moodycamel/` 子目录，Conan 2.x 配方若沿用默认 `includedirs=["include"]`，消费者 CMakeDeps target 的 include 路径与安装布局不一致，`#include "moodycamel/concurrentqueue.h"` 无法解析。

## 最小方案（Minimal Solution）

### 模式 A：透明 `g++ -> clang++` 作用域 shim（验证上游测试套件用）

```bash
mkdir -p $HOME/tmp/cq-verify/toolchain
ln -sf "$(command -v clang++)" $HOME/tmp/cq-verify/toolchain/g++
ln -sf "$(command -v clang)"   $HOME/tmp/cq-verify/toolchain/gcc
cd <src>/build
PATH="$HOME/tmp/cq-verify/toolchain:$PATH" make bin/unittests   # 同一 make 目标原样执行
./bin/unittests
```

要点与边界：

- **作用域受限**：shim 只存在于临时 PATH 前缀目录，仅对该一次 `make` 调用生效；不写系统目录、不 export alias、不修改上游 Makefile；用完即弃。
- **透明**：shim 是真实可执行文件（符号链接指向 clang++/clang），make 的行为、source list、flags、目标产物与直接运行完全一致，仅编译器实现按 g++/clang++ 命令兼容映射替换。
- 与 E095 forbid_1（禁止创建系统级 `c++`→`clang++` 软链接/alias，理由为污染构建环境、影响其他软件编译器检测）**不冲突**：本模式是显式限定在一次性验证 PATH 前缀内的临时手段，不进入系统 PATH，不改变全局编译器检测；报告必须如实声明"以 clang++ 替代上游写死的 g++ 跑通同一 make 目标"。

### 模式 B：header-only Conan 2.x 配方 include 布局一致性

```python
def package_info(self):
    self.cpp_info.set_property("cmake_file_name", "concurrentqueue")
    self.cpp_info.set_property("cmake_target_name", "concurrentqueue::concurrentqueue")
    self.cpp_info.includedirs = ["include/concurrentqueue"]   # 与上游安装目录对齐
    self.cpp_info.libs = []
```

- 安装布局 `include/<pkg>/moodycamel/*.h` ↔ `package_info.includedirs=["include/<pkg>"]` ↔ 消费者 `#include "moodycamel/concurrentqueue.h"` 三处必须一致，缺一即消费失败。

## R01 真实验证证据（Verified Evidence）

- **官方来源**：`https://github.com/cameron314/concurrentqueue`，标签 `v1.0.4` → commit `6dd38b8a1dbaa7863aa907045f32308a56a6ff5d`（2023-06-19 release），许可证 BSD-2-Clause；tarball SHA-256 `87fbc9884d60d0d4bf3462c18f4c0ee0a9311d0519341cac7cbd361c885e5281`。
- **专用 worktree**：`/storage/Users/currentUser/junshi_liu/worktrees/pc3-36-concurrentqueue-1.0.4`，分支 `feat/concurrentqueue-1.0.4`，HEAD `5292d3091f6c09c860a0071abb81229a481c656a`。
- **smoke test（test_package/test_concurrentqueue.cpp）**：`clang++ -std=c++17 -I <staging>/include -pthread` 编译并运行，输出 `PASS: concurrentqueue 头文件库链接和核心 API 验证通过`，exit 0。
- **上游测试套件（模式 A 验证）**：`PATH=<toolchain>:$PATH make bin/unittests` → `./bin/unittests`，输出 `All tests passed.`，**45/45 项 passed，0 failed**，exit 0（日志存于 R01 验证目录）。
- 本次 R02 仅作**只读路径/哈希核验**复用上述证据，未重跑构建与测试。

## 适用边界（Applicability Boundary）

1. 仅适用于上游 Makefile **recipe 层硬编码编译器名且忽略 `$(CXX)`** 的库；configure/autotools 层的同名问题走 E053/E095。
2. shim 只在"clang-only 环境 + 一次性上游测试验证"场景使用；代码须与 clang 15 `-std=c++11`/`-fno-exceptions` 等 flags 兼容（本案例验证通过）。
3. 报告口径必须如实：`45/45` 是在 **g++→clang++ shim** 下取得，不是原生 g++ 结果；禁止把替代编译器的验证写成上游原构建。
4. 不适用于依赖 GCC 特有扩展、ABI 特性或 gcc 专属内建宏的代码。
5. header-only include 布局一致性仅适用于安装时带子目录头文件的 INTERFACE 库。

## 恢复条件（Recovery Condition）

- 在 CI/runner 安装 g++（GCC）后，原 `make bin/unittests` 直接可跑，无需 shim；或 CI 环境预置等价的 g++→clang++ 命令映射。
- Conan 侧：配方 `package_info` 已按模式 B 对齐布局，任何环境消费者直接 `find_package(concurrentqueue)` + `#include "moodycamel/concurrentqueue.h"` 即可。

## 跨库复用价值（Cross-Lib Reuse Value）

- 上游以纯 Makefile 构建并 recipe 硬编码 `g++` 的 C/C++ 库（尤其单头文件/小型库），在 clang-only runner 上可复用同一诊断路径：先确认 `$(CXX)` 是否被 recipe 引用（grep recipe），再决定模式 A shim 或 `CXX=clang++` 传参。
- header-only Conan 2.x 配方统一检查安装布局 ↔ includedirs ↔ 消费者 include 三处一致性，避免消费时头文件找不到的返工。

## 查重结论（Deduplication Conclusion）

- **E053**（cc1plus→clang++，configure/make 硬编码 cc1plus，方案 `set-env-var`/sed）：不同——本条目为 recipe 层直接写 g++ 且忽略 `$(CXX)`，且验证手段是作用域 shim。
- **E095**（自定义 configure 硬编码 c++/g++）：不同——configure 层 vs makefile recipe 层；E095 forbid 系统级软链接，本模式是受控 PATH 前缀 shim，边界已显式区分。
- **E035**（boost header-only-install）：不同——打包/安装策略，非编译器 shim，也非 Conan include 布局。
- **E001**（PATH 无 cc）/ **E018/E050/E079**（HMDFS 软链接限制）：不同主题。
- **E216-draft**（Makefile-only C 库 lld/LD_LIBRARY_PATH）：不同——解决运行时链接库路径与 recipe 内嵌 source list，非编译器命令 shim。
- **结论**：knowledge/doc 与 knowledge/drafts 均无覆盖"makefile recipe 硬编码 g++ + 作用域透明 shim 验证 + header-only Conan include 布局一致性"的条目，本草稿为新增价值；未使用任何正式 `E###` 编号，未写入正式图谱/索引。