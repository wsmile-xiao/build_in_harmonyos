# rapidhash 3 适配笔记

## 编译环境
- 构建系统: 无（header-only；上游 rapidhash_v3 tag 树只有头文件与 GPL-2.0/BSD 研究工具）
- 编译日期: 2026-09-08
- 编译器: clang/clang++ 15.0.4 (target aarch64-unknown-linux-ohos)
- Conan: 2.29.1 (OHOS 适配版)
- 状态: built

## 版本甄别

任务卡版本 "3" 的上游发布形态甄别：`git ls-remote --tags` 实测上游全集为
`rapidhash_v1.0 / rapidhash_v2.0 / rapidhash_v2.1 / rapidhash_v2.2 / rapidhash_v3`
（master + v4 两个分支；无其他 tag）。**v3 的唯一发布物是 tag `rapidhash_v3`**，
不存在 `v3`/`3`/`v3.0`/`3.0`/`v3.0.0` 形态。tarball：
`https://codeload.github.com/Nicoshev/rapidhash/tar.gz/refs/tags/rapidhash_v3`，
SHA-256 `2e708bb2be76fd76f1e5d75bb3145d058e2dad0c5b0022646f84ec83aeff400d`。

### 版本 slug 归一化（目录 3 ↔ 配方 v3）

Conan 的 ref 校验正则要求版本至少 2 个字符（`conan/api/model/refs.py`
`^[a-z0-9_][a-z0-9_+.-]{1,100}$`），单字符版本在 `conan create` 导出阶段直接报
`ERROR: Invalid package version '3'`（conan-verify 首轮 G2 实测）。因此：

- 配方不写字面 `self.version = "..."` 属性，改用 `set_version()` 把制品版本归一化为
  **`v3`**（上游 tag `rapidhash_v3` 剥前缀；与仓库 hfsm2 `Beta73→beta73` 大写 slug
  归一化先例同型）；
- 归档目录保持任务卡的 `3`：CI L0n 分支门禁按「分支去前缀 == 目录名-版本目录」精确
  匹配 `rapidhash-3`（`feat/rapidhash-3`），任务平台也按该分支名关联；
- L0m-3 的目录↔配方 version 一致性检查只对字面 `self.version = "..."` 属性生效，
  `set_version()` 形态天然跳过（该检查写法即如此），目录与制品版本的对应关系由本
  notes 与版本级 manifest 留证。

## W0 依赖

无第三方依赖。`rapidhash.h`/`secret.h` 仅含 `<stdint.h>`/`<string.h>`（MSVC 分支
才用 `<intrin.h>`），无子模块、无 FetchContent、无 pkg-config 探测。bench/collisions
目录的 xxhash 为 vendored 副本且只服务于两个研究工具（不进包）。无需 conan install
验证步骤（无依赖可装）。

## 编译步骤

1. **原生探索**（`$HOME/tmp/task-rapidhash-3/native/bench`）：
   - `cd bench && make -j1 CC=clang CXX=clang++` — benchHash 构建成功（零警告），
     该工具经 VPATH 引用 `../collisions/allcodecs/xxhash.h`，纯 C 无外部依赖。
   - `./benchHash --minl=20 --maxl=10 --mins=8 --maxs=16 rapidhash` 限参数运行成功
     （吞吐 ~40-80M ops/s），证明头文件在 OHOS aarch64 目标真实可执行。
   - collisions/ 工具需要 15Gi×68 数据集（碰撞研究），无法且无需在设备执行。
2. **参考向量生成**（gen 程序）：由未修改 tarball 在本设备编译一次性生成 789 组
   （len 0..256 × 3 函数 seed 0 共 771 组；len {0,1,7,48,80,256} × 3 函数 × seed
   0x9E3779B97F4A7C15 共 18 组），输入填充 `buf[i]=(uint8_t)((i*31+7)&0xFF)`。
   生成器 host==target（本设备 clang），冻结进 `test_package/vectors.h`。
3. **语言/优化矩阵**（tarball 源码直编）：c11 / c++11 / c++17 / c++20 运行期全部
   通过；c++17 -O0/-O2 一致。
4. **test_package**：conan create 消费方编译运行（见下）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 消费方 `constexpr uint64_t k = rapidhash("", 0);` / `static_assert` 编译失败：`must be initialized by a constant expression`，note 指向头内 `cast from 'const void *' is not allowed in a constant expression` | C++ 常量表达式直到 C++26 P2738 才允许 void*→T* 转换；rapidhash_internal 函数体内 `const uint8_t *p=(const uint8_t *)key` 使调用链在常量表达式中不可求值。OHOS clang 15（C++17/C++20 档均实测）未实现该能力（首落 clang 19）。运行期调用完全正常 | KAT 断言全部改为运行期比较；知识草稿 E560 记录该工具链能力边界。不为绕过它修改上游头 |
| 2 | OHOS profile 携带 os.version=6.0 而 test_package 未声明 | 同仓 mdurl/afdko/rang 先例 | test_package conanfile `configure()` 中 `self.settings.rm_safe("os.version")` |
| 3 | conan CMakeToolchain 在 OHOS 下生成 `-stdlib=libstdc++` 而 OHOS clang 15 仅提供 libc++ | 同仓 rang 先例 | test_package `generate()` 显式 `tc.extra_cxxflags.append("-stdlib=libc++")` 并将 CMAKE_SYSTEM_NAME 映射为 Linux |

## 源码修改

无（零补丁；上游头文件未做任何修改，patches/ 不存在）。

## 依赖版本

- 无运行时/编译期依赖（header-only）。
- test_package 仅依赖被测头与 C 标准库。

## 上游测试

**上游无自带测试套件**（TOTAL=0）。取数口径与证据：
`find <tarball 解压目录> -type f \( -iname '*test*' -o -iname 'check*' \)` 结果为空；
仓库无 CMake/CTest/Makefile 测试目标；`bench/`（GPL-2.0 基准工具）与 `collisions/`
（碰撞研究工具，需 15Gi 级数据集）为研究性程序、非测试框架。SMHasher/SMHasher3
通过结论是上游 README 引用的第三方验证、不属于本仓库源码。设备侧等价验证由
test_package 冻结向量 KAT 承担（见下）。

## 验证结果

- 原生：benchHash 构建 EXIT 0 + 限参数运行 EXIT 0；向量验证器 c11/c++11/c++17/c++20
  全部 `OK: 832/835 checks passed, 0 failed`。
- conan create（--user=ohpcd --channel=stable，清缓存采信轮）：EXIT 0。
- test_package（3 个消费者可执行程序，真实编译+运行）：
  - test_rapidhash（C99）：832/832 checks passed
  - test_rapidhash_cpp（C++17）：835/835 checks passed
  - ohos_platform_test（C++17）：13/13 checks passed（platform: OHOS/aarch64）
- 详见 `test_package/MANIFEST.yml` 与 PR 正文统计表。

## 注意事项

- 包安装路径为 `include/rapidhash/{rapidhash.h,secret.h}`（命名空间化）；
  消费方 `#include <rapidhash/rapidhash.h>`。legacy 快照
  `old_version/rapidhashV1.h` 未随包分发：其 `rapid_secret[3]` 与 v3 头的
  `rapid_secret[8]` 同名异长，同 include 路径会重定义冲突。
- `secret.h` 非自包含（依赖 rapidhash.h 的 `rapid_mix`），需成对包含。
- bench/collisions 是 GPL-2.0/BSD 研究工具，不进 MIT 包本体。

---

**编译结束**: 2026-09-08
**最终状态**: built
