# lzham 1.0-stable1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-07
- 编译器: clang/clang++ 15.0.4 (OHOS SDK 26.0.0.18, target aarch64-unknown-linux-ohos)
- 状态: built

## 编译步骤

```bash
# 源码: 官方 tag v1_0_stable1 (https://github.com/richgel999/lzham_codec)
# SHA-256: 4f4f874706763b3a6e3d6dfff666a1e850ca1d92fd9240b2a14365c5864a0057

export CC=/data/service/hnp/bin/clang CXX=/data/service/hnp/bin/clang++
export LD_LIBRARY_PATH=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib:$LD_LIBRARY_PATH

cmake -S . -B build-ohos \
  -DCMAKE_SYSTEM_NAME=OHOS \
  -DCMAKE_SYSROOT=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot \
  -DCMAKE_C_COMPILER=$CC -DCMAKE_CXX_COMPILER=$CXX \
  -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=ON -DBUILD_X64=ON \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5
cmake --build build-ohos -j4
```

产物: liblzhamdecomp.so / liblzhamcomp.so / liblzhamdll.so / lzhamtest

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `lzham_types.h` 中 `INT32_MIN`/`INT32_MAX` 等常量与 OHOS musl `stdint.h` 宏冲突，编译报 `expected ')'` | 上游只对 Apple/FreeBSD/NetBSD 做了 `#undef`，未覆盖 OHOS；musl stdint.h 将这些名字定义为宏 | `lzham_types.h` 平台守卫追加 `\|\| defined(__OHOS__)`（与 Apple/BSD 同一模式） |
| 2 | CMake 4.x 拒绝 `cmake_minimum_required(VERSION 2.8)` | 上游 2015 年 CMake 版本过旧，CMake >= 3.5 已移除旧兼容 | 配置时加 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`（不改上游文件） |
| 3 | lzhamtest 间歇性 `lzham_realloc: bad ptr` 断言（Release 下 ~60-80% 失败；ASan 构建 100% 通过） | musl malloc 对极小分配（2/3 字节）只保证 8 字节对齐，而 lzham 全部内存要求 `LZHAM_MIN_ALLOC_ALIGNMENT`(16) 对齐；glibc 上 malloc(1..16) 恒 16 对齐故上游正常 | `lzham_mem.cpp` `lzham_default_realloc`：初始分配非 WIN32 改用 `memalign(LZHAM_MIN_ALLOC_ALIGNMENT, size)`；movable realloc 返回的指针若未 16 对齐则拷贝到 `memalign` 新块并释放旧块 |
| 4 | 首次 `BUILD_X64=OFF` 构建出 32 位产物无法执行 | 上游选项语义：OFF 会追加 `-m32` | 目标为 aarch64，必须 `BUILD_X64=ON` |

## 源码修改

- `patches/` 下由 refresh-patch --auto 生成的补丁，包含上述 #1、#3 两处源码修改：
  1. `lzhamdecomp/lzham_types.h` — __OHOS__ 加入 stdint 宏 undef 守卫
  2. `lzhamdecomp/lzham_mem.cpp` — 分配器强制 LZHAM_MIN_ALLOC_ALIGNMENT(16) 对齐（musl 兼容）

## 依赖版本

- 无第三方外部依赖（仅系统 pthread / 标准 C/C++ 库），L0i 依赖门禁为自身库消费，非阻塞项。

## 验证结果

### 上游测试枚举台账（双口径）

统计口径说明：lzham 上游无 CTest/GTest 框架，唯一用户测试程序为 `lzhamtest`（命令行 c/d/a 三模式 + 全选项）。样例 example1-4 属样例程序，不计入独立上游用例（按规则列入台账但不计数）。

| 入口 | 类型 | 独立上游用例 | 是否实际运行 | 结果 |
|------|------|------------|------------|------|
| lzhamtest/lzhamtest.cpp | 用户测试源（唯一测试程序） | ✅ 是（1 个可执行） | ✅ | 全部模式通过 |
| lzhamtest/timer.cpp/.h | 测试辅助（计时） | ❌ 非独立用例 | - | - |
| example1/example2/example3/example4 | 样例程序 | ❌ 样例不计入 | 随构建编译 | 编译通过 |
| include/lzham*.h / zlib.h | 框架头/API 头 | ❌ 非用例 | - | - |
| 测试脚本 / fixture / 基准 | 无 | - | - | - |

双口径统计：

- `source_declared_total` = 1（lzhamtest 独立测试程序）
- `configured_executable_total` = 1（OHOS 配置实例化 lzhamtest）
- `executed_passed_total` = 1，失败 = 0，未运行/未实例化 = 0
- 全量通过率 = 1/1 (100%)；当前配置可执行集合通过率 = 1/1 (100%)

逐项映射：源码声明（lzhamtest.cpp main）→ 构建条件（CMake add_executable lzhamtest → link lzhamdll）→ 实际执行（./lzhamtest 各模式，见下）。

### 实际执行证据（exit code 全为 0，decompressed compared OK）

```bash
# 压缩+即时解压验证 (-v)，覆盖 -m0..-m4 全级别 / 多文件 / 多字典 / 多选项
./lzhamtest -v -m0..4 c README.md ...         # 5/5 pass
./lzhamtest -v -m2 c CMakeLists.txt           # pass
./lzhamtest -v -m2 c lzhamtest.cpp            # pass (54826B -> 11451B, ratio 79.11%)
./lzhamtest -v -m1 a <dir>                    # 递归模式 pass
./lzhamtest d v2.lzham v2.dec                 # 解压 pass，cmp 字节一致
./lzhamtest -v -m2 -e c ...                   # 确定性解析 pass
./lzhamtest -v -m2 -i c ...                   # 压缩器重初始化 pass
./lzhamtest -v -u -m2 c ...                   # 无缓冲解压 pass
./lzhamtest -v -m2 -t0 c ...                  # 单线程 pass
./lzhamtest -v -m2 -h4 c ...                  # Huffman 更新频率 pass
./lzhamtest -v -m2 -r c ...                   # 随机参数 pass
./lzhamtest -v -m2 -d28 c ...                 # 256MB 字典 pass
./lzhamtest -v -m4 -x -d15 c ...              # 极限解析 pass
```

musl 对齐修复后连跑 8 次 -m4 -d15 及 5 级别各 1 次 + 3 种文件尺寸全部 exit 0、compared OK。

### 后续步骤

- 需在 conan 配方完成 test_package、消费者验证、finish、W2/W3（见本目录 conanfile.py / test_package/）。
---

**编译结束**: 2026-09-08 01:18
**最终状态**: built
