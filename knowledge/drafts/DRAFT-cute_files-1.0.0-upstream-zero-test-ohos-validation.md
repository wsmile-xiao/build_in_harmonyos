# DRAFT-cute_files-1.0.0-upstream-zero-test-ohos-validation：单头文件库上游零测试入口的可审计证据记录与 OHOS 替代验证

> Contributor: pc1-69 | Status: Draft | Updated: 2026-08-31
> Source: cute_files 1.0.0 R02（上游测试入口台账）/ R03（W3/finish 基线豁免复验）/ R04（预提交原子性审计）

## 问题（现象）

- 单头文件库 `cute_files` 的官方源码**没有任何自身上游测试入口**。
- 适配报告里不能把"上游测试通过"写成已执行事实（没有可执行入口），也不能把零入口记为"跳过/通过"（语义错误）。
- 需要一套**可审计的搜索范围 + 计数规则 + 零入口证据 + 实际可运行的替代验证**，清楚区分"上游 0"与"适配后实际执行"。

## 根因

- `cute_files` 是 Randy Gaul `cute_headers` 集合内的一个单头文件库（`cute_files.h`，v1.0，Copyright 2017），其官方源码形态就是单头文件，不含独立测试套件。
- `cute_files.h` 现位于官方归档库 `cute_headers_deprecated`（2022-11-10 从主集合 `cute_headers` 移入），两处均无 test/ 目录、无 CI 测试脚本；头文件内仅提供 `cf_do_unit_tests()` 辅助自检函数（打印错误到 stdout，非独立可运行测试入口）。
- 上游仓库把测试按单头库拆散：主集合 `cute_headers` 的 6 个测试相关条目全部属于 `test_cute_tiled`（cute_tiled 库专用），与 `cute_files` 无关。

## 可复用方案

### 1. 可审计的零入口证据（搜索范围 + 计数规则）

- 搜索范围：`git clone --depth 1` 上游两个官方仓库全树
  - `https://github.com/RandyGaul/cute_headers_deprecated.git`（cute_files.h 现所在）
  - `https://github.com/RandyGaul/cute_headers.git`（单头集合主仓库）
- 计数规则：`git ls-tree -r --name-only HEAD` 全树扫描，匹配
  `(^|/)(test|tests|unittest|spec|check|benchmark)(/|\.|$)|(^|/)(test|tests)[._-]|ctest|CMakeLists.*(test)|\.github/|\.gitlab|travis|appveyor`
- 结论：deprecated 仓库 18 个头文件，测试入口计数 0；主仓库 6 个测试相关条目全部归属 `test_cute_tiled`，cute_files 相关计数 0。
- 零入口结论必须注明是"未发现可运行的上游测试入口"，不是"测试通过"，也不是"跳过"。

### 2. 实际可运行的 OHOS 替代验证

- 在 test_package 中新增消费者视角测试：`test_cute_files.c` 定义 `CUTE_FILES_IMPLEMENTATION` 后真实调用
  `cf_file_exists` / `cf_dir_open` / `cf_read_file` / `cf_dir_next` / `cf_match_ext`，遍历真实目录并断言。
- 在 `-pr:h ohos-aarch64` profile（clang aarch64 OHOS）下 `conan create` 实际执行 test_package，
  断言 7/7 通过（`HMBS_TEST_PACKAGE_RESULT: PASS`，EXIT 0），验证 OHOS UNIX 兼容路径
  （`CUTE_FILES_PLATFORM == CUTE_FILES_UNIX`，POSIX dirent/stat/unistd）。

### 3. 统计口径

- 上游用例数 = 0（可审计搜索计数）。
- 适配后新增鸿蒙特有测试 1 个（7 项断言），属"上游无测试、适配后补全"。
- 通过率仅按**实际执行**的结果口径申报，不把 0/0 写成 100%，也不把零入口当作通过。

## 验证（真实证据引用）

| 门禁 | 结果 | 证据 |
|---|---|---|
| 上游测试入口台账 | 0（零入口） | R02 git 全树扫描计数 |
| OHOS test_package | 7/7 断言通过，EXIT 0 | conan create -pr:h ohos-aarch64 实际执行 |
| conan-verify | G1-G4 PASS | R02/R03 报告 |
| W3/finish | prdiff 模式 JC pass，Pass rate 100% | R03 基线豁免复验（三条基线路径隔离后 SHA-256/Git 状态一致） |
| 原子性审计 | pre_delivery_atomicity_pass | R04 PR 白名单 9 文件未 staged |

## 常见误判与适用边界

- **误判 1**：把"上游无测试"写成"上游测试通过"。→ 必须区分"上游 0"与"适配后实际执行"。
- **误判 2**：把零入口记为"跳过/通过"。→ 只能记为"未发现可运行入口 + 实际补充的替代验证"。
- **误判 3**：把某个集合仓库内**其他单头库**（如 test_cute_tiled）的测试算作本库测试。→ 必须逐条目归属核验。
- **适用边界**：本方案**不是**任意库跳过上游测试的通用豁免。仅当满足以下全部条件时才适用：
  1) 完成真实、可审计的上游搜索（范围 + 计数规则 + 逐条目归属）；
  2) 有实际在 OHOS 目标路径运行、调用库 API 的有效替代测试；
  3) 报告中如实区分"上游 0"与"适配后实际执行"，不编造测试数量/上游结果/知识编号/PR 链接。

## 查重差异

- 现有最相近草稿 `DRAFT-zstd-upstream-test-evidence-boundary` 针对 zstd 具体测试开关
  （ZSTD_BUILD_TESTS=OFF、/bin/sh 缺失、golden data、fuzz），主题是"上游有测试但 OHOS 不可运行"；
  本条主题是"上游本就没有任何可运行测试入口"的可审计零入口证据 + 替代验证，错误特征、根因、方案均不同，不构成重复。
- 其余命中（E229/E241/E251/E281/E298 及 DRAFT-protozero 等）为其他库的测试/构建问题，与本条主题无重复。
