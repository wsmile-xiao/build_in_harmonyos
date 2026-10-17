# DRAFT-hexdump-1.0.0-makefile-gcc-hardcode-headeronly：上游顶层 Makefile 硬编码 `g++`，OHOS 工具链仅有 clang++ —— header-only 库用 Conan header-library 免编译配方直接安装头文件

> Contributor: pc4-28 | Status: Draft | Updated: 2026-09-22
> Source: hexdump 1.0.0 适配（PR 分支 feat/hexdump-1.0.0）
> 对应：`knowledge/drafts/DRAFT-hexdump-1.0.0-makefile-gcc-hardcode-headeronly.kv`

## 现象

按上游 README 执行 `make`，立即失败：

```console
$ make
g++ -Wall --pedantic -std=c++14 -o hexdumpExample example.cpp
make: g++: No such file or directory
make: *** [Makefile:6: hexdumpExample] Error 127
```

环境预检同样提示 `cc: 未找到`、`c++: 未找到`（预期：OHOS SDK 工具链
仅提供 `clang`/`clang++` 15，目标 `aarch64-unknown-linux-ohos`，PATH 中
无任何 GNU 编译器）。

## 根因

OHOS PC 工具链基于 LLVM/Clang：`/data/service/hnp/bin/clang` 与
`clang++` 存在，而 `g++`/`gcc`/`cc`/`c++` 均不在 PATH。上游库若在顶层
**Makefile 里直接硬编码 `g++` 编译命令**（未用 `$(CXX)` 且无 configure
阶段），在 OHOS 上必然报 `No such file or directory`（Error 127）。

与既有 E053 的差异：E053 针对 **autotools configure 期 cc1plus 检测失败**
（`configure` 探测 C++ 编译器），本条目针对 **纯顶层 Makefile 直接调用
g++**，且经典场景是 **header-only 库**——库本身没有编译产物需求，
Conan 配方根本不需要执行上游编译命令。

## 方案

1. **判定 header-only**：`package.json` 的 `src` 只列头文件
   （hexdump: `"src": ["hexdump.hpp"]`）、`Makefile` 仅编译示例
   （`$(PROG): example.cpp hexdump.hpp`），无 `.a/.so` 产物 → header-only。
2. **Conan 配方用 `header-library` 模式**：
   - `package_type = "header-library"`，`no_copy_source = True`
   - `build()` 只 `apply_conandata_patches(self)`（patches:{} 为空时无编译
     日志，符合 R34 不伪造）
   - `package()` 用 `copy()` 把 `hexdump.hpp` 装入 `include/`，`COPYING`
     装入 `licenses/`
   - `package_id()` 里 `self.info.clear()`（单一 package_id）
   - `package_info()` 设 `bindirs=[]`、`libdirs=[]`、
     `includedirs=["include"]`，可选 cmake_file_name/target_name
3. **验证示例**：不改上游 Makefile（零补丁），用等价命令手动编译运行：
   ```bash
   clang++ -Wall --pedantic -std=c++14 -o hexdumpExample example.cpp && ./hexdumpExample
   ```
   输出与 README 示例一致（49 行，退出码 0）。
4. **test_package**：真实调用公开 API（`Hexdump`/`CustomHexdump`/
   `CustomHexdumpBase`）做消费者断言（13 项 PASS），禁止空壳。

## 验证

- 鸿蒙专项测试 `ohos_special_test`：10 断言 ALL PASS（rc=0）
  （`__OHOS__`/`__OHOS_FAMILY__`/`__aarch64__` 宏 + 输出格式逐字节断言）
- test_package 消费者 `test_hexdump`：13 断言 ALL PASS（rc=0）
- `conan create`（ohos-aarch64 profile）G2 PASS
- W3/JC 门禁通过（基线隔离复验后），conan-verify 全门禁 PASS

## 适用边界与反例

**适用**：由顶层/子 Makefile 直接硬编码 `g++` 编译命令、且为 header-only
的 C/C++ 库在 OHOS PC 适配；Linux 容器缺 g++ 时同样适用（同类根因）。

**反例/不适用**：
- 有真实编译/链接产物（.a/.so）需求的非 header-only 项目 → 不能套用
  免编译配方；应走 E053（`export CXX=clang++`）或改用 CMake 等构建系统。
- autotools/configure 工程的 cc1plus 检测失败 → E053（set-env-var）。

## 与既有条目差异（七轴摘要）

- exact_duplicate=false、causal_duplicate=false（无同"纯 Makefile 硬编码
  g++ + header-only 免编译配方"条目）
- trigger_overlap=partial（与 E053 共享"g++ 缺失→clang++"触发面）
- solution_overlap=partial（共享"指定 clang++"；本方案实质是免编译配方）
- combination_novelty=true、boundary_novelty=true（组合与边界均新增）