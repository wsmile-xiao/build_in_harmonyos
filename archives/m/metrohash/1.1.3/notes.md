# metrohash 1.1.3 — 适配笔记（OHOS aarch64）

## 来源核验
- 官方仓库：https://github.com/jandrewrogers/MetroHash
- 正式标签：`v1.1.3`（git tag 指向 commit `690a521d9beb2e1050cc8f273fdabc13b31bf8f6`）
- 源码 tarball：`https://github.com/jandrewrogers/MetroHash/archive/refs/tags/v1.1.3.tar.gz`
- SHA-256：`43991740b3e065151dc46fa4336295480a27913c42b45a42bbf7c760cade4229`（tarball 实测）
- 许可证：Apache-2.0（LICENSE）
- 平台任务：7320（`metrohash/1.1.3`，依赖活动 activity_id=6）

## 结构
- 非密码学哈希库：src/ 下 metrohash.h（总入口）+ metrohash64/128/128crc 的 .h/.cpp + platform.h + testvector.h（官方校验向量）
- **tarball 无构建系统、无测试程序**（全量 11 个文件，无 tests/、sample/、CMakeLists）
- CRC 变体（metrohash128crc.cpp）使用 x86 SSE4.2 intrinsics（`_mm_crc32_u64` 等），**aarch64 不可编译**；配方仅编入可移植的 metrohash64.cpp + metrohash128.cpp，CRC 头文件仍随包发布（总入口 metrohash.h 的包含链完整），CRC 函数在 aarch64 上不可用为平台事实
- 依赖：无任何第三方依赖（C++11，仅标准库）

## 分支基线说明
- 分支 `feat/metrohash-1.1.3` 基于 fork `origin/main`（9b49d7903），理由同前（W3 JC6 原子性判定用 origin/main...HEAD；fork main 为 upstream main 祖先，PR diff 不受影响）

## 上游测试（四维账本）
- **N_static（静态声明）= 0**：tarball 全量文件清点（11 个文件）无 tests/、sample/ 目录，无任何自动化测试程序；`grep -rc TEST/assert` 源码亦无用例。清点证据：tarball 文件清单（LICENSE、README.md、src/{metrohash.h, metrohash64.h/.cpp, metrohash128.h/.cpp, metrohash128crc.h/.cpp, platform.h, testvector.h}）
- **上游测试资产**：src/testvector.h 提供**官方校验向量**（63 字节测试键 test_key_63 + 64/128 位 + CRC 变体 × seed 0/1 的期望哈希）——非可执行程序，本适配的消费者测试以其非 CRC 向量为断言依据（等价于消费上游官方数据）
- **N_executed = 0**（上游无自动化测试可执行，如实申报）
- **新增消费者测试 N_consumer = 1（10 项断言）**

## 消费者测试（设备实测）
- `test_metrohash.cpp`：链接打包库（CMakeDeps + find_package）
  - 8 项官方向量校验：metrohash64_1/2、metrohash128_1/2 × seed 0/1，输出与 testvector.h 期望十六进制逐字节一致（**上游官方数据在本平台复现**）
  - 2 项类 API 一致性：MetroHash64/128 的流式（Update+Finalize）与一次性静态 Hash() 输出逐字节一致
- 退出码 0 判定通过；证据：reports/conan-create.log

## 试编译迭代记录（消费者 API 口径）
- 静态 `MetroHash64::Hash(buffer, length, hash, seed=0)`：hash 参数在 seed 前（首轮按 (buf,len,seed,hash) 误写编译失败）
- 类流式输出与一次性输出一致，但类静态 Hash() 与 C 函数 metrohash64_1 语义不同（不同哈希值），消费者断言不应跨语义比较

## 配方要点
- 无上游构建系统：配方在 build() 中经 `save()` 写入自带 CMakeLists.txt（编译 metrohash64.cpp + metrohash128.cpp，include src/），CMake 变量传源目录（R33 合规），configure 用 build_script_folder 指向 build 目录
- CRC 变体排除为**架构事实**（SSE4.2 为 x86 专属，非 OHOS 缺陷）；平台宏未注入上游源码（无补丁）

## 路径 B 判断（结论：不走 B，纯路径 A）
- 零补丁、零上游修改；"无构建系统小库用配方自带 CMakeLists"在本仓已有同型实践，无新增跨仓库知识。按纯路径 A 交付。

## 后续
- 状态：built（2026-09-12 finish 收尾）
- 无 commands.json（纯库，无命令行产物）
---

**编译结束**: 2026-09-12 06:15
**最终状态**: built
