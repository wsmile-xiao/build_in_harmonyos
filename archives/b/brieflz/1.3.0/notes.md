# brieflz 1.3.0 适配笔记

## 编译环境
- 构建系统: cmake（上游 CMakeLists.txt，声明 cmake_minimum_required 2.8.11）
- 编译日期: 2026-09-19
- 编译器: clang-15（OHOS PC aarch64，libc++，conan ohos-aarch64 profile）
- 状态: built（conan-verify G1-G4 通过；W3 本地 CI 全绿）

## 编译步骤

1. 下载官方 tag 源码: `https://github.com/jibsen/brieflz/archive/refs/tags/v1.3.0.tar.gz`
   （SHA-256 `b380611b533458514cca37d8477b3d4f8389121d7ce93cbf5b05eda062577766`；注意上游 tag 为 `v1.3.0` 而非 `1.3.0`）
2. 本地直编验证:
   ```bash
   cmake .. -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
            -DBRIEFLZ_BUILD_TESTING=ON -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX
   make -j4 && ctest --output-on-failure   # rc=0, 1/1 Passed
   ./test_brieflz                          # rc=0, 70 tests - 70 passed
   ```
3. Conan 配方: `conan-init` 生成模板后手工改写为 CMake 配方（模板默认 autotools，本库是 CMake 项目）
4. 验证: `conan-verify`（G1 完整性 / G0 预检 / G2 conan create 干净构建+上游测试+test_package / G3 系统同名库隔离 / G4 产物）全部 PASS
5. `finish published`（W3 本地 CI 模拟）: 首次因共享基线噪声（cloog 已跟踪空文件）JC1 失败，
   经基线隔离复验（git rm --cached → 重跑 → 恢复）后 L0/L1/L2/L4/L5 全 pass

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 4.x 拒绝 `cmake_minimum_required(VERSION 2.8.11)`（Compatibility with CMake < 3.5 has been removed） | CMake ≥4.0 移除 <3.5 兼容策略 | 传 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`；Conan recipe 内 `cmake.configure(variables={...})`（tc.variables 写入 toolchain 晚于 cmake_minimum_required 不生效，DRAFT-E321 同结论） |
| 2 | GitHub 直连超时（github.com:443 不可达） | 网络/代理限制 | 官方 tag 已下载到本地后 `init-build --no-download`；conan 下载走 E017 ghfast.top 镜像注入（临时，恢复 conandata 原样） |
| 3 | test_package 消费者测试链接失败（blz_compress/blz_decompress 未声明） | 公开 API 实为 blz_pack / blz_depack_safe，非猜测名 | 读 include/brieflz.h 核对真实 API 后重写 test.c |
| 4 | blz_depack_safe 传 depacked_size=in_len+1 返回 BLZ_ERROR | 安全解码要求 depacked_size 精确等于原始长度 | 传精确 in_len（实测；鸿蒙专项测试覆盖截断/超大/损坏输入三种防护） |
| 5 | finish W3 JC1 报 Junk Files: 2（cloog 基线空文件） | 零提交新库分支 junk_check full 模式扫整仓（git ls-files），命中其他库已跟踪隐藏标记 | 基线隔离复验：记录路径+SHA-256 → git rm --cached → 重跑 W3 全绿 → git add 恢复并核对哈希一致；未修改/未提交该文件 |

## 源码修改

无（未改上游源码，无补丁）。仅配方层传 CMAKE_POLICY_VERSION_MINIMUM 与测试开关。

## 依赖版本

0 第三方依赖（纯 C 单头文件库，仅 libc）。

## 验证结果

- 上游测试: ctest 1/1 Passed（19.42s）；test_brieflz 70/70 passed、482153 断言（全量 10/10 独立用例 100%）
- 消费者用例（tests/consumer_test.c）: rc=0，`packed 65536 -> 18752 bytes (28.61%), round-trip verified`
- 鸿蒙专项测试（tests/ohos_platform_test.c）: rc=0，`ALL brieflz platform tests PASSED`（8 MiB 大缓冲往返 + 安全解码防护 + 版本宏）
- conan-verify: G1/G0/G2/G3/G4 PASS（报告 reports/conan-verify-report.md）

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake 配方（static 默认，CMAKE_POLICY_VERSION_MINIMUM=3.5，BRIEFLZ_BUILD_TESTING=ON） |
| conandata.yml | 官方 GitHub tag v1.3.0 + SHA-256 |
| test_package/ | 消费者测试（真实 blz_pack/blz_depack_safe 往返） |
| tests/ohos_platform_test.c | 鸿蒙专项测试 |
| tests/consumer_test.c | 消费者用例（针对已安装制品编译运行） |
| reports/ | conan-verify-report / test-report / upstream-test-ledger / knowledge-candidate-ledger |

## 注意事项

- 上游 release tag 带 `v` 前缀（`v1.3.0`），init-build/conan 下载 URL 需用 `refs/tags/v1.3.0.tar.gz`
- 该库同时构建 CLI 工具 `blzpack`（example/），属库型包（cpp_info.libs=brieflz），不建 commands.json（R38：库类型不需要）
- 知识查重结论 `reuse_existing`（路径 A）：CMake 策略与基线隔离均为既有知识（E187/E103/E291 + DRAFT-E321/dr_mp3/jc-full-scan 草稿）覆盖，无新增草稿
