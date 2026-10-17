# snappy 1.1.10 — 编译进度

> 档案创建时间: 2026-09-04 01:55
> 最后更新: 2026-09-04
> 当前会话 ID: snappy-1.1.10 (j669539 依赖项池)

## 一、基本信息
| 项目 | 值 |
|------|-----|
| 软件 | snappy |
| 版本 | 1.1.10 |
| 状态 | ✅ success (conan-verify G0-G4+L2/L4/L5 全过; 上游测试 21/21) |
| 构建系统 | cmake |
| 源码路径 | https://github.com/google/snappy/archive/refs/tags/1.1.10.tar.gz |
| sha256 | 49d831bffcc5f3d01482340fe5af59852ca2fe76c3e05df0e67203ebbe0f1d90 |

## 二、适配记录

### 源码获取
- 任务给定的 release asset URL `https://github.com/google/snappy/releases/download/1.1.10/snappy-1.1.10.tar.gz` 实测 404：GitHub API 查证 tag 1.1.10 的 release 存在但 **assets 为空**（上游从未上传 release 附件）。
- 改用 GitHub 官方 tag 归档 `archive/refs/tags/1.1.10.tar.gz`（与仓库内 snappy 1.2.2 归档同模式，符合 R39 官方源要求）。

### 关键修复（3 项，无源码补丁，全部走 conanfile.py 工具链参数）
1. **E103/E187 — CMake 4.x 兼容**：snappy 1.1.10 声明 `cmake_minimum_required(VERSION 3.1)`，本地/CI CMake 4.1.2 已移除 <3.5 policy 兼容，configure 阶段直接报错。修复：`tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"`（知识图谱 E103/E187/E447 已有先例，leveldb 1.23 同款）。
2. **-Werror × clang 15 sign-compare**：上游 CMakeLists 对 Clang 强制 `-Werror`，`snappy.cc:1293` 在 clang 15 (aarch64) 触发 `-Wsign-compare`（unsigned long vs ptrdiff_t，上游 1.2.x 才修复）。修复：`tc.extra_cxxflags.append("-Wno-error=sign-compare")`——按知识图谱原则精准降级单一 warning 类别（E293 模式），不全局禁用 -Werror。
3. **test_package 运行时 libc++_shared.so 加载失败**：编译链接全过，但 test_snappy 运行报 `Error loading shared library libc++_shared.so` + `symbol not found: _Znwm`。根因是**本机 shell 的 LD_LIBRARY_PATH 有被空格污染的条目**（`chipset-pub-sdk:         /system/lib64`，前导空格导致 loader 无法解析该目录）。实测 `env -i`（无 LD_LIBRARY_PATH）或干净 `LD_LIBRARY_PATH=/system/lib64` 下测试全过——OHOS loader 默认搜索 /system/lib64。配方本身无需修改，属本机环境缺陷。⚠️ 此问题可能影响本机所有 C++ 库的 test_package 运行验证，值得平台侧关注。

### 上游测试（真实执行，非跳过）
- release tarball 的 `third_party/{googletest,benchmark}` 子模块为空目录（tarball 天然不含子模块内容）。
- 为验证上游测试，手动放置 googletest v1.13.0 到 third_party/，独立 cmake 构建 `snappy_unittest`：
  - 需额外 `-Wno-error=implicit-int-float-conversion`（googletest 1.13 自身在 -Werror 下的问题，上游 -Werror 全局传播）
  - 运行：**21/21 PASSED**（CorruptedTest 1 + Snappy 17 + SnappyCorruption 3，含 testdata 全量回环），总耗时 ~32s
- 配方本身保持 `SNAPPY_BUILD_TESTS=OFF`（零 conan 依赖原则：不把 gtest 打进依赖链，CI 干净构建口径），测试覆盖说明写入 test_package/MANIFEST.yml。

### SIMD/CPU 特性检测观察（路径 B 素材）
- snappy CMake 用 `check_cxx_source_compiles` 编译期探测 SSSE3/X86_CRC32/BMI2/NEON_CRC32/NEON，交叉编译（aarch64-ohos）下 x86 探测自动失败、NEON 探测成功——**纯编译期探测设计对交叉编译友好，无 try_run**，无需任何适配。无 OHOS 特有差异。

## 三、knowledge_gained（路径 B 素材记录）
1. **老 CMake 项目 × CMake 4.x**（已有知识条目 E103/E187/E447，本次复用验证，无需新条目）：`cmake_minimum_required(VERSION <3.5)` 在 CMake 4+ 一律 configure 失败，统一处方 `CMAKE_POLICY_VERSION_MINIMUM=3.5`。
2. **上游 -Werror × 新版 clang 误报**（已有先例 E293 模式，本次为 sign-compare 类别）：老版本库自带 `-Werror`，新版 clang 诊断更严导致历史代码误报。处方：**精准降级具体 warning 类别**（`-Wno-error=<category>`），禁止全局 `-Wno-error`（P 原则）。
3. **本机 LD_LIBRARY_PATH 空格污染**（潜在平台环境问题）：本 agent shell 的 LD_LIBRARY_PATH 中 `/system/lib64` 条目前有空格，导致所有依赖系统 libc++_shared.so 的 C++ 测试二进制运行失败。`env -i` 或干净 PATH 可绕过。CI 环境未见此问题（近期 C++ 库 PR 的 test() 均正常）。如其他任务遇到 `Error loading shared library libc++_shared.so`，先检查 `echo "$LD_LIBRARY_PATH" | cat -A`。
4. **release tarball 子模块为空**：GitHub release tarball 不含 submodule 内容，依赖 gtest/benchmark 子模块的上游测试需手动补齐（选代用版本时注意 -Werror 传播问题，见素材 2）。

## 四、验证结果汇总
| 验证项 | 结果 | 证据 |
|--------|------|------|
| conan create (G2) | ✅ PASS | reports/conan-create.log |
| G1/G3/G4 + L2/L4/L5 | ✅ 全 PASS | reports/conan-verify-report.md |
| test_package (C++ API + C API 往返) | ✅ 5/5 断言 | conan create test 输出 |
| 上游 snappy_unittest | ✅ 21/21 | 本 notes 上文实测 |
| sha256 | ✅ 49d831bf...e0f1d90 | conandata.yml |

## 五、源码修改清单
| 文件 | 原因 | 方式 | 补丁状态 |
|------|------|------|---------|
| （无） | 零源码修改 | 工具链参数注入（conanfile.py generate()） | 无需补丁 |

## 六、结束记录
- **最终状态**: success（待 finish published + W4 审计）
- **结束时间**: 2026-09-04
---

**编译结束**: 2026-09-04 02:45
**最终状态**: published
