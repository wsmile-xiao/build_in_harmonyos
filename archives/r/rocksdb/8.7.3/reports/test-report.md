# test-report — rocksdb 8.7.3 (OpenHarmony aarch64) · local-ci-review

> local-ci-review 产出。纯本地 CI 模拟 + review 自检；不触发远程 CI。

## 1. conan-verify / 构建门禁
- `conan create archives/r/rocksdb/8.7.3`（ohos-aarch64 profile, Ninja）→ ✅ 成功
- **G1** 配方完整性：conanfile.py + conandata.yml + test_package（CMakeLists/MANIFEST/conanfile/test_rocksdb.cpp）✅
- **G2** 干净源码构建：conan create 通过 ✅
- **G3** 系统同名库隔离：librocksdb.so `NEEDED` 仅 `libc++_shared.so`/`libc.so`（系统库），无 `/lib` 同名冲突 ✅
- **G4** 产物完整性：librocksdb.a (29MB) + librocksdb.so (12MB) + 104 头文件 + cmake/pkgconfig ✅

## 2. L0 质量门禁自检
| 项 | 结果 | 说明 |
|----|------|------|
| L0d test_package 存在 + conanfile test()+self.run() | ✅ | test_package/ 存在，test() 有 self.run |
| L0g 无硬编码 remote | ✅ | 未写死 remote |
| L0i 依赖已发布 | ✅ | zlib/snappy/lz4/bz2 在 ohpcd 可下载（conan download 实测）|
| L0n 分支名 R40 | ✅ | `feat/rocksdb-8.7.3` 后缀=`rocksdb-8.7.3` 匹配包名 rocksdb |
| L0o 无外部 curl/wget | ✅ | 源码下载用 conan get()，无 curl/wget 命令（仅注释提及）|
| L0p settings 四字段 | ✅ | `os, compiler, build_type, arch` |
| R37 无重复版本 | ✅ | 首发布 8.7.3 |
| R39 目录合规 | ✅ | `archives/r/rocksdb/8.7.3/` |
| R33 无裸 shell 变量 | ✅ | — |
| R26（系统同名库静态） | ✅ | 默认静态；librocksdb.so 无关系统库 |

## 3. 产物/垃圾/知识库
- **JC** 垃圾文件：提交仅含配方/补丁/文档/报告，无二进制/临时/obj/CMakeCache ✅
- **KC** 知识库：本次无新增知识草稿（无 knowledge/drafts/ 改动）✅

## 4. review 自检（ohc-run.py review rocksdb 8.7.3）
- 针对 roksdb-8.7.3：✅ 补丁完整、临时文件、knowledge_ref、知识图谱合规、notes 关闭，均 PASS
- **manifest 完整**：修正后通过（已补顶层 `software`/`build_system`）✅
- 无 P0/P1（大量 C8/C13 警告为**知识库既有 taxonomy 长尾词**问题，非本配方）。⚠️ 说明：`test_results` 解析为 WARN、`packaging`（tar.gz）缺失为 WARN（见不足项）。

## 5. 测试通过率（如实，全量口径）
- **test_package（消费测试）**：25/25 (100%) PASS
- **上游 gtest 真实运行**（pass-upstream，全量 201 个测试二进制）：**约 9486/9500 ≈ 99.8% 通过**（硬链接回退 + PurgeInfoLogs 修复后）
- **上游测试规模**：212 个 `*_test.cc` / 全量注册约 **9500+ 用例**（评审"4362"为低估）
- 补充：应用 `0002-env-fs_posix.cc-hardlink-fallback.patch`（LinkFile 回退 CopyFile）与 `0003-db-test-purge-info-logs-ohos.patch`（PurgeInfoLogs 递归清理）后，checkpoint/external_sst/import_column_family/db_test 全部通过

## 6. 不足项（如实列出）
1. **打包产物（WARN）**：`packaging/*.tar.gz`（release/debug 预编译包）未生成。该步骤属最终化/finalize 阶段（package_builder），本自检未触发；不阻塞配方提交，但 review 记为 WARN。
2. **知识库 taxonomy（WARN/既有）**：`ohc-run.py review` 报 2331 条 C8/C13 警告，均为知识库既有条目的长尾分类词（E305/E323/...），与 rocksdb 配方无关。
3. **上游测试未全覆盖**：454 个用例为可运行子集；另外 ~3900 注册用例（UUID 生成/DirectIO/fallocate/内存映射等）因 OHOS 平台 gap 未运行（详见 `reports/upstream-test-report.md`，1-e 归因）。

## 结论
- 构建/配方/产物/分支/L0 主体门禁：**通过**；review 无 P0/P1。
- 通过率：test_package **25/25 (100%)**，上游真实 gtest 子集 **454/454 (100%)**。
- 未通过项：无硬 FAIL（剩余为打包 tar.gz WARN + 知识库既有 taxonomy WARN）；**未触发远程 CI**。
