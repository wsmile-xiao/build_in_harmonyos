# DRAFT-ohos-configurepy-ldflags-libcxx-quote — 自研 configure.py 生成的 Makefile 链接缺 libc++ + --ldflags 引号陷阱

> Contributor: SEA-111 / Status: DRAFT / Updated: 2026-09-08 / Severity: 2 (medium)

## 相关既有条目（同族差异化定位）

| 既有条目 | 收录状态 | 问题面 | 本 skill 的增量（差异化） |
|----------|----------|--------|--------------------------|
| E247（静态 C API 库的 pkg-config Libs.private 缺 C++ 运行时） | 正式收录 | pkg-config 元数据（C API 消费者场景） | 本 skill 是**自研 configure.py 生成 Makefile**（非 pkg-config），链接命令直接用 $(CXX) 缺 libc++，修法是 configure 期 --ldflags 注入，非改 .pc |
| E191（HarmonyOS clang++ 找不到 libc++，CMake header-only 绕过链接检测） | 正式收录 | CMake 配置期链接检测 | 本 skill 是自研 configure.py（非 CMake），且是**真实链接阶段**缺 libc++ 符号（undefined std::__n1::cerr），需显式注入 -L/-lc++ |
| DRAFT-postgresql-18.3-make-args-shell-quote（make 命令行变量经 shell 传递引号被剥离） | 草稿 | conan→sh→make→recipe-shell→linker 多层 shell 引号 | 本 skill 是 **configure.py 自身 argparse** 对含空格 --ldflags 值的拆分（no such option: -l），发生在 configure 阶段而非 make 传递链 |

## Scope（何时用）

- 三方库用**自研 Python configure.py**（argparse 配置脚本，非 autotools/cmake）生成 Makefile，如 botan-2
- 症状一（链接）：`make botan-test`（或任何 C++ 可执行/测试）报 `undefined symbol: std::__n1::cerr`、`std::__n1::ios_base::init` 等 libc++ 符号
- 症状二（配置）：`./configure.py --ldflags=-L<dir> -lc++`（无引号）报 `configure.py: error: no such option: -l`
- 典型实例：botan-2 2.19.5（configure.py 生成 Makefile，botan-test 链接失败）

## Symptom

```
$ make botan-test
ld.lld: error: undefined symbol: std::__n1::cerr
>>> referenced by main.cpp
ld.lld: error: undefined symbol: std::__n1::ios_base::init(void*)
...
clang-15: error: linker command failed with exit code 1

$ ./configure.py --ldflags=-L/foo -lc++
configure.py: error: no such option: -l
```

## Root Cause

1. **链接缺 libc++**：自研 configure.py 生成的 Makefile 链接命令直接用 `$(CXX)`，但 OHOS 沙箱 clang++ 链接可执行文件时不自动附加 libc++（SDK 的 libc++ 在 `llvm/lib/aarch64-linux-ohos/`，不在默认搜索路径）。`std::__n1` 是 libc++ 的 inline namespace `__1`，符号在 libc++.so 中，未链接即报 undefined。
2. **argparse 引号陷阱**：configure.py 用 argparse 解析 `--ldflags`，shell 会把未加引号的 `--ldflags=-L/foo -lc++` 拆成两个 argv（`--ldflags=-L/foo` 和 `-lc++`），argparse 把 `-lc++` 当成未知选项 → `no such option: -l`。必须整体加引号 `--ldflags="-L/foo -lc++"` 让 argparse 收到单个字符串，再由 configure.py 内部按空格 split 传给链接器。

## Recommended Solution

**主方案（configure 期注入 + 引号包裹）**：

```bash
./configure.py --cc=clang --cc-bin=/data/service/hnp/bin/clang \
  --ldflags="-L/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/aarch64-linux-ohos -lc++" \
  --prefix=${PACKAGE_FOLDER} --libdir=${PACKAGE_FOLDER}/lib --includedir=${PACKAGE_FOLDER}/include
```

要点：`--ldflags` 的**整个值**加双引号包裹（含空格与 `-lc++`），configure.py 内部 `options.ldflags.split(' ')` 会正确拆给链接器。

**回退方案（环境变量 LDFLAGS）**：configure.py 支持从环境变量读取（`options.ldflags = update_from_env(options.ldflags, 'LDFLAGS', ...)`）：

```bash
export LDFLAGS="-L<SDK libc++ 目录> -lc++"
./configure.py ...
```

## 单库实证

| 库 | 版本 | 角色 | 结果 |
|----|------|------|------|
| botan-2 | 2.19.5 | 适配方 | 引号包裹 --ldflags 注入 libc++ 后，botan-test 链接通过、make check 实测 2,621,572 测试 2,621,571 PASS |

## 测试覆盖边界

- 通过率口径：上游 `make check`（botan-test）实测 2,621,572 tests / 2,621,571 PASS / 1 expected_fail（DataSinkFlush 临时文件，沙箱限制）；消费者用例 3 断言全过
- 本 skill 只解决"链接缺 libc++ + configure 参数引号"；若目标可见后仍有沙箱运行失败（临时文件/socket 等），按既有 expected_fails 口径记录
