# fleur 0.3 适配笔记

## 编译环境
- 构建系统: cmake（TARGET_GROUP=production，静态库 + fleurcli CLI）
- 编译日期: 2026-09-26
- 编译器: clang 15.0.4（OHOS SDK llvm）/ clang++
- 状态: built

## 编译步骤

1. `ohc-run.py init-build fleur 0.3 --url=https://github.com/hashlookup/fleur/archive/refs/tags/v0.3.tar.gz`
   - 官方 tag v0.3 归档（commit 5b740578），SHA-256 与上游 `.tarball-sha256` 一致
2. `ohc-run.py lang-preflight fleur 0.3 --src <work>` → exit 0（C，兼容族）
3. 探索编译（CMake，本机 profile）：
   - `cmake -GNinja -DTARGET_GROUP=production -DCMAKE_BUILD_TYPE=Release . && ninja -v`
   - `cmake -GNinja -DTARGET_GROUP=test -DCMAKE_BUILD_TYPE=Release . && ninja -v`
4. `ohc-run.py conan-init fleur 0.3` → 生成配方；核对 CMake 构建后重写 conanfile.py
5. `ohc-run.py conan-verify fleur 0.3` → G1/G0/G2/G3/G4 + L2/L4/L5 全通过
6. `ohc-run.py finish fleur 0.3 built` → W3 本地 CI 模拟通过（期间按基线隔离协议处理
   其他库既有基线文件），submit 就绪

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游测试 suite_2 崩溃（Signal 5） | `fleur_bloom_filter_from_file` 错误路径返回未初始化结构体，`fleur_destroy_filter` → `free(垃圾指针)` | `BloomFilter bf = {0}` 入口零初始化（补丁 0001）；复跑 8/8 通过 |
| 2 | GitHub tar 包缺 Unity 测试子模块 | tar 包不打包 git 子模块内容 | gitcode 镜像克隆 Unity（HEAD 8500dd29）恢复 `external/Unity/src`（E150 复用） |
| 3 | conan-init 生成 autotools 模板 | init-build 将纯 CMake 项目误判为 autotools | 重写 conanfile.py 为 CMake 模板（CMakeToolchain + 手工 package） |
| 4 | W3 本地 CI full 模式命中其他库基线文件 | junk_check 无 PR diff 时全仓扫描 `git ls-files` | 基线隔离复验：`git rm --cached` 隔离 → 复跑 → `git add -f` 恢复（SHA 前后一致） |
| 5 | conan-verify E017 临时注入镜像后残留 gh-proxy 前缀 | verify 工具注入镜像 fallback 后未完整还原 | 恢复官方源 URL 单一条目（审计 P1 R39 修复） |

## 源码修改

- `patches/0001-fleur-fleur.c.patch`（1 行）：`fleur_bloom_filter_from_file` 内
  `BloomFilter bf;` → `BloomFilter bf = {0};`，修复错误路径未初始化结构体导致
  `free(未初始化指针)` 崩溃。非平台特定 bugfix，上游测试 suite_2 复跑 7/7 通过。

## 依赖版本

无第三方构建依赖（pure C，仅 libm）。测试框架 Unity v2.5.2 按上游子模块声明
（gitcode 镜像恢复）仅供本地测试构建，不入配方。

## 上游测试清点与实测（R51）

| 测试源 | 独立用例数 | 实测结果 |
|--------|-----------|----------|
| test/suite_1/test_vectors.c | 1（test_fnv） | PASS |
| test/suite_2/test_fleur.c | 7（reading_header/reading_full/initialize/fingerprint/checking/writing/joining） | PASS（修复补丁后） |

合计：源码声明 8 个独立 RUN_TEST 用例，当前配置实例化 2 个可执行（suite_1_app /
suite_2_app），实测 8/8 通过（100%）。单元测试框架为 Unity（上游子模块）。
test_ohos 鸿蒙专项 5 项检查（ELF/musl/codesign/无宿主路径/真实 bloom 计算）全过；
消费者用例 consumer_fleur（爬虫去重场景）PASS。

## 验证结果

```bash
conan-verify fleur 0.3   # exit 0: G1/G0/G2/G3/G4 + L2/L4/L5
finish fleur 0.3 built   # exit 0: W3 本地 CI 模拟通过
test_ohos/run_ohos_test.py <pkg>   # exit 0: TEST_OHOS_ALL_PASS
consumer/consumer_fleur.c 编译+运行  # exit 0: consumer_fleur PASS
```

## 注意事项

- fleurcli 为子命令式 CLI（create/insert/check/show/set-data/get-data/join），
  无 `--version/--help` 选项（上游设计）；`commands.json` 已按 R38 声明，L2
  平台 smoke 跳过 `--version` 检查并如实记录。
- 上游测试需 Unity 子模块，仅测试构建使用；生产配方（TARGET_GROUP=production）
  不含 external/test。
- 基线隔离：本次 W3 命中 cloog/kics 3 个空标记文件，已按协议隔离复验并原样恢复，
  未修改/提交/写入 PR 或知识库。
**PR**: 待创建（Path B 知识库扩展，3 条知识草稿同 PR 交付）
---

**编译结束**: 2026-09-26 07:24
**最终状态**: built
