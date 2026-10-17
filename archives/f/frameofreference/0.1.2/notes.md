# frameofreference 0.1.2 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-23
- 编译器: clang 15.0.4 / clang++ (OHOS PC native, aarch64)
- 状态: published

## 编译步骤

```bash
# 上游为 CMake 构建（add_library STATIC + unit test），无 install() 规则
cmake -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX .
make -j2
ctest --output-on-failure   # 1/1 通过 (unit)
```

- 上游同时提供 Makefile（`make` 直接产出 `test` 二进制），两套构建均可编译通过。
- CMake >= 4.0 对 `cmake_minimum_required(VERSION 2.8.7)` 报策略版本错误，
  配方在 generate() 注入 `CMAKE_POLICY_VERSION_MINIMUM=3.5` 解决。
- 上游 CMakeLists.txt 无 install 规则：conanfile.py 的 package() 手动
  复制 include/*.h 与 libFrameOfReference.a（R49 风格产物托管）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 任务头 URL 为仓库主页 https://github.com/lemire/FrameOfReference，非 tarball | 上游仓库已迁移至 fast-pack/FrameOfReference；主页无法直接下载 | 用 GitHub API 核验正式标签 v0.1.2（commit da003110），下载官方 tag tarball |
| 2 | /tmp 满导致 codeload 下载写盘失败 | 环境 /tmp 4.3G 100% | 下载到 $HOME/tmp（大容量分区），并预置 init-build 缓存路径 |
| 3 | CMake 4.1.2 configure 失败（policy） | 上游 cmake_minimum_required 2.8.7 过旧 | 配方 generate() 注入 CMAKE_POLICY_VERSION_MINIMUM=3.5 |
| 4 | make install DESTDIR 无 install 目标 | 上游无 install() 规则 | 配方 package() 手动 copy 头文件与静态库 |

## 源码修改

无补丁（上游源码零改动，全部适配在 conanfile.py 内完成）。

## 依赖版本

- 无第三方依赖（纯 C++11 静态库）。

## 验证结果

```bash
ctest --output-on-failure   # 1/1 passed (unit: 上游压缩/解压自检 + 基准)
./unit sampledata.txt       # 上游基准 exit=0（standard/turbo/turbo64 三档）
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake 配方，package() 托管头文件与静态库 |
| conandata.yml | 官方 tag tarball + SHA-256 72dd18cee302d5df2e880474be9b17f41b5c4a66e6c2919d8f1b46bdc925f251 |
| test_package/ | 消费者往返测试（pack4_8/unpack4_8 + compress/uncompress） |

## 注意事项

- 库导出 pack1_8..pack32_8 / unpack1_8..unpack32_8 与 turbopacking32/64 系列；
  test_package 覆盖 4-bit 路径与 compress/uncompress 全量路径。
- 构建产物仅静态库 libFrameOfReference.a（上游未提供 .so）。
---

**编译结束**: 2026-09-23 00:25
**最终状态**: built

## 知识判定（executor_local_required，2026-09-23）

- 快照：/storage/Users/currentUser/.ohpc-knowledge-snapshots/frameofreference-0.1.2-20260922T154912Z（head 48d9cee6，sparse=knowledge，只读程序性约束）
- 候选：CMake 4.x 拒绝 cmake_minimum_required(<3.5) → 配方注入 CMAKE_POLICY_VERSION_MINIMUM=3.5（-D 命令行，configure variables）
- 等价命中：E103（bump-cmake-minimum-version / fallback cmake-compat-flag：-DCMAKE_POLICY_VERSION_MINIMUM=3.5）、E187（add-cmake-flag：cmake -DCMAKE_POLICY_VERSION_MINIMUM=3.5）、DRAFT-E321（明确"用 cache_variables 走 -D，切勿 tc.variables"——与本轮实际修复路径一致）
- 逐字段适用性验证：error_signature 命中（"Compatibility with CMake < 3.5 has been removed"），root_cause 一致（CMake 4.x 移除 <3.5 兼容策略），rec_approach 一致（-DCMAKE_POLICY_VERSION_MINIMUM=3.5），affected_scope 含 OHOS CMake 4.1.2
- knowledge_decision: reuse_existing（路径 A），不创建草稿
- 基线隔离审计：见 $HOME/tmp/fof-baseline-isolation-audit.json（cloog/kics 空状态文件临时 git rm --cached，复验 W3 后恢复，index blob 与 HEAD 一致）
